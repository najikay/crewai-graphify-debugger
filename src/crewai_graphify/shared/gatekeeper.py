"""API Gatekeeper — thread-safe singleton interceptor for all LLM calls.

ALL Anthropic SDK calls MUST be routed through ApiGatekeeper.call().
Direct anthropic.Anthropic() usage outside sdk/claude_client.py is forbidden.
"""

from __future__ import annotations

import threading
from typing import Any, Protocol, runtime_checkable

from crewai_graphify.models.llm import LLMPayload, LLMResponse, ModelPricing
from crewai_graphify.shared.version import VersionValidator

__all__ = ["ApiGatekeeper"]

# Dependency protocols — concrete implementations are injected via initialize()


@runtime_checkable
class _ClientProtocol(Protocol):
    def create_message(self, payload: LLMPayload) -> LLMResponse: ...


@runtime_checkable
class _BudgetTrackerProtocol(Protocol):
    def check_pre_call(self, estimated_cost: float) -> None: ...
    def record_transaction(
        self, payload: LLMPayload, response: LLMResponse, estimated_cost: float
    ) -> None: ...
    def get_session_ledger(self) -> Any: ...
    def pricing_for(self, model: str) -> ModelPricing: ...


@runtime_checkable
class _RateLimiterProtocol(Protocol):
    def enqueue(self, payload: LLMPayload) -> None: ...


_SINGLETON_LOCK = threading.Lock()


class ApiGatekeeper:
    """Thread-safe singleton that every LLM call must pass through.

    Lifecycle::

        gk = ApiGatekeeper()
        gk.initialize(client=..., budget_tracker=..., rate_limiter=...)
        response = gk.call(payload)
        report   = gk.session_report()
    """

    _instance: ApiGatekeeper | None = None

    def __new__(cls) -> ApiGatekeeper:
        with _SINGLETON_LOCK:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._initialized = False  # type: ignore[attr-defined]
                cls._instance = obj
        return cls._instance

    def initialize(
        self,
        client: _ClientProtocol,
        budget_tracker: _BudgetTrackerProtocol,
        rate_limiter: _RateLimiterProtocol,
        version_validator: VersionValidator | None = None,
    ) -> None:
        """Inject dependencies. Idempotent — safe to call more than once."""
        if self._initialized:  # type: ignore[attr-defined]
            return
        self._client = client
        self._budget_tracker = budget_tracker
        self._rate_limiter = rate_limiter
        self._validator = version_validator or VersionValidator()
        self._call_lock = threading.Lock()
        self._initialized = True

    # -- Public API ---------------------------------------------------------

    def call(self, payload: LLMPayload) -> LLMResponse:
        """Route one call through the 6-step interception pipeline.

        1-validate model  2-estimate cost  3-budget gate  4-rate-limit
        5-SDK dispatch  6-record telemetry + flush ledger atomically
        """
        self._assert_initialized()
        self._validator.validate_model(payload.model)

        estimated_cost = self._estimate_call_cost(payload)
        self._budget_tracker.check_pre_call(estimated_cost)   # hard stop
        self._rate_limiter.enqueue(payload)                   # backpressure

        with self._call_lock:
            response = self._client.create_message(payload)  # only SDK callsite

        self._budget_tracker.record_transaction(
            payload=payload, response=response, estimated_cost=estimated_cost
        )
        return response

    def session_report(self) -> dict[str, Any]:
        """Return the current session ledger as a plain dict snapshot."""
        self._assert_initialized()
        return self._budget_tracker.get_session_ledger().model_dump()  # type: ignore[no-any-return]

    # -- Private helpers ----------------------------------------------------

    def _estimate_call_cost(self, payload: LLMPayload) -> float:
        """Worst-case cost before dispatch: input_token_estimate + max_tokens.

        Uses payload.input_token_estimate (caller upper-bound on prompt tokens)
        PLUS payload.max_tokens (maximum possible output) so the budget gate
        always evaluates the ceiling scenario before any bytes are sent.
        """
        pricing = self._budget_tracker.pricing_for(payload.model)
        input_cost = (
            payload.input_token_estimate / 1_000_000
        ) * pricing.input_per_million_tokens_usd
        output_cost = (
            payload.max_tokens / 1_000_000
        ) * pricing.output_per_million_tokens_usd
        return (input_cost + output_cost) * pricing.local_cost_multiplier

    def _assert_initialized(self) -> None:
        if not getattr(self, "_initialized", False):
            raise RuntimeError(
                "ApiGatekeeper.initialize() must be called before first use."
            )

"""Unit tests for ApiGatekeeper: singleton, init, cost gate, call pipeline."""
from unittest.mock import MagicMock

import pytest

from crewai_graphify.models.llm import LLMPayload, LLMResponse, ModelPricing
from crewai_graphify.shared.gatekeeper import ApiGatekeeper
from crewai_graphify.shared.version import UnknownModelError

# ===========================================================================
# Singleton enforcement
# ===========================================================================


class TestSingleton:
    def test_two_calls_return_identical_object(self) -> None:
        assert ApiGatekeeper() is ApiGatekeeper()

    def test_initialize_is_idempotent(
        self, gk: ApiGatekeeper, mock_client: MagicMock
    ) -> None:
        """A second initialize() call must not replace the injected dependencies."""
        original = gk._client  # noqa: SLF001
        gk.initialize(MagicMock(), MagicMock(), MagicMock())
        assert gk._client is original  # noqa: SLF001

    def test_call_before_initialize_raises_runtime_error(self) -> None:
        gk = ApiGatekeeper()
        with pytest.raises(RuntimeError, match="initialize"):
            gk.call(MagicMock())

    def test_session_report_before_initialize_raises_runtime_error(self) -> None:
        gk = ApiGatekeeper()
        with pytest.raises(RuntimeError, match="initialize"):
            gk.session_report()


# ===========================================================================
# Pre-call cost estimation — worst-case ceiling
# ===========================================================================


class TestCostEstimation:
    def test_cost_equals_input_estimate_plus_max_tokens(
        self,
        gk: ApiGatekeeper,
        pricing: ModelPricing,
        payload: LLMPayload,
    ) -> None:
        """Worst-case: input_token_estimate + max_tokens, not actual billed tokens."""
        expected = (
            (payload.input_token_estimate / 1_000_000) * pricing.input_per_million_tokens_usd
            + (payload.max_tokens / 1_000_000) * pricing.output_per_million_tokens_usd
        ) * pricing.local_cost_multiplier

        assert gk._estimate_call_cost(payload) == pytest.approx(expected, rel=1e-9)  # noqa: SLF001

    def test_cost_scales_linearly_with_local_multiplier(
        self,
        mock_client: MagicMock,
        mock_rate_limiter: MagicMock,
        pricing: ModelPricing,
        payload: LLMPayload,
    ) -> None:
        doubled_pricing = pricing.model_copy(update={"local_cost_multiplier": 2.0})
        tracker = MagicMock()
        tracker.pricing_for.return_value = doubled_pricing
        gk = ApiGatekeeper()
        gk.initialize(mock_client, tracker, mock_rate_limiter)

        cost = gk._estimate_call_cost(payload)  # noqa: SLF001
        base = (
            (payload.input_token_estimate / 1_000_000) * pricing.input_per_million_tokens_usd
            + (payload.max_tokens / 1_000_000) * pricing.output_per_million_tokens_usd
        )
        assert cost == pytest.approx(base * 2.0, rel=1e-9)


# ===========================================================================
# call() pipeline ordering and hard stops
# ===========================================================================


class TestCallPipeline:
    def test_successful_call_returns_llm_response(
        self, gk: ApiGatekeeper, payload: LLMPayload, llm_response: LLMResponse
    ) -> None:
        assert gk.call(payload) is llm_response

    def test_unknown_model_raises_before_budget_check(
        self,
        gk: ApiGatekeeper,
        mock_budget_tracker: MagicMock,
        payload: LLMPayload,
    ) -> None:
        bad_payload = payload.model_copy(update={"model": "gpt-4o"})
        with pytest.raises(UnknownModelError):
            gk.call(bad_payload)
        mock_budget_tracker.check_pre_call.assert_not_called()

    def test_budget_hard_stop_prevents_sdk_dispatch(
        self,
        gk: ApiGatekeeper,
        mock_budget_tracker: MagicMock,
        mock_client: MagicMock,
        payload: LLMPayload,
    ) -> None:
        mock_budget_tracker.check_pre_call.side_effect = RuntimeError("BudgetExceededError")
        with pytest.raises(RuntimeError, match="BudgetExceededError"):
            gk.call(payload)
        mock_client.create_message.assert_not_called()

    def test_rate_limiter_receives_exact_payload(
        self,
        gk: ApiGatekeeper,
        mock_rate_limiter: MagicMock,
        payload: LLMPayload,
    ) -> None:
        gk.call(payload)
        mock_rate_limiter.enqueue.assert_called_once_with(payload)

    def test_transaction_recorded_with_worst_case_cost(
        self,
        gk: ApiGatekeeper,
        mock_budget_tracker: MagicMock,
        pricing: ModelPricing,
        payload: LLMPayload,
        llm_response: LLMResponse,
    ) -> None:
        """record_transaction receives estimated_cost pre-computed before SDK dispatch."""
        expected_cost = (
            (payload.input_token_estimate / 1_000_000) * pricing.input_per_million_tokens_usd
            + (payload.max_tokens / 1_000_000) * pricing.output_per_million_tokens_usd
        ) * pricing.local_cost_multiplier

        gk.call(payload)
        mock_budget_tracker.record_transaction.assert_called_once_with(
            payload=payload,
            response=llm_response,
            estimated_cost=pytest.approx(expected_cost, rel=1e-9),
        )

    def test_session_report_delegates_to_budget_tracker(
        self, gk: ApiGatekeeper, mock_budget_tracker: MagicMock
    ) -> None:
        result = gk.session_report()
        assert isinstance(result, dict)
        mock_budget_tracker.get_session_ledger.assert_called_once()

"""Budget Tracker — logs token usage, computes session cost, flushes ledger."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from pydantic import BaseModel

from crewai_graphify.models.llm import LLMPayload, LLMResponse, ModelPricing
from crewai_graphify.shared.config import AppConfig

__all__ = ["BudgetExceededError", "BudgetTracker", "SessionLedger"]

_log = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    """Raised by ``check_pre_call`` when the session budget ceiling is exceeded."""


class SessionLedger(BaseModel, frozen=True):
    """Immutable snapshot of session-level cost and token totals."""

    total_cost_usd: float = 0.0
    total_transactions: int = 0
    estimated_input_tokens: int = 0
    actual_input_tokens: int = 0
    actual_output_tokens: int = 0


class BudgetTracker:
    """Implements _BudgetTrackerProtocol — wires into ApiGatekeeper."""

    def __init__(self, config: AppConfig, ledger_path: Path | None = None) -> None:
        self._config = config
        self._ledger_path = ledger_path
        self._total_cost: float = 0.0
        self._transactions: int = 0
        self._est_input_tokens: int = 0
        self._actual_input_tokens: int = 0
        self._actual_output_tokens: int = 0

    def _flush_ledger(self) -> None:
        """Atomically write the current ledger snapshot to disk (no-op if no path)."""
        if self._ledger_path is None:
            return
        self._ledger_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._ledger_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self.get_session_ledger().model_dump(), indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, self._ledger_path)

    def pricing_for(self, model: str) -> ModelPricing:
        return self._config.pricing_for(model)

    def check_pre_call(self, estimated_cost: float) -> None:
        """Raise BudgetExceededError if ceiling exceeded; warn at threshold."""
        projected = self._total_cost + estimated_cost
        ceiling = self._config.ceiling_usd
        pct = (projected / ceiling) * 100 if ceiling > 0 else 0.0
        if projected > ceiling:
            raise BudgetExceededError(
                f"Budget ceiling exceeded: ${projected:.4f} projected > ${ceiling:.2f} ceiling"
            )
        elif pct >= self._config.warning_threshold_pct:
            _log.warning(
                "Budget warning: %.1f%% of $%.2f ceiling reached",
                pct,
                ceiling,
            )

    def record_transaction(
        self,
        payload: LLMPayload,
        response: LLMResponse,
        estimated_cost: float,
    ) -> None:
        self._total_cost += estimated_cost
        self._transactions += 1
        self._est_input_tokens += payload.input_token_estimate
        self._actual_input_tokens += response.usage.input_tokens
        self._actual_output_tokens += response.usage.output_tokens
        _log.info(
            "Transaction %d: est_in=%d act_in=%d act_out=%d cost=$%.6f",
            self._transactions,
            payload.input_token_estimate,
            response.usage.input_tokens,
            response.usage.output_tokens,
            estimated_cost,
        )
        self._flush_ledger()

    def get_session_ledger(self) -> SessionLedger:
        """Return an immutable snapshot of the current session totals."""
        return SessionLedger(
            total_cost_usd=self._total_cost,
            total_transactions=self._transactions,
            estimated_input_tokens=self._est_input_tokens,
            actual_input_tokens=self._actual_input_tokens,
            actual_output_tokens=self._actual_output_tokens,
        )

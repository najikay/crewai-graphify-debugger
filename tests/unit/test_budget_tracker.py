"""Unit tests for BudgetTracker — pricing, pre-call gate, and transaction recording."""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

from crewai_graphify.models.llm import LLMPayload, LLMResponse, ModelPricing, UsageStats
from crewai_graphify.shared.budget_tracker import BudgetExceededError, BudgetTracker
from crewai_graphify.shared.config import AppConfig

CONFIG_DIR = Path("config")


@pytest.fixture()
def cfg() -> AppConfig:
    return AppConfig.load(CONFIG_DIR)


@pytest.fixture()
def tracker(cfg: AppConfig) -> BudgetTracker:
    return BudgetTracker(cfg)


@pytest.fixture()
def payload() -> LLMPayload:
    return LLMPayload(
        model="claude-sonnet-4-6",
        system="debug",
        messages=[{"role": "user", "content": "Find bug"}],
        max_tokens=512,
        input_token_estimate=1000,
    )


@pytest.fixture()
def response() -> LLMResponse:
    return LLMResponse(
        id="msg_1",
        model="claude-sonnet-4-6",
        content="Found it.",
        usage=UsageStats(input_tokens=980, output_tokens=40),
        stop_reason="end_turn",
    )


class TestPricingFor:
    def test_returns_model_pricing(self, tracker: BudgetTracker) -> None:
        assert isinstance(tracker.pricing_for("claude-sonnet-4-6"), ModelPricing)

    def test_unknown_model_raises(self, tracker: BudgetTracker) -> None:
        with pytest.raises(KeyError):
            tracker.pricing_for("gpt-4o")


class TestCheckPreCall:
    def test_no_raise_under_budget(self, tracker: BudgetTracker) -> None:
        tracker.check_pre_call(0.001)  # must not raise

    def test_raises_budget_exceeded_error_over_ceiling(self, tracker: BudgetTracker) -> None:
        with pytest.raises(BudgetExceededError):
            tracker.check_pre_call(999.0)

    def test_exception_message_contains_projected_cost(self, tracker: BudgetTracker) -> None:
        with pytest.raises(BudgetExceededError, match="999"):
            tracker.check_pre_call(999.0)

    def test_warning_logged_at_threshold(
        self, tracker: BudgetTracker, caplog: pytest.LogCaptureFixture
    ) -> None:
        pct = tracker._config.warning_threshold_pct / 100
        amount = tracker._config.ceiling_usd * pct + 0.001
        with caplog.at_level(logging.WARNING):
            tracker.check_pre_call(amount)
        assert len(caplog.records) >= 1

    def test_no_warning_below_threshold(
        self, tracker: BudgetTracker, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            tracker.check_pre_call(0.001)
        assert len(caplog.records) == 0


class TestRecordTransaction:
    def test_accumulates_cost(
        self, tracker: BudgetTracker, payload: LLMPayload, response: LLMResponse
    ) -> None:
        tracker.record_transaction(payload=payload, response=response, estimated_cost=0.05)
        tracker.record_transaction(payload=payload, response=response, estimated_cost=0.03)
        assert tracker.get_session_ledger().total_cost_usd == pytest.approx(0.08)

    def test_increments_transaction_count(
        self, tracker: BudgetTracker, payload: LLMPayload, response: LLMResponse
    ) -> None:
        tracker.record_transaction(payload=payload, response=response, estimated_cost=0.01)
        assert tracker.get_session_ledger().total_transactions == 1

    def test_tracks_estimated_tokens(
        self, tracker: BudgetTracker, payload: LLMPayload, response: LLMResponse
    ) -> None:
        tracker.record_transaction(payload=payload, response=response, estimated_cost=0.01)
        assert tracker.get_session_ledger().estimated_input_tokens == 1000

    def test_tracks_actual_tokens(
        self, tracker: BudgetTracker, payload: LLMPayload, response: LLMResponse
    ) -> None:
        tracker.record_transaction(payload=payload, response=response, estimated_cost=0.01)
        ledger = tracker.get_session_ledger()
        assert ledger.actual_input_tokens == 980 and ledger.actual_output_tokens == 40

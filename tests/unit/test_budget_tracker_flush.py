"""Unit tests for BudgetTracker atomic ledger flush + SessionLedger snapshot."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from crewai_graphify.models.llm import LLMPayload, LLMResponse, UsageStats
from crewai_graphify.shared.budget_tracker import BudgetTracker, SessionLedger
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


class TestSessionLedger:
    def test_initial_ledger_is_zero(self, tracker: BudgetTracker) -> None:
        ledger = tracker.get_session_ledger()
        assert ledger.total_cost_usd == 0.0 and ledger.total_transactions == 0

    def test_model_dump_has_required_keys(self, tracker: BudgetTracker) -> None:
        d = tracker.get_session_ledger().model_dump()
        assert "total_cost_usd" in d and "total_transactions" in d

    def test_session_ledger_is_frozen(self) -> None:
        ledger = SessionLedger()
        with pytest.raises(ValidationError):
            ledger.total_cost_usd = 99.0  # type: ignore[misc]


class TestAtomicFlush:
    def test_flush_writes_ledger_json(
        self, cfg: AppConfig, payload: LLMPayload, response: LLMResponse, tmp_path: Path
    ) -> None:
        ledger_file = tmp_path / "ledger.json"
        tracker = BudgetTracker(cfg, ledger_path=ledger_file)
        tracker.record_transaction(payload=payload, response=response, estimated_cost=0.01)
        assert ledger_file.exists()

    def test_flush_content_is_valid_json(
        self, cfg: AppConfig, payload: LLMPayload, response: LLMResponse, tmp_path: Path
    ) -> None:
        ledger_file = tmp_path / "ledger.json"
        tracker = BudgetTracker(cfg, ledger_path=ledger_file)
        tracker.record_transaction(payload=payload, response=response, estimated_cost=0.05)
        data = json.loads(ledger_file.read_text(encoding="utf-8"))
        assert data["total_transactions"] == 1
        assert data["total_cost_usd"] == pytest.approx(0.05)

    def test_flush_tmp_file_not_present_after_write(
        self, cfg: AppConfig, payload: LLMPayload, response: LLMResponse, tmp_path: Path
    ) -> None:
        ledger_file = tmp_path / "ledger.json"
        tracker = BudgetTracker(cfg, ledger_path=ledger_file)
        tracker.record_transaction(payload=payload, response=response, estimated_cost=0.01)
        assert not (tmp_path / "ledger.tmp").exists()

    def test_flush_no_op_without_ledger_path(
        self, tracker: BudgetTracker, payload: LLMPayload, response: LLMResponse
    ) -> None:
        # tracker has no ledger_path — must not raise
        tracker.record_transaction(payload=payload, response=response, estimated_cost=0.01)

    def test_flush_creates_parent_directories(
        self, cfg: AppConfig, payload: LLMPayload, response: LLMResponse, tmp_path: Path
    ) -> None:
        nested = tmp_path / "deep" / "nested" / "ledger.json"
        tracker = BudgetTracker(cfg, ledger_path=nested)
        tracker.record_transaction(payload=payload, response=response, estimated_cost=0.01)
        assert nested.exists()

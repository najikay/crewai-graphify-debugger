"""Unit tests for main.py — report writers, rate limiter, budget session."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crewai_graphify.main import (
    _budget_session,
    _sanitize_messages,
    _save_efficiency_report,
    _save_root_cause,
    _ThrottledRateLimiter,
)
from crewai_graphify.shared.budget_tracker import SessionLedger
from crewai_graphify.shared.gatekeeper import ApiGatekeeper

_WKSP = "crewai_graphify.main._WORKSPACE"
_TGTPY = "crewai_graphify.main._TARGET_PY"


@pytest.fixture(autouse=True)
def _reset_gk() -> None:  # type: ignore[return]
    ApiGatekeeper._instance = None
    yield
    ApiGatekeeper._instance = None


@pytest.fixture()
def ledger() -> SessionLedger:
    return SessionLedger(
        total_transactions=3,
        estimated_input_tokens=500,
        actual_input_tokens=420,
        actual_output_tokens=80,
        total_cost_usd=0.002345,
    )


class TestSaveRootCause:
    def test_writes_parsed_json(self, tmp_path: Path) -> None:
        with patch(_WKSP, tmp_path):
            _save_root_cause('{"root_cause": "NameError"}')
        data = json.loads((tmp_path / "root_cause_report.json").read_text())
        assert data["root_cause"] == "NameError"

    def test_invalid_json_wrapped_in_raw_output(self, tmp_path: Path) -> None:
        with patch(_WKSP, tmp_path):
            _save_root_cause("not json at all")
        data = json.loads((tmp_path / "root_cause_report.json").read_text())
        assert "raw_output" in data

    def test_creates_workspace_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "ws"
        with patch(_WKSP, target):
            _save_root_cause("{}")
        assert target.exists()

    def test_file_is_valid_json(self, tmp_path: Path) -> None:
        with patch(_WKSP, tmp_path):
            _save_root_cause('{"line": 29}')
        raw = (tmp_path / "root_cause_report.json").read_text()
        assert json.loads(raw) == {"line": 29}


class TestSaveEfficiencyReport:
    def test_creates_report_file(self, tmp_path: Path, ledger: SessionLedger) -> None:
        with patch(_WKSP, tmp_path), patch(_TGTPY, tmp_path / "no.py"):
            _save_efficiency_report(ledger)
        assert (tmp_path / "token_efficiency_report.md").exists()

    def test_report_contains_api_call_count(
        self, tmp_path: Path, ledger: SessionLedger
    ) -> None:
        with patch(_WKSP, tmp_path), patch(_TGTPY, tmp_path / "no.py"):
            _save_efficiency_report(ledger)
        text = (tmp_path / "token_efficiency_report.md").read_text()
        assert "3" in text  # total_transactions

    def test_report_contains_cost(self, tmp_path: Path, ledger: SessionLedger) -> None:
        with patch(_WKSP, tmp_path), patch(_TGTPY, tmp_path / "no.py"):
            _save_efficiency_report(ledger)
        text = (tmp_path / "token_efficiency_report.md").read_text()
        assert "0.002345" in text

    def test_report_contains_savings_row(self, tmp_path: Path, ledger: SessionLedger) -> None:
        with patch(_WKSP, tmp_path), patch(_TGTPY, tmp_path / "no.py"):
            _save_efficiency_report(ledger)
        text = (tmp_path / "token_efficiency_report.md").read_text()
        assert "Savings" in text

    def test_naive_estimate_from_file(self, tmp_path: Path, ledger: SessionLedger) -> None:
        py_file = tmp_path / "polygons.py"
        py_file.write_text("x" * 400, encoding="utf-8")  # 400 chars = 100 tokens
        with patch(_WKSP, tmp_path), patch(_TGTPY, py_file):
            _save_efficiency_report(ledger)
        text = (tmp_path / "token_efficiency_report.md").read_text()
        assert "100" in text  # naive token count

    def test_missing_target_falls_back_to_zero(
        self, tmp_path: Path, ledger: SessionLedger
    ) -> None:
        with patch(_WKSP, tmp_path), patch(_TGTPY, tmp_path / "missing.py"):
            _save_efficiency_report(ledger)  # must not raise


class TestThrottledRateLimiter:
    def test_enqueue_sleeps(self) -> None:
        rl = _ThrottledRateLimiter()
        with patch.object(time, "sleep") as mock_sleep:
            rl.enqueue(MagicMock())
            mock_sleep.assert_called_once_with(0.5)


class TestBudgetSession:
    def test_yields_budget_tracker(self, tmp_path: Path) -> None:
        from crewai_graphify.shared.budget_tracker import BudgetTracker
        from crewai_graphify.shared.config import AppConfig

        cfg = AppConfig.load(Path("config"))
        mock_client = MagicMock()
        mock_rl = MagicMock()

        with (
            patch("crewai_graphify.main._AnthropicClient", return_value=mock_client),
            patch("crewai_graphify.main._ThrottledRateLimiter", return_value=mock_rl),
            _budget_session(cfg) as tracker,
        ):
            assert isinstance(tracker, BudgetTracker)


class TestSanitizeMessages:
    # --- cache_breakpoint stripping (original behaviour) --------------------

    def test_clean_messages_pass_through(self) -> None:
        msgs = [{"role": "user", "content": "hello"}]
        _sys, result = _sanitize_messages("fallback", msgs)
        assert result == msgs and _sys == "fallback"

    def test_strips_cache_breakpoint(self) -> None:
        dirty = [{"role": "user", "content": "hello", "cache_breakpoint": True}]
        _, result = _sanitize_messages("s", dirty)
        assert result == [{"role": "user", "content": "hello"}]

    def test_strips_multiple_extra_keys(self) -> None:
        dirty = [{"role": "user", "content": "x", "cache_breakpoint": True, "extra": 1}]
        _, result = _sanitize_messages("s", dirty)
        assert set(result[0].keys()) == {"role", "content"}

    def test_warning_logged_when_stripping(self, caplog: pytest.LogCaptureFixture) -> None:
        dirty = [{"role": "user", "content": "x", "cache_breakpoint": True}]
        with caplog.at_level(logging.WARNING):
            _sanitize_messages("s", dirty)
        assert "cache_breakpoint" in caplog.text

    def test_no_warning_for_clean_messages(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            _sanitize_messages("s", [{"role": "user", "content": "x"}])
        assert not caplog.records

    # --- system-message hoisting (new behaviour) ----------------------------

    def test_system_message_extracted_to_return_value(self) -> None:
        msgs = [{"role": "system", "content": "Be helpful."}, {"role": "user", "content": "Hi"}]
        system, result = _sanitize_messages("fallback", msgs)
        assert system == "Be helpful."
        assert result == [{"role": "user", "content": "Hi"}]

    def test_system_message_removed_from_cleaned_list(self) -> None:
        msgs = [{"role": "system", "content": "Sys"}, {"role": "user", "content": "U"}]
        _, result = _sanitize_messages("fb", msgs)
        assert all(m["role"] != "system" for m in result)

    def test_fallback_system_used_when_no_system_message(self) -> None:
        msgs = [{"role": "user", "content": "Q"}]
        system, _ = _sanitize_messages("default-system", msgs)
        assert system == "default-system"

    def test_multiple_system_messages_joined(self) -> None:
        msgs = [
            {"role": "system", "content": "Part A"},
            {"role": "system", "content": "Part B"},
            {"role": "user", "content": "Q"},
        ]
        system, _ = _sanitize_messages("fb", msgs)
        assert "Part A" in system and "Part B" in system

    def test_warning_logged_when_hoisting(self, caplog: pytest.LogCaptureFixture) -> None:
        msgs = [{"role": "system", "content": "Sys"}, {"role": "user", "content": "U"}]
        with caplog.at_level(logging.WARNING):
            _sanitize_messages("fb", msgs)
        assert "Hoisted" in caplog.text

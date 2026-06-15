"""Unit tests for main.py — report writers, budget session, message sanitizer."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crewai_graphify.main import (
    _budget_session,
    _sanitize_messages,
    _save_efficiency_report,
    _save_root_cause,
)
from crewai_graphify.shared.budget_tracker import BudgetTracker, SessionLedger
from crewai_graphify.shared.config import AppConfig
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
    return SessionLedger(total_transactions=3, estimated_input_tokens=500, actual_input_tokens=420, actual_output_tokens=80, total_cost_usd=0.002345)


def _root_cause(tmp_path: Path, raw: str) -> Path:
    with patch(_WKSP, tmp_path):
        _save_root_cause(raw)
    return tmp_path / "root_cause_report.json"


def _gen_report(tmp_path: Path, ledger: SessionLedger, target: Path | None = None) -> str:
    with patch(_WKSP, tmp_path), patch(_TGTPY, target or tmp_path / "no.py"):
        _save_efficiency_report(ledger)
    return (tmp_path / "token_efficiency_report.md").read_text()


class TestSaveRootCause:
    def test_writes_parsed_json(self, tmp_path: Path) -> None:
        data = json.loads(_root_cause(tmp_path, '{"root_cause": "NameError"}').read_text())
        assert data["root_cause"] == "NameError"

    def test_invalid_json_wrapped_in_raw_output(self, tmp_path: Path) -> None:
        data = json.loads(_root_cause(tmp_path, "not json at all").read_text())
        assert "raw_output" in data

    def test_creates_workspace_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "ws"
        with patch(_WKSP, target):
            _save_root_cause("{}")
        assert target.exists()

    def test_file_is_valid_json(self, tmp_path: Path) -> None:
        assert json.loads(_root_cause(tmp_path, '{"line": 29}').read_text()) == {"line": 29}


class TestSaveEfficiencyReport:
    def test_creates_report_file(self, tmp_path: Path, ledger: SessionLedger) -> None:
        _gen_report(tmp_path, ledger)
        assert (tmp_path / "token_efficiency_report.md").exists()

    def test_report_contains_api_call_count(self, tmp_path: Path, ledger: SessionLedger) -> None:
        assert "3" in _gen_report(tmp_path, ledger)  # total_transactions

    def test_report_contains_cost(self, tmp_path: Path, ledger: SessionLedger) -> None:
        assert "0.002345" in _gen_report(tmp_path, ledger)

    def test_report_has_both_sections(self, tmp_path: Path, ledger: SessionLedger) -> None:
        text = _gen_report(tmp_path, ledger)
        assert "Session Summary" in text and "Context Optimization" in text

    def test_context_reduction_from_file(self, tmp_path: Path, ledger: SessionLedger) -> None:
        (tmp_path / "p.py").write_text("\n".join("x" for _ in range(75)), encoding="utf-8")  # 75 lines
        assert "~68%" in _gen_report(tmp_path, ledger, target=tmp_path / "p.py")  # 24 of 75 → 68%

    def test_missing_target_falls_back_to_zero(self, tmp_path: Path, ledger: SessionLedger) -> None:
        _gen_report(tmp_path, ledger, target=tmp_path / "missing.py")  # must not raise


class TestBudgetSession:
    def test_yields_budget_tracker(self, tmp_path: Path) -> None:
        cfg = AppConfig.load(Path("config"))
        with patch("crewai_graphify.main._AnthropicClient", return_value=MagicMock()), \
                patch("crewai_graphify.main.ThrottledRateLimiter", return_value=MagicMock()), \
                _budget_session(cfg) as tracker:
            assert isinstance(tracker, BudgetTracker)


class TestSanitizeMessages:
    def test_clean_messages_pass_through(self) -> None:
        msgs = [{"role": "user", "content": "hello"}]
        _sys, result = _sanitize_messages("fallback", msgs)
        assert result == msgs and _sys == "fallback"

    def test_strips_cache_breakpoint(self) -> None:
        _, result = _sanitize_messages("s", [{"role": "user", "content": "hello", "cache_breakpoint": True}])
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

    def test_system_message_extracted_to_return_value(self) -> None:
        msgs = [{"role": "system", "content": "Be helpful."}, {"role": "user", "content": "Hi"}]
        system, result = _sanitize_messages("fallback", msgs)
        assert system == "Be helpful." and result == [{"role": "user", "content": "Hi"}]

    def test_system_message_removed_from_cleaned_list(self) -> None:
        msgs = [{"role": "system", "content": "Sys"}, {"role": "user", "content": "U"}]
        _, result = _sanitize_messages("fb", msgs)
        assert all(m["role"] != "system" for m in result)

    def test_fallback_system_used_when_no_system_message(self) -> None:
        system, _ = _sanitize_messages("default-system", [{"role": "user", "content": "Q"}])
        assert system == "default-system"

    def test_multiple_system_messages_joined(self) -> None:
        msgs = [{"role": "system", "content": "Part A"}, {"role": "system", "content": "Part B"}, {"role": "user", "content": "Q"}]
        system, _ = _sanitize_messages("fb", msgs)
        assert "Part A" in system and "Part B" in system

    def test_warning_logged_when_hoisting(self, caplog: pytest.LogCaptureFixture) -> None:
        msgs = [{"role": "system", "content": "Sys"}, {"role": "user", "content": "U"}]
        with caplog.at_level(logging.WARNING):
            _sanitize_messages("fb", msgs)
        assert "Hoisted" in caplog.text

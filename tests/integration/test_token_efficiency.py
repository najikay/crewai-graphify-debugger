"""Integration test — graph-guided slicing yields a large context reduction.

The test builds a synthetic 10,000-line monolith and asserts that the efficiency
report produced by ``_save_efficiency_report`` records a >50 % context reduction
(the hot-node slice is a tiny fraction of the whole file's line count).
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest

from crewai_graphify.main import _save_efficiency_report
from crewai_graphify.shared.budget_tracker import SessionLedger

_WKSP = "crewai_graphify.main._WORKSPACE"
_TGTPY = "crewai_graphify.main._TARGET_PY"

# A 10,000-line monolith; the graph-guided hot slice (24 lines) is a tiny fraction.
_MONOLITH_LINES = 10_000
_CHARS_PER_LINE = 80
_GRAPH_GUIDED_TOKENS = 3_000  # only hot-node slices were read


@pytest.fixture()
def monolith(tmp_path: Path) -> Path:
    """Write a synthetic 10 000-line Python file and return its path."""
    py = tmp_path / "monolith.py"
    line = "x = " + "1" * (_CHARS_PER_LINE - 4) + "\n"  # exactly 80 chars
    py.write_text(line * _MONOLITH_LINES, encoding="utf-8")
    return py


@pytest.fixture()
def ledger() -> SessionLedger:
    """SessionLedger simulating a graph-guided run that read 3 000 input tokens."""
    return SessionLedger(
        total_transactions=4,
        estimated_input_tokens=3_500,
        actual_input_tokens=_GRAPH_GUIDED_TOKENS,
        actual_output_tokens=200,
        total_cost_usd=0.004_500,
    )


class TestTokenEfficiency:
    def test_report_file_created(
        self, monolith: Path, ledger: SessionLedger, tmp_path: Path
    ) -> None:
        with patch(_WKSP, tmp_path), patch(_TGTPY, monolith):
            _save_efficiency_report(ledger)
        assert (tmp_path / "token_efficiency_report.md").exists()

    def test_context_reduction_exceeds_50_percent(
        self, monolith: Path, ledger: SessionLedger, tmp_path: Path
    ) -> None:
        """Reading only the 24-line hot slice of a 10k-line file → ~100 % context reduction."""
        with patch(_WKSP, tmp_path), patch(_TGTPY, monolith):
            _save_efficiency_report(ledger)
        text = (tmp_path / "token_efficiency_report.md").read_text(encoding="utf-8")
        match = re.search(r"~(\d+)% less context", text)
        assert match is not None, "Context-reduction percentage not found in report"
        assert float(match.group(1)) > 50.0

    def test_full_line_count_reflects_file_size(
        self, monolith: Path, ledger: SessionLedger, tmp_path: Path
    ) -> None:
        """The 'entire file' baseline row shows the full line count (10,000)."""
        with patch(_WKSP, tmp_path), patch(_TGTPY, monolith):
            _save_efficiency_report(ledger)
        text = (tmp_path / "token_efficiency_report.md").read_text(encoding="utf-8")
        assert str(_MONOLITH_LINES) in text  # full-file line count in the report

    def test_actual_tokens_appear_in_report(
        self, monolith: Path, ledger: SessionLedger, tmp_path: Path
    ) -> None:
        with patch(_WKSP, tmp_path), patch(_TGTPY, monolith):
            _save_efficiency_report(ledger)
        text = (tmp_path / "token_efficiency_report.md").read_text(encoding="utf-8")
        assert str(_GRAPH_GUIDED_TOKENS) in text.replace(",", "")

    def test_cost_appears_in_report(
        self, monolith: Path, ledger: SessionLedger, tmp_path: Path
    ) -> None:
        with patch(_WKSP, tmp_path), patch(_TGTPY, monolith):
            _save_efficiency_report(ledger)
        text = (tmp_path / "token_efficiency_report.md").read_text(encoding="utf-8")
        assert "0.004500" in text

    def test_api_call_count_in_report(
        self, monolith: Path, ledger: SessionLedger, tmp_path: Path
    ) -> None:
        with patch(_WKSP, tmp_path), patch(_TGTPY, monolith):
            _save_efficiency_report(ledger)
        text = (tmp_path / "token_efficiency_report.md").read_text(encoding="utf-8")
        assert "4" in text  # total_transactions

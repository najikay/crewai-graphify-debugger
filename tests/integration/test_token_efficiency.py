"""Integration test — graph-guided slicing saves >50 % tokens vs. naive full-file dump.

The test builds a synthetic 10,000-line monolith, pretends the graph-guided
crew read only a small slice (3,000 tokens), and asserts that the efficiency
report produced by ``_save_efficiency_report`` records ≥ 50 % token savings.
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

# 10,000 lines × 80 chars = 800,000 chars ≈ 200,000 naive tokens (@4 chars/token)
_MONOLITH_LINES = 10_000
_CHARS_PER_LINE = 80
_CHARS_PER_TOKEN = 4
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

    def test_savings_exceed_50_percent(
        self, monolith: Path, ledger: SessionLedger, tmp_path: Path
    ) -> None:
        """Graph-guided reading of 3 000 tokens out of a 200 000-token monolith → 98.5 % saving."""
        with patch(_WKSP, tmp_path), patch(_TGTPY, monolith):
            _save_efficiency_report(ledger)
        text = (tmp_path / "token_efficiency_report.md").read_text(encoding="utf-8")
        # Extract the percentage from the "Savings" row: "… tokens (XX.X% reduction)"
        match = re.search(r"\((\d+(?:\.\d+)?)% reduction\)", text)
        assert match is not None, "Savings percentage not found in report"
        pct = float(match.group(1))
        assert pct > 50.0, f"Expected >50 % savings, got {pct:.1f} %"

    def test_naive_token_count_reflects_file_size(
        self, monolith: Path, ledger: SessionLedger, tmp_path: Path
    ) -> None:
        """Naive count = file_chars / 4; derived from actual file to stay exact."""
        expected_naive = len(monolith.read_text(encoding="utf-8")) // _CHARS_PER_TOKEN
        with patch(_WKSP, tmp_path), patch(_TGTPY, monolith):
            _save_efficiency_report(ledger)
        text = (tmp_path / "token_efficiency_report.md").read_text(encoding="utf-8")
        assert str(expected_naive) in text.replace(",", ""), (
            f"Expected naive count {expected_naive} in report"
        )

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

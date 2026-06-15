"""Unit tests for the read tools: read_vault_document, read_code_slice, read-cap."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from crewai_graphify.agents.tools import (
    _MAX_READS,
    _read_counter,
    read_code_slice,
    read_vault_document,
    reset_read_cap,
)

_VAULT = "crewai_graphify.agents.tools._VAULT"
_TARGET = "crewai_graphify.agents.tools._TARGET"


@pytest.fixture(autouse=True)
def _reset_read_counter() -> None:  # type: ignore[return]
    _read_counter.reset()
    yield
    _read_counter.reset()


class TestReadVaultDocument:
    def test_returns_file_content(self, tmp_path: Path) -> None:
        (tmp_path / "hot.md").write_text("# Hot nodes\n- Polygon", encoding="utf-8")
        with patch(_VAULT, tmp_path):
            assert "Hot nodes" in read_vault_document._run(filename="hot.md")

    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        with patch(_VAULT, tmp_path):
            result = read_vault_document._run(filename="missing.md")
        assert "[ERROR]" in result and "missing.md" in result

    def test_reads_exact_content(self, tmp_path: Path) -> None:
        (tmp_path / "index.md").write_text("line1\nline2\nline3", encoding="utf-8")
        with patch(_VAULT, tmp_path):
            assert read_vault_document._run(filename="index.md") == "line1\nline2\nline3"

    def test_func_attribute_is_callable(self) -> None:
        assert callable(read_vault_document.func)

    def test_tool_name(self) -> None:
        assert read_vault_document.name == "read_vault_document"


class TestReadCodeSlice:
    def test_returns_requested_lines(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("\n".join(f"line{i}" for i in range(1, 11)), encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="main.py", start_line=2, end_line=4)
        assert "line2" in result and "line4" in result and "line5" not in result

    def test_header_contains_filename_and_range(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("a\nb\nc", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="app.py", start_line=1, end_line=2)
        assert "app.py" in result and "1" in result and "2" in result

    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="nope.py", start_line=1, end_line=5)
        assert "[ERROR]" in result and "nope.py" in result

    def test_invalid_start_line_zero(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("x", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            assert "[ERROR]" in read_code_slice._run(file_path="f.py", start_line=0, end_line=1)

    def test_end_before_start_returns_error(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("x\ny", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            assert "[ERROR]" in read_code_slice._run(file_path="f.py", start_line=5, end_line=3)

    def test_out_of_range_returns_error(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("only one line", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            assert "[ERROR]" in read_code_slice._run(file_path="f.py", start_line=99, end_line=100)

    def test_clamps_end_to_file_length(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("a\nb\nc", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="f.py", start_line=2, end_line=999)
        assert "b" in result and "c" in result

    def test_tool_name(self) -> None:
        assert read_code_slice.name == "read_code_slice"

    def test_func_attribute_is_callable(self) -> None:
        assert callable(read_code_slice.func)


class TestReadCodeSliceCap:
    def test_cap_enforced_after_max_reads(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("x", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            for _ in range(_MAX_READS):
                read_code_slice._run(file_path="f.py", start_line=1, end_line=1)
            result = read_code_slice._run(file_path="f.py", start_line=1, end_line=1)
        assert "[ERROR]" in result and "cap" in result.lower()

    def test_reset_read_cap_clears_counter(self) -> None:
        _read_counter.increment()
        _read_counter.increment()
        reset_read_cap()
        assert _read_counter.count == 0

    def test_reads_work_again_after_reset(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("hello", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            for _ in range(_MAX_READS + 2):
                read_code_slice._run(file_path="f.py", start_line=1, end_line=1)
            reset_read_cap()
            result = read_code_slice._run(file_path="f.py", start_line=1, end_line=1)
        assert "[ERROR]" not in result and "hello" in result

    def test_counter_increments_per_call(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("x", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            read_code_slice._run(file_path="f.py", start_line=1, end_line=1)
        assert _read_counter.count == 1

    def test_counter_increments_on_invalid_calls_too(self, tmp_path: Path) -> None:
        with patch(_TARGET, tmp_path):
            read_code_slice._run(file_path="missing.py", start_line=1, end_line=1)
        assert _read_counter.count == 1

    def test_reset_clears_count(self) -> None:
        _read_counter.increment()
        _read_counter.reset()
        assert _read_counter.count == 0

    def test_max_reads_constant_value(self) -> None:
        assert _MAX_READS >= 1

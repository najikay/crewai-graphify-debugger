"""Unit tests for agent tools (read_vault_document, read_code_slice, apply_patch)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from crewai_graphify.agents.tools import (
    _MAX_READS,
    _read_counter,
    apply_patch,
    read_code_slice,
    read_vault_document,
)

_VAULT = "crewai_graphify.agents.tools._VAULT"
_TARGET = "crewai_graphify.agents.tools._TARGET"


# ---------------------------------------------------------------------------
# Autouse fixture — resets the read counter before every test in this module
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_read_counter() -> None:  # type: ignore[return]
    _read_counter.reset()
    yield
    _read_counter.reset()


# ---------------------------------------------------------------------------
# read_vault_document
# ---------------------------------------------------------------------------


class TestReadVaultDocument:
    def test_returns_file_content(self, tmp_path: Path) -> None:
        doc = tmp_path / "hot.md"
        doc.write_text("# Hot nodes\n- Polygon", encoding="utf-8")
        with patch(_VAULT, tmp_path):
            result = read_vault_document._run(filename="hot.md")
        assert "Hot nodes" in result

    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        with patch(_VAULT, tmp_path):
            result = read_vault_document._run(filename="missing.md")
        assert "[ERROR]" in result
        assert "missing.md" in result

    def test_reads_exact_content(self, tmp_path: Path) -> None:
        content = "line1\nline2\nline3"
        (tmp_path / "index.md").write_text(content, encoding="utf-8")
        with patch(_VAULT, tmp_path):
            result = read_vault_document._run(filename="index.md")
        assert result == content

    def test_error_message_contains_filename(self, tmp_path: Path) -> None:
        with patch(_VAULT, tmp_path):
            result = read_vault_document._run(filename="no_such.md")
        assert "no_such.md" in result

    def test_func_attribute_is_callable(self) -> None:
        assert callable(read_vault_document.func)

    def test_tool_name(self) -> None:
        assert read_vault_document.name == "read_vault_document"


# ---------------------------------------------------------------------------
# read_code_slice
# ---------------------------------------------------------------------------


class TestReadCodeSlice:
    def test_returns_requested_lines(self, tmp_path: Path) -> None:
        src = "\n".join(f"line{i}" for i in range(1, 11))
        (tmp_path / "main.py").write_text(src, encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="main.py", start_line=2, end_line=4)
        assert "line2" in result
        assert "line4" in result
        assert "line5" not in result

    def test_header_contains_filename_and_range(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("a\nb\nc", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="app.py", start_line=1, end_line=2)
        assert "app.py" in result
        assert "1" in result and "2" in result

    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="nope.py", start_line=1, end_line=5)
        assert "[ERROR]" in result
        assert "nope.py" in result

    def test_invalid_start_line_zero(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("x", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="f.py", start_line=0, end_line=1)
        assert "[ERROR]" in result

    def test_end_before_start_returns_error(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("x\ny", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="f.py", start_line=5, end_line=3)
        assert "[ERROR]" in result

    def test_out_of_range_returns_error(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("only one line", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="f.py", start_line=99, end_line=100)
        assert "[ERROR]" in result

    def test_clamps_end_to_file_length(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("a\nb\nc", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="f.py", start_line=2, end_line=999)
        assert "b" in result and "c" in result

    def test_tool_name(self) -> None:
        assert read_code_slice.name == "read_code_slice"

    def test_func_attribute_is_callable(self) -> None:
        assert callable(read_code_slice.func)


# ---------------------------------------------------------------------------
# read_code_slice — read-cap enforcement
# ---------------------------------------------------------------------------


class TestReadCodeSliceCap:
    def test_cap_enforced_after_max_reads(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("x", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            for _ in range(_MAX_READS):
                read_code_slice._run(file_path="f.py", start_line=1, end_line=1)
            result = read_code_slice._run(file_path="f.py", start_line=1, end_line=1)
        assert "[ERROR]" in result
        assert "cap" in result.lower()

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
        _read_counter.increment()
        _read_counter.reset()
        assert _read_counter.count == 0

    def test_max_reads_constant_value(self) -> None:
        assert _MAX_READS >= 1


# ---------------------------------------------------------------------------
# apply_patch
# ---------------------------------------------------------------------------


class TestApplyPatch:
    def test_replaces_original_with_new(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = apply_patch._run(file_path="f.py", original_code="x = 1", new_code="x = 10")
        assert "Patch applied" in result
        assert (tmp_path / "f.py").read_text(encoding="utf-8") == "x = 10\ny = 2\n"

    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        with patch(_TARGET, tmp_path):
            result = apply_patch._run(file_path="nope.py", original_code="x", new_code="y")
        assert "[ERROR]" in result
        assert "nope.py" in result

    def test_original_not_found_returns_error(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("x = 1\n", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = apply_patch._run(file_path="f.py", original_code="NOTHERE", new_code="y")
        assert "[ERROR]" in result

    def test_only_first_occurrence_replaced(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("a\na\n", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            apply_patch._run(file_path="f.py", original_code="a", new_code="b")
        assert (tmp_path / "f.py").read_text(encoding="utf-8") == "b\na\n"

    def test_result_contains_replaced_char_count(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("hello world", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = apply_patch._run(
                file_path="f.py", original_code="hello world", new_code="bye"
            )
        assert "11" in result  # len("hello world") == 11

    def test_tool_name(self) -> None:
        assert apply_patch.name == "apply_patch"

    def test_func_attribute_is_callable(self) -> None:
        assert callable(apply_patch.func)

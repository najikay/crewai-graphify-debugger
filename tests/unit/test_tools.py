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
    reset_read_cap,
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

    def test_path_traversal_raises_value_error(self, tmp_path: Path) -> None:
        with patch(_TARGET, tmp_path), pytest.raises(ValueError, match="Path outside target directory"):
            read_code_slice._run(file_path="../../etc/passwd", start_line=1, end_line=5)

    def test_glob_fallback_finds_unique_file_by_name(self, tmp_path: Path) -> None:
        """Glob fallback resolves a file nested deeper than the agent's path."""
        nested = tmp_path / "sub" / "dir"
        nested.mkdir(parents=True)
        (nested / "target.py").write_text("found it\nline2", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="target.py", start_line=1, end_line=1)
        assert "found it" in result

    def test_glob_fallback_multiple_matches_returns_not_found(self, tmp_path: Path) -> None:
        """Glob with multiple name matches returns file-not-found to avoid ambiguity."""
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        (tmp_path / "a" / "dup.py").write_text("x", encoding="utf-8")
        (tmp_path / "b" / "dup.py").write_text("x", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = read_code_slice._run(file_path="dup.py", start_line=1, end_line=1)
        assert "[ERROR]" in result

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

    def test_reset_read_cap_clears_counter(self) -> None:
        """The public reset_read_cap() must zero the process-global counter."""
        _read_counter.increment()
        _read_counter.increment()
        reset_read_cap()
        assert _read_counter.count == 0

    def test_reads_work_again_after_reset(self, tmp_path: Path) -> None:
        """After hitting the cap, reset_read_cap() must un-brick read_code_slice."""
        (tmp_path / "f.py").write_text("hello", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            for _ in range(_MAX_READS + 2):  # blow past the cap
                read_code_slice._run(file_path="f.py", start_line=1, end_line=1)
            reset_read_cap()
            result = read_code_slice._run(file_path="f.py", start_line=1, end_line=1)
        assert "[ERROR]" not in result
        assert "hello" in result

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
            result = apply_patch._run(file_path="nope.py", original_code="x = 1", new_code="y = 2")
        assert "[ERROR]" in result
        assert "nope.py" in result

    def test_original_not_found_returns_error(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("x = 1\n", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = apply_patch._run(file_path="f.py", original_code="NOTHERE", new_code="y")
        assert "[ERROR]" in result

    def test_only_first_occurrence_replaced(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("aaaa\naaaa\n", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            apply_patch._run(file_path="f.py", original_code="aaaa", new_code="bbbb")
        assert (tmp_path / "f.py").read_text(encoding="utf-8") == "bbbb\naaaa\n"

    def test_identical_code_rejected_as_trivial(self, tmp_path: Path) -> None:
        """original_code == new_code is a no-op patch and must be rejected."""
        (tmp_path / "f.py").write_text("print('hi')\n", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = apply_patch._run(
                file_path="f.py", original_code="print", new_code="print"
            )
        assert "[ERROR]" in result
        assert "identical" in result.lower()
        assert (tmp_path / "f.py").read_text(encoding="utf-8") == "print('hi')\n"

    def test_too_short_target_rejected_as_trivial(self, tmp_path: Path) -> None:
        """A target snippet below the min non-space length must be rejected."""
        (tmp_path / "f.py").write_text("x = 1\n", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = apply_patch._run(file_path="f.py", original_code="x", new_code="z")
        assert "[ERROR]" in result
        assert "trivial" in result.lower()
        assert (tmp_path / "f.py").read_text(encoding="utf-8") == "x = 1\n"

    def test_result_contains_replaced_char_count(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("hello world", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = apply_patch._run(
                file_path="f.py", original_code="hello world", new_code="bye"
            )
        assert "11" in result  # len("hello world") == 11

    def test_path_traversal_raises_value_error(self, tmp_path: Path) -> None:
        with patch(_TARGET, tmp_path), pytest.raises(ValueError, match="Path outside target directory"):
            apply_patch._run(file_path="../../secret.py", original_code="x", new_code="y")

    def test_glob_fallback_patches_file_by_name(self, tmp_path: Path) -> None:
        """apply_patch resolves via glob when exact path doesn't exist."""
        nested = tmp_path / "sub"
        nested.mkdir()
        (nested / "fix.py").write_text("x = 1\n", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = apply_patch._run(file_path="fix.py", original_code="x = 1", new_code="x = 99")
        assert "Patch applied" in result
        assert (nested / "fix.py").read_text(encoding="utf-8") == "x = 99\n"

    def test_tool_name(self) -> None:
        assert apply_patch.name == "apply_patch"

    def test_func_attribute_is_callable(self) -> None:
        assert callable(apply_patch.func)

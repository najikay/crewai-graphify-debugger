"""Unit tests for apply_patch + path resolution (path-traversal, glob fallback, trivial-guard)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from crewai_graphify.agents.tools import _read_counter, apply_patch, read_code_slice

_TARGET = "crewai_graphify.agents.tools._TARGET"


@pytest.fixture(autouse=True)
def _reset_read_counter() -> None:  # type: ignore[return]
    _read_counter.reset()
    yield
    _read_counter.reset()


class TestReadCodeSliceResolution:
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
        """Multiple name matches → file-not-found, to avoid ambiguity."""
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        (tmp_path / "a" / "dup.py").write_text("x", encoding="utf-8")
        (tmp_path / "b" / "dup.py").write_text("x", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            assert "[ERROR]" in read_code_slice._run(file_path="dup.py", start_line=1, end_line=1)


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
        assert "[ERROR]" in result and "nope.py" in result

    def test_original_not_found_returns_error(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("x = 1\n", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            assert "[ERROR]" in apply_patch._run(file_path="f.py", original_code="NOTHERE", new_code="y")

    def test_only_first_occurrence_replaced(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("aaaa\naaaa\n", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            apply_patch._run(file_path="f.py", original_code="aaaa", new_code="bbbb")
        assert (tmp_path / "f.py").read_text(encoding="utf-8") == "bbbb\naaaa\n"

    def test_identical_code_rejected_as_trivial(self, tmp_path: Path) -> None:
        """original_code == new_code is a no-op patch and must be rejected."""
        (tmp_path / "f.py").write_text("print('hi')\n", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = apply_patch._run(file_path="f.py", original_code="print", new_code="print")
        assert "[ERROR]" in result and "identical" in result.lower()
        assert (tmp_path / "f.py").read_text(encoding="utf-8") == "print('hi')\n"

    def test_too_short_target_rejected_as_trivial(self, tmp_path: Path) -> None:
        """A target snippet below the min non-space length must be rejected."""
        (tmp_path / "f.py").write_text("x = 1\n", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = apply_patch._run(file_path="f.py", original_code="x", new_code="z")
        assert "[ERROR]" in result and "trivial" in result.lower()
        assert (tmp_path / "f.py").read_text(encoding="utf-8") == "x = 1\n"

    def test_result_contains_replaced_char_count(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("hello world", encoding="utf-8")
        with patch(_TARGET, tmp_path):
            result = apply_patch._run(file_path="f.py", original_code="hello world", new_code="bye")
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

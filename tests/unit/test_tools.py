"""Unit tests for agent tools (read_vault_document, read_code_slice)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from crewai_graphify.agents.tools import read_code_slice, read_vault_document

_VAULT = "crewai_graphify.agents.tools._VAULT"
_TARGET = "crewai_graphify.agents.tools._TARGET"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_exists(path: Path, *, exists: bool) -> bool:  # type: ignore[return]
    return exists


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

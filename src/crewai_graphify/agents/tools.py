"""Agent tools — file-system accessors for vault documents and code slices.

All paths are resolved relative to ``workspace/`` so agents are sandboxed
to the local repository.  Tools return plain strings for direct LLM consumption.
"""
from __future__ import annotations

from pathlib import Path

from crewai.tools import tool

__all__ = ["apply_patch", "read_code_slice", "read_vault_document"]

_VAULT = Path("workspace/vault")
_TARGET = Path("workspace/target")
_MAX_READS = 5


class _ReadCounter:
    """Caps read_code_slice calls per run; reset between pipeline invocations."""

    def __init__(self) -> None:
        self._count = 0

    def increment(self) -> int:
        self._count += 1
        return self._count

    def reset(self) -> None:
        self._count = 0

    @property
    def count(self) -> int:
        return self._count


_read_counter = _ReadCounter()


@tool("read_vault_document")
def read_vault_document(filename: str) -> str:
    """Read a markdown document from the Obsidian vault.

    Use this tool to read graph summaries, hot-node lists, or index files
    produced by the graph builder.  Pass only the file *name* (e.g.
    ``hot.md``), not a full path.
    """
    path = _VAULT / filename
    if not path.exists():
        return f"[ERROR] Vault document not found: {filename}"
    return path.read_text(encoding="utf-8")


@tool("read_code_slice")
def read_code_slice(file_path: str, start_line: int, end_line: int) -> str:
    """Read a contiguous slice of lines from a Python source file.

    ``file_path`` is relative to ``workspace/target/``.  ``start_line`` and
    ``end_line`` are 1-based and inclusive.  Capped at _MAX_READS per run.
    """
    if _read_counter.increment() > _MAX_READS:
        return f"[ERROR] Read cap reached ({_MAX_READS} reads maximum per run)."
    if start_line < 1 or end_line < start_line:
        return "[ERROR] start_line must be ≥ 1 and ≤ end_line."
    path = _TARGET / file_path
    if not path.exists():
        return f"[ERROR] Source file not found: {file_path}"
    lines = path.read_text(encoding="utf-8").splitlines()
    total = len(lines)
    lo, hi = max(0, start_line - 1), min(total, end_line)
    selected = lines[lo:hi]
    if not selected:
        return f"[ERROR] No lines in range {start_line}–{end_line} (file has {total} lines)."
    return f"# {file_path} lines {start_line}–{end_line}\n" + "\n".join(selected)


@tool("apply_patch")
def apply_patch(file_path: str, original_code: str, new_code: str) -> str:
    """Replace ``original_code`` with ``new_code`` in a target file (first match).

    ``file_path`` is relative to ``workspace/target/``.  Returns an error
    string if the file does not exist or the original snippet is not found.
    """
    path = _TARGET / file_path
    if not path.exists():
        return f"[ERROR] Target file not found: {file_path}"
    source = path.read_text(encoding="utf-8")
    if original_code not in source:
        return f"[ERROR] original_code not found in {file_path}."
    patched = source.replace(original_code, new_code, 1)
    path.write_text(patched, encoding="utf-8")
    return f"Patch applied to {file_path}: replaced {len(original_code)} chars."

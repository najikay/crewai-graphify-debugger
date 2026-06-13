"""Agent tools — file-system accessors for vault documents and code slices.

All paths are resolved relative to ``workspace/`` so agents are sandboxed
to the local repository.  Both tools return a plain string; the agent LLM
receives the content directly.
"""
from __future__ import annotations

from pathlib import Path

from crewai.tools import tool

__all__ = ["read_vault_document", "read_code_slice"]

_VAULT = Path("workspace/vault")
_TARGET = Path("workspace/target")


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
    """Read a contiguous slice of lines from a Python source file in the target.

    ``file_path`` is relative to ``workspace/target/`` (e.g. ``main.py``).
    ``start_line`` and ``end_line`` are 1-based and inclusive.  At least one
    line must be requested; the tool refuses to dump entire files to keep
    token usage minimal.
    """
    if start_line < 1 or end_line < start_line:
        return "[ERROR] start_line must be ≥ 1 and ≤ end_line."
    path = _TARGET / file_path
    if not path.exists():
        return f"[ERROR] Source file not found: {file_path}"
    lines = path.read_text(encoding="utf-8").splitlines()
    total = len(lines)
    lo = max(0, start_line - 1)
    hi = min(total, end_line)
    selected = lines[lo:hi]
    if not selected:
        return f"[ERROR] No lines in range {start_line}–{end_line} (file has {total} lines)."
    header = f"# {file_path} lines {start_line}–{end_line}\n"
    return header + "\n".join(selected)

"""Agent tools — file-system accessors for vault documents and code slices.

All paths are resolved relative to ``workspace/`` so agents are sandboxed
to the local repository.  Tools return plain strings for direct LLM consumption.
"""
from __future__ import annotations

import os
from pathlib import Path

from crewai.tools import tool

__all__ = ["apply_patch", "read_code_slice", "read_vault_document", "reset_read_cap"]

_VAULT = Path("workspace/vault")
_TARGET = Path("workspace/target")
_MAX_READS = 5
_MIN_PATCH_LEN = 4  # min non-space chars in original_code — blocks trivial/no-op patches


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


def reset_read_cap() -> None:
    """Reset the per-run read counter to 0.

    The read counter is process-global, so in a long-running server it survives
    between pipeline runs.  Without this reset the second run would start already
    at the cap and the Reader agent would be bricked on its first ``read_code_slice``
    call.  Invoked by ``build_crew()`` so every run (and retry) starts fresh.
    """
    _read_counter.reset()


def _resolve_target_path(file_path: str) -> Path:
    """Locate ``file_path`` inside _TARGET; glob-fallback on filename if not found.

    If the exact path ``_TARGET / file_path`` exists it is returned immediately.
    Otherwise searches ``_TARGET`` recursively for a file whose *name* matches
    the basename of ``file_path``.  This handles agents that pass a partial path
    (e.g. ``broken-python/polygons.py``) when the real location is a sub-folder
    (``broken-python/polygons/polygons.py``).  Returns the unique match when
    exactly one file matches; returns the original unresolved path otherwise so
    callers receive a consistent ``path.exists() == False`` signal.
    """
    exact = _TARGET / file_path
    if exact.exists():
        return exact
    name = Path(file_path).name
    matches = [p for p in _TARGET.rglob(name) if p.is_file()]
    return matches[0] if len(matches) == 1 else exact


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

    Action Input MUST be a flat JSON object with EXACTLY these keys:
      "file_path"  : string  — path relative to workspace/target/
                               (e.g. "broken-python/polygons.py")
      "start_line" : integer — first line to read, 1-based inclusive
      "end_line"   : integer — last line to read, 1-based inclusive
    Example: {"file_path": "broken-python/f.py", "start_line": 1, "end_line": 20}
    Capped at _MAX_READS calls per pipeline run.
    """
    target_abs = os.path.abspath(str(_TARGET))
    resolved = os.path.abspath(str(_TARGET / file_path))
    if not resolved.startswith(target_abs + os.sep):
        raise ValueError("Path outside target directory")
    if _read_counter.increment() > _MAX_READS:
        return f"[ERROR] Read cap reached ({_MAX_READS} reads maximum per run)."
    if start_line < 1 or end_line < start_line:
        return "[ERROR] start_line must be ≥ 1 and ≤ end_line."
    path = _resolve_target_path(file_path)
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
    """Replace original_code with new_code in a target source file (first match).

    Action Input MUST be a flat JSON object with EXACTLY these keys:
      "file_path"     : string — path relative to workspace/target/
                                 (e.g. "broken-python/polygons.py")
      "original_code" : string — the exact verbatim snippet to replace
      "new_code"      : string — the replacement code
    Example: {"file_path": "broken-python/f.py", "original_code": "x=1", "new_code": "x=2"}
    Rejects no-op patches (original_code == new_code) and trivially short targets.
    Returns an error string if the file does not exist or the snippet is not found.
    """
    target_abs = os.path.abspath(str(_TARGET))
    resolved = os.path.abspath(str(_TARGET / file_path))
    if not resolved.startswith(target_abs + os.sep):
        raise ValueError("Path outside target directory")
    if original_code == new_code:
        return "[ERROR] Trivial patch rejected: original_code is identical to new_code."
    if len(original_code.strip()) < _MIN_PATCH_LEN:
        return (
            f"[ERROR] Trivial patch rejected: original_code has < {_MIN_PATCH_LEN} "
            "non-space chars — provide a real, specific snippet to replace."
        )
    path = _resolve_target_path(file_path)
    if not path.exists():
        return f"[ERROR] Target file not found: {file_path}"
    source = path.read_text(encoding="utf-8")
    if original_code not in source:
        return f"[ERROR] original_code not found in {file_path}."
    patched = source.replace(original_code, new_code, 1)
    path.write_text(patched, encoding="utf-8")
    return f"Patch applied to {file_path}: replaced {len(original_code)} chars."

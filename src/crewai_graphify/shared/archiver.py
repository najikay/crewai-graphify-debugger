"""Post-run validation gate and result archiver.

Compares ``workspace/target/broken-python/`` against the pristine fixture to
verify that agents made real on-disk changes, then archives the run output
together with a unified diff of every modified file.
"""
from __future__ import annotations

import difflib
import filecmp
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

__all__ = ["archive_run"]

_TARGET = Path("workspace/target")
_FIXTURE = Path("fixtures/original_buggy")
_RESULTS = Path("workspace/results")


def _detect_changes() -> list[Path]:
    """Return .py files under workspace/target/broken-python/ that differ from fixture."""
    target_root = _TARGET / "broken-python"
    if not target_root.exists():
        return []
    changed: list[Path] = []
    for src in sorted(target_root.rglob("*.py")):
        rel = src.relative_to(target_root)
        fix = _FIXTURE / rel
        if not fix.exists() or not filecmp.cmp(str(src), str(fix), shallow=False):
            changed.append(src)
    return changed


def _unified_diff(changed: list[Path]) -> str:
    """Build a unified diff of every changed file against its pristine fixture."""
    target_root = _TARGET / "broken-python"
    blocks: list[str] = []
    for src in changed:
        rel = src.relative_to(target_root)
        fix = _FIXTURE / rel
        old = fix.read_text(encoding="utf-8").splitlines() if fix.exists() else []
        new = src.read_text(encoding="utf-8").splitlines()
        diff = difflib.unified_diff(
            old, new, fromfile=f"a/{rel}", tofile=f"b/{rel}", lineterm=""
        )
        block = "\n".join(diff)
        if block:
            blocks.append(block)
    return "\n\n".join(blocks)


def archive_run(result: str, push_log: Callable[[str], None]) -> None:
    """Validate on-disk changes; archive run to workspace/results/ if changes exist.

    Pushes an SSE message for either outcome so the UI always gets feedback.
    On success the target tree is copied to a timestamped run folder and a
    ``run_summary.txt`` (file list + unified diff + agent answer) is written.
    """
    changed = _detect_changes()
    if not changed:
        push_log(
            "❌ VALIDATION FAILED: Agents reported success, "
            "but no physical changes were detected on disk."
        )
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = _RESULTS / f"run_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(_TARGET, run_dir / "target", dirs_exist_ok=True)
    names = ", ".join(str(f.relative_to(_TARGET)) for f in changed)
    (run_dir / "run_summary.txt").write_text(
        f"Run: {stamp}\n"
        f"Files modified ({len(changed)}): {names}\n\n"
        f"=== Unified Diff (vs pristine fixture) ===\n{_unified_diff(changed)}\n\n"
        f"=== Agent Final Answer ===\n{result}\n",
        encoding="utf-8",
    )
    push_log(
        f"✅ VALIDATION PASSED: Changes verified. "
        f"Repository archived to workspace/results/run_{stamp}"
    )
    # A real on-disk change can alter the AST (e.g. a newly added function call),
    # so regenerate graph.json + index.md + hot.md from the patched target tree.
    # Lazy import keeps shared.archiver and shared.fixture_setup free of any cycle.
    from crewai_graphify.shared.fixture_setup import _rebuild_vault_graph

    push_log("INFO: Patch changed the code structure — rebuilding vault graph…")
    _rebuild_vault_graph(push_log)

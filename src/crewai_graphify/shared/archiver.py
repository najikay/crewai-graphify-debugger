"""Post-run validation gate and result archiver.

Compares ``workspace/target/broken-python/`` against the pristine fixture to
verify that agents made real on-disk changes, then archives the run output.
"""
from __future__ import annotations

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
    """Return files under workspace/target/broken-python/ that differ from fixture."""
    target_root = _TARGET / "broken-python"
    if not target_root.exists():
        return []
    changed: list[Path] = []
    for src in target_root.rglob("*.py"):
        rel = src.relative_to(target_root)
        fix = _FIXTURE / rel
        if not fix.exists() or not filecmp.cmp(str(src), str(fix), shallow=False):
            changed.append(src)
    return changed


def archive_run(result: str, push_log: Callable[[str], None]) -> None:
    """Validate on-disk changes; archive run to workspace/results/ if changes exist.

    Pushes an SSE message for either outcome so the UI always gets feedback.
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
        f"Run: {stamp}\nModified: {names}\n\nAgent output:\n{result}\n",
        encoding="utf-8",
    )
    push_log(
        f"✅ VALIDATION PASSED: Changes verified. "
        f"Repository archived to workspace/results/run_{stamp}"
    )

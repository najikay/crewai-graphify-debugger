"""Unit tests for the post-run validation gate and archiver."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from crewai_graphify.shared.archiver import _detect_changes, archive_run

_MOD = "crewai_graphify.shared.archiver"


def _make_workspace(
    tmp_path: Path,
    *,
    fixture_content: str = "x = 1",
    target_content: str = "x = 1",
) -> tuple[Path, Path, Path]:
    """Create a minimal target/fixture/results layout under tmp_path."""
    target = tmp_path / "target"
    fixture = tmp_path / "fixture"
    results = tmp_path / "results"
    (target / "broken-python").mkdir(parents=True)
    fixture.mkdir()
    (fixture / "f.py").write_text(fixture_content, encoding="utf-8")
    (target / "broken-python" / "f.py").write_text(target_content, encoding="utf-8")
    return target, fixture, results


class TestDetectChanges:
    def test_empty_when_target_missing(self, tmp_path: Path) -> None:
        with patch(f"{_MOD}._TARGET", tmp_path / "no_target"):
            assert _detect_changes() == []

    def test_empty_when_files_identical(self, tmp_path: Path) -> None:
        target, fixture, _ = _make_workspace(tmp_path)
        with patch(f"{_MOD}._TARGET", target), patch(f"{_MOD}._FIXTURE", fixture):
            assert _detect_changes() == []

    def test_returns_modified_file(self, tmp_path: Path) -> None:
        target, fixture, _ = _make_workspace(tmp_path, target_content="x = 99")
        with patch(f"{_MOD}._TARGET", target), patch(f"{_MOD}._FIXTURE", fixture):
            assert len(_detect_changes()) == 1

    def test_returns_file_absent_from_fixture(self, tmp_path: Path) -> None:
        target, fixture, _ = _make_workspace(tmp_path)
        (target / "broken-python" / "extra.py").write_text("y = 2", encoding="utf-8")
        with patch(f"{_MOD}._TARGET", target), patch(f"{_MOD}._FIXTURE", fixture):
            changed = _detect_changes()
        assert any(p.name == "extra.py" for p in changed)


class TestArchiveRun:
    def test_validation_failed_when_no_changes(self, tmp_path: Path) -> None:
        logs: list[str] = []
        target, fixture, _ = _make_workspace(tmp_path)
        with patch(f"{_MOD}._TARGET", target), patch(f"{_MOD}._FIXTURE", fixture):
            archive_run("result", logs.append)
        assert any("VALIDATION FAILED" in m for m in logs)

    def test_run_directory_created_on_success(self, tmp_path: Path) -> None:
        logs: list[str] = []
        target, fixture, results = _make_workspace(tmp_path, target_content="x = 99")
        with (
            patch(f"{_MOD}._TARGET", target),
            patch(f"{_MOD}._FIXTURE", fixture),
            patch(f"{_MOD}._RESULTS", results),
        ):
            archive_run("output", logs.append)
        assert any(d.name.startswith("run_") for d in results.iterdir())

    def test_run_summary_contains_agent_output(self, tmp_path: Path) -> None:
        logs: list[str] = []
        target, fixture, results = _make_workspace(tmp_path, target_content="changed")
        with (
            patch(f"{_MOD}._TARGET", target),
            patch(f"{_MOD}._FIXTURE", fixture),
            patch(f"{_MOD}._RESULTS", results),
        ):
            archive_run("agent said this", logs.append)
        summary = next(results.rglob("run_summary.txt")).read_text(encoding="utf-8")
        assert "agent said this" in summary

    def test_validation_passed_pushed_on_success(self, tmp_path: Path) -> None:
        logs: list[str] = []
        target, fixture, results = _make_workspace(tmp_path, target_content="changed")
        with (
            patch(f"{_MOD}._TARGET", target),
            patch(f"{_MOD}._FIXTURE", fixture),
            patch(f"{_MOD}._RESULTS", results),
        ):
            archive_run("output", logs.append)
        assert any("VALIDATION PASSED" in m for m in logs)

    def test_target_files_copied_to_run_dir(self, tmp_path: Path) -> None:
        logs: list[str] = []
        target, fixture, results = _make_workspace(tmp_path, target_content="patched!")
        with (
            patch(f"{_MOD}._TARGET", target),
            patch(f"{_MOD}._FIXTURE", fixture),
            patch(f"{_MOD}._RESULTS", results),
        ):
            archive_run("output", logs.append)
        archived = list(results.rglob("f.py"))
        assert archived and archived[0].read_text(encoding="utf-8") == "patched!"

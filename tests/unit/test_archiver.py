"""Unit tests for the post-run validation gate and archiver."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from crewai_graphify.shared.archiver import _detect_changes, archive_run

_MOD = "crewai_graphify.shared.archiver"


@pytest.fixture(autouse=True)
def _mock_rebuild():  # type: ignore[no-untyped-def]
    """Stub the heavy vault rebuild so archiver tests stay fast and side-effect free."""
    with patch("crewai_graphify.shared.fixture_setup._rebuild_vault_graph") as m:
        yield m


def _make_workspace(
    tmp_path: Path, *, fixture_content: str = "x = 1", target_content: str = "x = 1",
) -> tuple[Path, Path, Path]:
    """Create a minimal target/fixture/results layout under tmp_path."""
    target, fixture, results = tmp_path / "target", tmp_path / "fixture", tmp_path / "results"
    (target / "broken-python").mkdir(parents=True)
    fixture.mkdir()
    (fixture / "f.py").write_text(fixture_content, encoding="utf-8")
    (target / "broken-python" / "f.py").write_text(target_content, encoding="utf-8")
    return target, fixture, results


def _patched(target: Path, fixture: Path, results: Path | None = None):  # type: ignore[no-untyped-def]
    """Patch the archiver's module-level _TARGET/_FIXTURE/(_RESULTS) constants at once."""
    kw = {"_TARGET": target, "_FIXTURE": fixture}
    if results is not None:
        kw["_RESULTS"] = results
    return patch.multiple(_MOD, **kw)


class TestDetectChanges:
    def test_empty_when_target_missing(self, tmp_path: Path) -> None:
        with patch(f"{_MOD}._TARGET", tmp_path / "no_target"):
            assert _detect_changes() == []

    def test_empty_when_files_identical(self, tmp_path: Path) -> None:
        target, fixture, _ = _make_workspace(tmp_path)
        with _patched(target, fixture):
            assert _detect_changes() == []

    def test_returns_modified_file(self, tmp_path: Path) -> None:
        target, fixture, _ = _make_workspace(tmp_path, target_content="x = 99")
        with _patched(target, fixture):
            assert len(_detect_changes()) == 1

    def test_returns_file_absent_from_fixture(self, tmp_path: Path) -> None:
        target, fixture, _ = _make_workspace(tmp_path)
        (target / "broken-python" / "extra.py").write_text("y = 2", encoding="utf-8")
        with _patched(target, fixture):
            changed = _detect_changes()
        assert any(p.name == "extra.py" for p in changed)


class TestArchiveRun:
    def test_validation_failed_when_no_changes(self, tmp_path: Path) -> None:
        logs: list[str] = []
        target, fixture, _ = _make_workspace(tmp_path)
        with _patched(target, fixture):
            archive_run("result", logs.append)
        assert any("VALIDATION FAILED" in m for m in logs)

    def test_run_directory_created_on_success(self, tmp_path: Path) -> None:
        logs: list[str] = []
        target, fixture, results = _make_workspace(tmp_path, target_content="x = 99")
        with _patched(target, fixture, results):
            archive_run("output", logs.append)
        assert any(d.name.startswith("run_") for d in results.iterdir())

    def test_run_summary_contains_agent_output(self, tmp_path: Path) -> None:
        logs: list[str] = []
        target, fixture, results = _make_workspace(tmp_path, target_content="changed")
        with _patched(target, fixture, results):
            archive_run("agent said this", logs.append)
        summary = next(results.rglob("run_summary.txt")).read_text(encoding="utf-8")
        assert "agent said this" in summary

    def test_run_summary_contains_unified_diff(self, tmp_path: Path) -> None:
        logs: list[str] = []
        target, fixture, results = _make_workspace(tmp_path, target_content="x = 99")
        with _patched(target, fixture, results):
            archive_run("output", logs.append)
        summary = next(results.rglob("run_summary.txt")).read_text(encoding="utf-8")
        assert "Unified Diff" in summary and "-x = 1" in summary and "+x = 99" in summary

    def test_newline_only_change_archives_with_empty_diff_block(self, tmp_path: Path) -> None:
        """Byte-different but line-identical file still archives (empty-diff branch)."""
        logs: list[str] = []
        target, fixture, results = _make_workspace(tmp_path, fixture_content="x = 1\n", target_content="x = 1")
        with _patched(target, fixture, results):
            archive_run("output", logs.append)
        assert any("VALIDATION PASSED" in m for m in logs)

    def test_validation_passed_pushed_on_success(self, tmp_path: Path) -> None:
        logs: list[str] = []
        target, fixture, results = _make_workspace(tmp_path, target_content="changed")
        with _patched(target, fixture, results):
            archive_run("output", logs.append)
        assert any("VALIDATION PASSED" in m for m in logs)

    def test_target_files_copied_to_run_dir(self, tmp_path: Path) -> None:
        logs: list[str] = []
        target, fixture, results = _make_workspace(tmp_path, target_content="patched!")
        with _patched(target, fixture, results):
            archive_run("output", logs.append)
        archived = list(results.rglob("f.py"))
        assert archived and archived[0].read_text(encoding="utf-8") == "patched!"


class TestGraphRebuild:
    def test_rebuild_called_on_success(self, tmp_path: Path, _mock_rebuild) -> None:  # type: ignore[no-untyped-def]
        """A real on-disk change must trigger a vault graph rebuild (new AST edges)."""
        target, fixture, results = _make_workspace(tmp_path, target_content="changed")
        with _patched(target, fixture, results):
            archive_run("output", lambda _m: None)
        assert _mock_rebuild.called

    def test_rebuild_not_called_on_validation_failure(self, tmp_path: Path, _mock_rebuild) -> None:  # type: ignore[no-untyped-def]
        """No physical change ⇒ validation fails and the graph is NOT rebuilt."""
        target, fixture, results = _make_workspace(tmp_path)
        with _patched(target, fixture, results):
            archive_run("output", lambda _m: None)
        assert not _mock_rebuild.called

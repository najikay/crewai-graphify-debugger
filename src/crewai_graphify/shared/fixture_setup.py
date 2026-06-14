"""Download the broken-python fixture and reset workspace/target/ before each run."""
from __future__ import annotations

import io
import shutil
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

_FIXTURE_DIR = Path("fixtures/original_buggy")
_TARGET_DIR = Path("workspace/target")
_VAULT_DIR = Path("workspace/vault")
_REPO_ZIP = (
    "https://github.com/martinpeck/broken-python/archive/refs/heads/master.zip"
)
_TMP_DIR = Path("fixtures/_tmp_download")


def _detect_archive_root(zf: zipfile.ZipFile) -> str:
    """Return the single top-level directory name from the ZIP, or a safe fallback."""
    roots = {entry.split("/")[0] for entry in zf.namelist() if "/" in entry}
    if len(roots) == 1:
        return next(iter(roots))
    return "broken-python-master"


def _download_fixture(push_log: Callable[[str], None]) -> None:
    """Fetch the broken-python repo from GitHub and unpack into fixtures/original_buggy/."""
    push_log("INFO: Downloading broken-python fixture from GitHub…")
    _FIXTURE_DIR.parent.mkdir(parents=True, exist_ok=True)
    if _TMP_DIR.exists():
        shutil.rmtree(_TMP_DIR)
    with urllib.request.urlopen(_REPO_ZIP, timeout=60) as resp:  # noqa: S310
        data: bytes = resp.read()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        archive_root = _detect_archive_root(zf)
        zf.extractall(_TMP_DIR)
    shutil.move(str(_TMP_DIR / archive_root), str(_FIXTURE_DIR))
    shutil.rmtree(_TMP_DIR, ignore_errors=True)
    push_log(f"INFO: Fixture saved to {_FIXTURE_DIR}")


def _reset_workspace(push_log: Callable[[str], None]) -> None:
    """Wipe workspace/target/ and copy a fresh clone from the pristine fixture."""
    push_log("INFO: Resetting workspace/target/ from pristine fixture…")
    if _TARGET_DIR.exists():
        for item in _TARGET_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    _TARGET_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(_FIXTURE_DIR, _TARGET_DIR / "broken-python")
    push_log("INFO: workspace/target/ reset — only broken-python files present.")


def _rebuild_vault_graph(push_log: Callable[[str], None]) -> None:
    """Re-parse workspace/target/ recursively and regenerate vault artefacts."""
    from crewai_graphify.models.graph import Edge, Graph, Node
    from crewai_graphify.services.graph_builder import GraphBuilder
    from crewai_graphify.services.obsidian_manager import ObsidianManager

    push_log("INFO: Rebuilding vault graph from workspace/target/ …")
    builder = GraphBuilder(vault_dir=_VAULT_DIR)
    seen: dict[str, Node] = {}
    all_edges: list[Edge] = []
    for py_file in sorted(_TARGET_DIR.rglob("*.py")):
        g = builder.build(py_file)
        for n in g.nodes:
            seen[n.id] = n
        all_edges.extend(g.edges)
    graph = Graph(file_path=str(_TARGET_DIR), nodes=list(seen.values()), edges=all_edges)
    builder.save_graph(graph)
    builder.save_index_md(graph)
    ObsidianManager(vault_dir=_VAULT_DIR).save_hot_md(graph)
    push_log(f"INFO: Vault rebuilt — {len(graph.nodes)} nodes, {len(graph.edges)} edges.")


def _fixture_is_valid() -> bool:
    """Return True if the fixture directory exists and contains files."""
    return _FIXTURE_DIR.exists() and any(_FIXTURE_DIR.iterdir())


def ensure_fixture(push_log: Callable[[str], None]) -> None:
    """Ensure fixtures/original_buggy/ exists, reset workspace/target/, rebuild vault graph."""
    if not _fixture_is_valid():
        _download_fixture(push_log)
    _reset_workspace(push_log)
    _rebuild_vault_graph(push_log)

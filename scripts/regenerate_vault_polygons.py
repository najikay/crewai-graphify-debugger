"""Regenerate the Obsidian vault from the polygons module ONLY (submission helper).

In the full multi-file merge every non-``__main__`` node has in-degree 1, so the
"Primary Target File" is decided by edge insertion order — and ``mathsquiz`` sorts
before ``polygons`` alphabetically, making mathsquiz the (misleading) primary
target. Building the vault from ``polygons/polygons.py`` alone makes
``calc_polygon_details`` → ``Polygon`` and ``polygons.py`` the organic hot path,
matching our documented ``class Polygon(Object)`` NameError fix.

Run before scripts/stage_obsidian.sh when staging the submission vault.
"""
from __future__ import annotations

from pathlib import Path

from crewai_graphify.services.graph_builder import GraphBuilder
from crewai_graphify.services.obsidian_manager import ObsidianManager

_VAULT = Path("workspace/vault")
_POLYGONS = Path("workspace/target/broken-python/polygons/polygons.py")


def main() -> None:
    builder = GraphBuilder(vault_dir=_VAULT)
    graph = builder.build(_POLYGONS)
    builder.save_graph(graph)
    builder.save_index_md(graph)
    ObsidianManager(vault_dir=_VAULT).save_hot_md(graph)
    print(
        f"Vault regenerated from {_POLYGONS} — "
        f"{len(graph.nodes)} nodes, {len(graph.edges)} edges."
    )


if __name__ == "__main__":
    main()

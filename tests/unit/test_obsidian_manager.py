"""Unit tests for ObsidianManager and Graph model helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from crewai_graphify.models.graph import Edge, EdgeType, Graph, Node, NodeType
from crewai_graphify.services.obsidian_manager import ObsidianManager


def _make_graph() -> Graph:
    nodes = [
        Node(id="__main__", name="__main__", node_type=NodeType.MODULE,
             file_path="t.py", start_line=1, end_line=10),
        Node(id="calc_polygon_details", name="calc_polygon_details",
             node_type=NodeType.FUNCTION, file_path="t.py", start_line=2, end_line=5),
        Node(id="Polygon", name="Polygon", node_type=NodeType.CLASS,
             file_path="t.py", start_line=6, end_line=9, docstring="A polygon."),
    ]
    edges = [
        Edge(source="__main__", target="calc_polygon_details",
             edge_type=EdgeType.CALLS, weight=0.9),
        Edge(source="calc_polygon_details", target="Polygon",
             edge_type=EdgeType.INSTANTIATES, weight=0.8),
    ]
    return Graph(file_path="t.py", nodes=nodes, edges=edges)


@pytest.fixture()
def graph() -> Graph:
    return _make_graph()


@pytest.fixture()
def manager(tmp_path: Path) -> ObsidianManager:
    return ObsidianManager(vault_dir=tmp_path)


class TestHotNodes:
    def test_sorted_by_centrality(self, manager: ObsidianManager, graph: Graph) -> None:
        scores = [s for _, s in manager.compute_hot_nodes(graph)]
        assert scores == sorted(scores, reverse=True)

    def test_all_nodes_included(self, manager: ObsidianManager, graph: Graph) -> None:
        ids = {n.id for n, _ in manager.compute_hot_nodes(graph)}
        assert {"__main__", "Polygon", "calc_polygon_details"} <= ids

    def test_mid_node_highest_centrality(self, manager: ObsidianManager, graph: Graph) -> None:
        by_id = {n.id: s for n, s in manager.compute_hot_nodes(graph)}
        assert by_id["calc_polygon_details"] == pytest.approx(1.0)

    def test_empty_graph_returns_empty(self, manager: ObsidianManager) -> None:
        assert manager.compute_hot_nodes(Graph(file_path="x.py")) == []


class TestBugChain:
    def test_starts_at_main(self, manager: ObsidianManager, graph: Graph) -> None:
        assert manager.trace_bug_chain(graph)[0] == "__main__"

    def test_full_chain(self, manager: ObsidianManager, graph: Graph) -> None:
        assert manager.trace_bug_chain(graph) == ["__main__", "calc_polygon_details", "Polygon"]

    def test_no_cycles(self, manager: ObsidianManager, graph: Graph) -> None:
        chain = manager.trace_bug_chain(graph)
        assert len(chain) == len(set(chain))


class TestSaveHotMd:
    def test_creates_file(self, manager: ObsidianManager, graph: Graph) -> None:
        out = manager.save_hot_md(graph)
        assert out.exists() and out.stat().st_size > 0

    def test_bug_chain_section_present(self, manager: ObsidianManager, graph: Graph) -> None:
        assert "## Bug Call Chain" in manager.save_hot_md(graph).read_text()

    def test_chain_nodes_in_content(self, manager: ObsidianManager, graph: Graph) -> None:
        content = manager.save_hot_md(graph).read_text()
        assert "calc_polygon_details" in content and "Polygon" in content

    def test_primary_target_file_present(self, manager: ObsidianManager, graph: Graph) -> None:
        assert "Primary Target File" in manager.save_hot_md(graph).read_text()

    def test_root_cause_node_present(self, manager: ObsidianManager, graph: Graph) -> None:
        assert "Root-Cause Node" in manager.save_hot_md(graph).read_text()

    def test_nodes_in_primary_file_section(self, manager: ObsidianManager, graph: Graph) -> None:
        assert "## Nodes in Primary Target File" in manager.save_hot_md(graph).read_text()

    def test_empty_graph_falls_back_to_graph_file_path(self, manager: ObsidianManager) -> None:
        empty = Graph(file_path="x.py")
        content = manager.save_hot_md(empty).read_text()
        assert "x.py" in content

    def test_docstring_rendered(self, manager: ObsidianManager, graph: Graph) -> None:
        assert "A polygon." in manager.save_hot_md(graph).read_text()


class TestLoadGraph:
    def test_round_trip(self, manager: ObsidianManager, graph: Graph) -> None:
        (manager.vault_dir / "graph.json").write_text(graph.model_dump_json())
        loaded = manager.load_graph()
        assert loaded.file_path == graph.file_path and len(loaded.nodes) == len(graph.nodes)


class TestGraphHelpers:
    def test_node_by_id_found(self, graph: Graph) -> None:
        assert graph.node_by_id("Polygon") is not None

    def test_node_by_id_missing(self, graph: Graph) -> None:
        assert graph.node_by_id("missing") is None

    def test_edges_from(self, graph: Graph) -> None:
        assert graph.edges_from("__main__")[0].target == "calc_polygon_details"

    def test_edges_to(self, graph: Graph) -> None:
        assert graph.edges_to("Polygon")[0].source == "calc_polygon_details"

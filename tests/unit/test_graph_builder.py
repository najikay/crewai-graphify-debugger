"""Unit tests for GraphBuilder."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from crewai_graphify.models.graph import EdgeType, Graph, NodeType
from crewai_graphify.services.graph_builder import GraphBuilder

TARGET = Path("workspace/target/broken-python/polygons/polygons.py")


@pytest.fixture()
def builder(tmp_path: Path) -> GraphBuilder:
    return GraphBuilder(vault_dir=tmp_path)


@pytest.fixture()
def graph(builder: GraphBuilder) -> Graph:
    return builder.build(TARGET)


class TestNodeCollection:
    def test_module_node_present(self, graph: Graph) -> None:
        assert "__main__" in {n.id for n in graph.nodes}

    def test_class_node_present(self, graph: Graph) -> None:
        assert "Polygon" in {n.id for n in graph.nodes}

    def test_function_nodes_present(self, graph: Graph) -> None:
        ids = {n.id for n in graph.nodes}
        assert "calc_polygon_details" in ids and "draw_polygon" in ids

    def test_method_node_present(self, graph: Graph) -> None:
        assert any("Polygon." in nid for nid in {n.id for n in graph.nodes})

    def test_node_types_correct(self, graph: Graph) -> None:
        by_id = {n.id: n for n in graph.nodes}
        assert by_id["__main__"].node_type == NodeType.MODULE
        assert by_id["Polygon"].node_type == NodeType.CLASS
        assert by_id["calc_polygon_details"].node_type == NodeType.FUNCTION


class TestEdgeCollection:
    def test_instantiates_edge_exists(self, graph: Graph) -> None:
        edge = next(
            (e for e in graph.edges
             if e.source == "calc_polygon_details" and e.target == "Polygon"),
            None,
        )
        assert edge is not None and edge.edge_type == EdgeType.INSTANTIATES

    def test_calls_edges_from_main(self, graph: Graph) -> None:
        assert "__main__" in {e.source for e in graph.edges}

    def test_edge_weights_in_range(self, graph: Graph) -> None:
        assert all(0.0 <= e.weight <= 1.0 for e in graph.edges)


class TestSanitize:
    def test_new_keyword_stripped(self, builder: GraphBuilder, tmp_path: Path) -> None:
        src = tmp_path / "broken.py"
        src.write_text("class Foo:\n    pass\ndef bar():\n    x = new Foo()\n")
        g = builder.build(src)
        assert any(n.id == "Foo" for n in g.nodes)

    def test_build_does_not_raise(self, builder: GraphBuilder) -> None:
        assert len(builder.build(TARGET).nodes) >= 4

    def test_subscript_call_ignored(self, builder: GraphBuilder, tmp_path: Path) -> None:
        """Covers _call_name() return-None branch (func is neither Name nor Attribute)."""
        src = tmp_path / "sub.py"
        src.write_text("funcs = [print]\nfuncs[0]()\n")
        g = builder.build(src)
        assert len(g.edges) == 0

    def test_recursive_call_excluded(self, builder: GraphBuilder, tmp_path: Path) -> None:
        """Covers callee == scope branch — self-calls must not produce edges."""
        src = tmp_path / "rec.py"
        src.write_text("def fib(n: int) -> int:\n    return fib(n - 1) if n > 0 else 0\n")
        g = builder.build(src)
        assert not any(e.source == "fib" and e.target == "fib" for e in g.edges)

    def test_syntax_error_creates_fallback_node(self, builder: GraphBuilder, tmp_path: Path) -> None:
        """Python 2 syntax triggers SyntaxError → single __main__ MODULE node, no edges."""
        src = tmp_path / "py2.py"
        src.write_text('print "hello"\n')
        g = builder.build(src)
        assert len(g.nodes) == 1
        assert g.nodes[0].id == "__main__"
        assert g.nodes[0].node_type.value == "module"
        assert len(g.edges) == 0


class TestPersistence:
    def test_save_graph_writes_json(self, builder: GraphBuilder, graph: Graph) -> None:
        out = builder.save_graph(graph)
        assert out.exists() and out.stat().st_size > 0

    def test_save_graph_valid_json(self, builder: GraphBuilder, graph: Graph) -> None:
        data = json.loads(builder.save_graph(graph).read_text())
        assert "nodes" in data and "edges" in data

    def test_save_index_md_has_sections(self, builder: GraphBuilder, graph: Graph) -> None:
        content = builder.save_index_md(graph).read_text()
        assert "## Nodes" in content and "## Edges" in content

    def test_save_index_md_contains_node(self, builder: GraphBuilder, graph: Graph) -> None:
        assert "calc_polygon_details" in builder.save_index_md(graph).read_text()

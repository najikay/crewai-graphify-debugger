"""Unit tests for GraphBuilder and Graph.merge."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from crewai_graphify.models.graph import Edge, EdgeType, Graph, Node, NodeType
from crewai_graphify.services.graph_builder import GraphBuilder

TARGET = Path("workspace/target/broken-python/polygons/polygons.py")


def _mnode(node_id: str) -> Node:
    return Node(id=node_id, name=node_id, node_type=NodeType.FUNCTION, file_path="f.py",
                start_line=1, end_line=2)


def _medge(src: str, tgt: str) -> Edge:
    return Edge(source=src, target=tgt, edge_type=EdgeType.CALLS, weight=0.9)


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
        edge = next((e for e in graph.edges
                     if e.source == "calc_polygon_details" and e.target == "Polygon"), None)
        assert edge is not None and edge.edge_type == EdgeType.INSTANTIATES

    def test_calls_edges_from_main(self, graph: Graph) -> None:
        assert "__main__" in {e.source for e in graph.edges}

    def test_edge_weights_in_range(self, graph: Graph) -> None:
        assert all(0.0 <= e.weight <= 1.0 for e in graph.edges)


class TestSanitize:
    def test_new_keyword_stripped(self, builder: GraphBuilder, tmp_path: Path) -> None:
        src = tmp_path / "broken.py"
        src.write_text("class Foo:\n    pass\ndef bar():\n    x = new Foo()\n")
        assert any(n.id == "Foo" for n in builder.build(src).nodes)

    def test_build_does_not_raise(self, builder: GraphBuilder) -> None:
        assert len(builder.build(TARGET).nodes) >= 4

    def test_subscript_call_ignored(self, builder: GraphBuilder, tmp_path: Path) -> None:
        # _call_name() returns None when func is neither Name nor Attribute.
        src = tmp_path / "sub.py"
        src.write_text("funcs = [print]\nfuncs[0]()\n")
        assert len(builder.build(src).edges) == 0

    def test_recursive_call_excluded(self, builder: GraphBuilder, tmp_path: Path) -> None:
        # callee == scope branch — self-calls must not produce edges.
        src = tmp_path / "rec.py"
        src.write_text("def fib(n: int) -> int:\n    return fib(n - 1) if n > 0 else 0\n")
        g = builder.build(src)
        assert not any(e.source == "fib" and e.target == "fib" for e in g.edges)

    def test_syntax_error_creates_fallback_node(self, builder: GraphBuilder, tmp_path: Path) -> None:
        # Python 2 syntax → SyntaxError → single __main__ MODULE node, no edges.
        src = tmp_path / "py2.py"
        src.write_text('print "hello"\n')
        g = builder.build(src)
        assert len(g.nodes) == 1 and g.nodes[0].id == "__main__"
        assert g.nodes[0].node_type.value == "module" and len(g.edges) == 0


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


class TestGraphMerge:
    def test_dedupes_identical_edges_across_files(self) -> None:
        nodes = [_mnode("__main__"), _mnode("welcome")]
        g1 = Graph(file_path="a.py", nodes=nodes, edges=[_medge("__main__", "welcome")])
        g2 = Graph(file_path="b.py", nodes=nodes, edges=[_medge("__main__", "welcome")])
        assert len(Graph.merge([g1, g2], "workspace/target").edges) == 1

    def test_dedupes_nodes_by_id(self) -> None:
        g1 = Graph(file_path="a.py", nodes=[_mnode("__main__")])
        g2 = Graph(file_path="b.py", nodes=[_mnode("__main__")])
        assert len(Graph.merge([g1, g2], "t").nodes) == 1

    def test_keeps_distinct_edges(self) -> None:
        g = Graph(file_path="a.py", nodes=[_mnode("__main__"), _mnode("a"), _mnode("b")],
                  edges=[_medge("__main__", "a"), _medge("__main__", "b")])
        assert len(Graph.merge([g], "t").edges) == 2

    def test_first_occurrence_wins(self) -> None:
        first = Edge(source="x", target="y", edge_type=EdgeType.CALLS, weight=0.9)
        second = Edge(source="x", target="y", edge_type=EdgeType.INSTANTIATES, weight=0.1)
        g1 = Graph(file_path="a.py", nodes=[_mnode("x"), _mnode("y")], edges=[first])
        g2 = Graph(file_path="b.py", nodes=[_mnode("x"), _mnode("y")], edges=[second])
        assert Graph.merge([g1, g2], "t").edges[0].edge_type == EdgeType.CALLS

    def test_empty_input_yields_empty_graph(self) -> None:
        merged = Graph.merge([], "t")
        assert merged.nodes == [] and merged.edges == [] and merged.file_path == "t"

    def test_merged_file_path_is_set(self) -> None:
        g = Graph(file_path="a.py", nodes=[_mnode("__main__")])
        assert Graph.merge([g], "workspace/target").file_path == "workspace/target"

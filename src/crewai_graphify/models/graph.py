"""Pydantic data models for the code-structure graph.

``Node`` represents a code entity (module, class, method, or function).
``Edge`` represents a directed relationship (call, instantiation, etc.).
``Graph`` is the immutable container holding both collections plus helpers.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

__all__ = ["Edge", "EdgeType", "Graph", "Node", "NodeType"]


class NodeType(StrEnum):
    """Classifies what kind of code entity a Node represents."""

    MODULE = "module"
    CLASS = "class"
    METHOD = "method"
    FUNCTION = "function"


class EdgeType(StrEnum):
    """Classifies the structural relationship between two nodes."""

    CALLS = "calls"
    INSTANTIATES = "instantiates"
    INHERITS = "inherits"
    IMPORTS = "imports"


class Node(BaseModel, frozen=True):
    """A single code entity extracted from a source file.

    ``id`` is the unique key used in edge references
    (e.g. ``"Polygon.__init__"`` for a class method).
    """

    id: str = Field(description="Unique identifier, e.g. 'Polygon.__init__'.")
    name: str = Field(description="Short entity name, e.g. '__init__'.")
    node_type: NodeType
    file_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    docstring: str | None = None


class Edge(BaseModel, frozen=True):
    """A directed structural relationship from *source* node to *target* node.

    ``weight`` is a relevance score in [0, 1] used by the Navigator Agent to
    prioritise traversal order.  Higher weight = more likely to be on the
    bug call chain.
    """

    source: str = Field(description="ID of the source (caller/parent) node.")
    target: str = Field(description="ID of the target (callee/child) node.")
    edge_type: EdgeType
    weight: float = Field(default=0.8, ge=0.0, le=1.0)


class Graph(BaseModel, frozen=True):
    """Immutable graph of all nodes and edges for a single source file."""

    file_path: str
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)

    # -- Convenience accessors (pure, no mutation) -------------------------

    def node_by_id(self, node_id: str) -> Node | None:
        """Return the node with *node_id*, or ``None`` if not found."""
        return next((n for n in self.nodes if n.id == node_id), None)

    def edges_from(self, node_id: str) -> list[Edge]:
        """Return all edges whose source is *node_id*."""
        return [e for e in self.edges if e.source == node_id]

    def edges_to(self, node_id: str) -> list[Edge]:
        """Return all edges whose target is *node_id*."""
        return [e for e in self.edges if e.target == node_id]

    @classmethod
    def merge(cls, graphs: list[Graph], file_path: str) -> Graph:
        """Merge per-file graphs into one deduplicated graph.

        Nodes are deduped by ``id`` (every module's ``__main__`` collapses into a
        single node) and edges are deduped on the ``(source, target)`` key — the
        same key the UI ForceGraph uses — so the persisted edge count matches the
        rendered link count exactly.  First occurrence wins, making the result
        deterministic for a sorted input list.
        """
        nodes: dict[str, Node] = {}
        edges: dict[tuple[str, str], Edge] = {}
        for g in graphs:
            for n in g.nodes:
                nodes[n.id] = n
            for e in g.edges:
                edges.setdefault((e.source, e.target), e)
        return cls(file_path=file_path, nodes=list(nodes.values()), edges=list(edges.values()))

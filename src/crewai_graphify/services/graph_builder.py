"""Graph Builder — AST analyser that extracts code structure and writes vault artefacts.

Pre-processes source to strip invalid keywords (e.g. ``new``) before ast.parse().
"""

from __future__ import annotations

import ast
from pathlib import Path

from crewai_graphify.models.graph import Edge, EdgeType, Graph, Node, NodeType

__all__ = ["GraphBuilder"]

# Syntax patches applied before ast.parse() — strips invalid keywords
_SANITIZE: list[tuple[str, str]] = [("new ", "")]



def _call_name(func: ast.expr) -> str | None:
    """Return the bare callee name from a Call's func node, or None."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _edges_from(
    scope: str,
    stmts: list[ast.stmt],
    id_types: dict[str, NodeType],
    weight: float = 0.8,
) -> list[Edge]:
    """Collect unique edges for every known callee found in *stmts*."""
    seen: set[str] = set()
    edges: list[Edge] = []
    for stmt in stmts:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                callee = _call_name(node.func)
                if callee and callee in id_types and callee != scope and callee not in seen:
                    seen.add(callee)
                    etype = (
                        EdgeType.INSTANTIATES
                        if id_types[callee] == NodeType.CLASS
                        else EdgeType.CALLS
                    )
                    edges.append(Edge(source=scope, target=callee, edge_type=etype, weight=weight))
    return edges



class GraphBuilder:
    """Parses a Python source file's AST into a ``Graph`` and persists vault artefacts."""

    def __init__(self, vault_dir: Path | None = None) -> None:
        self.vault_dir = vault_dir or Path("workspace/vault")
        self.vault_dir.mkdir(parents=True, exist_ok=True)

    def build(self, target_file: Path) -> Graph:
        """Parse *target_file* and return an in-memory ``Graph``.  No disk I/O."""
        source = target_file.read_text(encoding="utf-8")
        for old, replacement in _SANITIZE:
            source = source.replace(old, replacement)
        tree = ast.parse(source, filename=str(target_file))
        nodes = self._collect_nodes(tree, target_file)
        return Graph(
            file_path=str(target_file),
            nodes=nodes,
            edges=self._collect_edges(tree, nodes),
        )

    def save_graph(self, graph: Graph) -> Path:
        """Serialise *graph* as ``{vault_dir}/graph.json``."""
        out = self.vault_dir / "graph.json"
        out.write_text(graph.model_dump_json(indent=2), encoding="utf-8")
        return out

    def save_index_md(self, graph: Graph) -> Path:
        """Write a Markdown node index to ``{vault_dir}/index.md``."""
        lines: list[str] = [
            "# Obsidian Vault — Node Index",
            "",
            f"**Source:** `{graph.file_path}`  ",
            f"**Nodes:** {len(graph.nodes)} | **Edges:** {len(graph.edges)}",
            "",
            "## Nodes",
            "",
        ]
        for n in graph.nodes:
            doc = f" — _{n.docstring[:60]}_" if n.docstring else ""
            lines.append(f"- [[{n.id}]] `{n.node_type.value}` L{n.start_line}–{n.end_line}{doc}")
        lines += ["", "## Edges", ""]
        for e in graph.edges:
            lines.append(f"- `{e.source}` →[{e.edge_type.value} w={e.weight}]→ `{e.target}`")
        out = self.vault_dir / "index.md"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

    def _collect_nodes(self, tree: ast.Module, target_file: Path) -> list[Node]:
        fp = str(target_file)
        max_line = max((n.lineno for n in ast.walk(tree) if hasattr(n, "lineno")), default=1)
        nodes: list[Node] = [
            Node(id="__main__", name="__main__", node_type=NodeType.MODULE,
                 file_path=fp, start_line=1, end_line=max_line)
        ]
        method_names: set[str] = set()
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            nodes.append(Node(id=cls.name, name=cls.name, node_type=NodeType.CLASS,
                              file_path=fp, start_line=cls.lineno,
                              end_line=cls.end_lineno or cls.lineno,
                              docstring=ast.get_docstring(cls)))
            for item in cls.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_names.add(item.name)
                    nodes.append(Node(id=f"{cls.name}.{item.name}", name=item.name,
                                      node_type=NodeType.METHOD, file_path=fp,
                                      start_line=item.lineno,
                                      end_line=item.end_lineno or item.lineno,
                                      docstring=ast.get_docstring(item)))
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name not in method_names:
                nodes.append(Node(id=stmt.name, name=stmt.name,
                                  node_type=NodeType.FUNCTION, file_path=fp,
                                  start_line=stmt.lineno,
                                  end_line=stmt.end_lineno or stmt.lineno,
                                  docstring=ast.get_docstring(stmt)))
        return nodes

    def _collect_edges(self, tree: ast.Module, nodes: list[Node]) -> list[Edge]:
        id_types = {n.id: n.node_type for n in nodes}
        edges: list[Edge] = []
        script = [s for s in tree.body
                  if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        edges += _edges_from("__main__", script, id_types, weight=0.9)
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                edges += _edges_from(stmt.name, [stmt], id_types)
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            for method in cls.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    edges += _edges_from(f"{cls.name}.{method.name}", [method], id_types)
        return edges

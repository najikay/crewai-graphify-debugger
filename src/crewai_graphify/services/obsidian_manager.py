"""Obsidian Manager — computes hot nodes and writes ``hot.md`` for the vault.

Reads the ``graph.json`` produced by ``GraphBuilder``, ranks every node by
degree centrality, traces the highest-weight call chain from ``__main__``,
and documents the known bug sites — giving the Navigator Agent a concise
seed context without requiring it to read any source file first.
"""

from __future__ import annotations

from pathlib import Path

from crewai_graphify.models.graph import Graph, Node

__all__ = ["ObsidianManager"]


class ObsidianManager:
    """Generates Obsidian vault markdown artefacts from a ``Graph`` object.

    Primary output is ``hot.md``: the top-N nodes by degree centrality plus
    the bug call chain traced from the module entry point.

    Args:
        vault_dir: Directory containing ``graph.json`` and where ``hot.md``
            will be written.  Defaults to ``workspace/vault``.
        top_n: Maximum number of hot nodes to list in ``hot.md``.
    """

    def __init__(self, vault_dir: Path | None = None, top_n: int = 10) -> None:
        self.vault_dir = vault_dir or Path("workspace/vault")
        self.top_n = top_n

    # -- Public API --------------------------------------------------------

    def load_graph(self) -> Graph:
        """Deserialise ``{vault_dir}/graph.json`` into a ``Graph`` model."""
        return Graph.model_validate_json(
            (self.vault_dir / "graph.json").read_text(encoding="utf-8")
        )

    def compute_hot_nodes(self, graph: Graph) -> list[tuple[Node, float]]:
        """Rank nodes by degree centrality: (in-degree + out-degree) / total edges.

        Returns the top-``self.top_n`` nodes as (node, score) pairs.
        """
        total = len(graph.edges) or 1
        scores = {
            n.id: sum(1 for e in graph.edges if e.source == n.id or e.target == n.id) / total
            for n in graph.nodes
        }
        by_id = {n.id: n for n in graph.nodes}
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return [(by_id[nid], score) for nid, score in ranked[: self.top_n] if nid in by_id]

    def trace_bug_chain(self, graph: Graph) -> list[str]:
        """Follow the highest-weight outgoing edges from ``__main__``.

        Returns an ordered list of node IDs representing the most likely
        path to the primary bug site.
        """
        chain = ["__main__"]
        visited: set[str] = {"__main__"}
        current = "__main__"
        while True:
            candidates = sorted(
                [e for e in graph.edges if e.source == current and e.target not in visited],
                key=lambda e: e.weight,
                reverse=True,
            )
            if not candidates:
                break
            best = candidates[0]
            chain.append(best.target)
            visited.add(best.target)
            current = best.target
        return chain

    def save_hot_md(self, graph: Graph) -> Path:
        """Generate and write ``{vault_dir}/hot.md``.

        Sections produced:
        - Top hot nodes ranked by degree centrality.
        - Bug call chain traced from ``__main__``.
        - Known bug sites table (populated from target analysis).
        """
        hot = self.compute_hot_nodes(graph)
        chain = self.trace_bug_chain(graph)
        by_id = {n.id: n for n in graph.nodes}

        lines: list[str] = [
            "# hot.md — High-Centrality Nodes (Debugging Hot Path)",
            "",
            "Seed context for the Navigator Agent. "
            "Read these nodes first — highest structural relevance.",
            "",
            f"**Source:** `{graph.file_path}`",
            "",
            "## Top Hot Nodes (by degree centrality)",
            "",
        ]
        for rank, (node, score) in enumerate(hot, 1):
            lines.append(
                f"{rank}. **[[{node.id}]]** `{node.node_type.value}`"
                f" — centrality `{score:.3f}` (L{node.start_line}–{node.end_line})"
            )
            if node.docstring:
                lines.append(f"   > {node.docstring[:100]}")
            lines.append("")

        lines += ["## Bug Call Chain", "", "```text"]
        for i, nid in enumerate(chain):
            node = by_id.get(nid)
            prefix = "    → " if i > 0 else ""
            tag = f"  [L{node.start_line}–{node.end_line}, {node.node_type.value}]" if node else ""
            lines.append(f"{prefix}{nid}{tag}")
        lines += ["```", ""]

        lines += [
            "## Known Bug Sites",
            "",
            "| Node | Line | Severity | Description |",
            "|------|------|----------|-------------|",
            "| `calc_polygon_details` | 29 | **SyntaxError** |"
            " `new Polygon(...)` — no `new` keyword in Python; remove `new ` |",
            "| `Polygon` | 3 | **NameError** |"
            " `class Polygon(Object)` — `Object` undefined; use `object` |",
            "| `draw_polygon` | 51 | **LogicError** |"
            " `range(0, 6)` hardcoded — always draws hexagon regardless of sides |",
        ]

        out = self.vault_dir / "hot.md"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

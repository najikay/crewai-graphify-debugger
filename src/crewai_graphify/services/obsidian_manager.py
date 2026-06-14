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

        Sections: primary target file (highest in-degree node), top hot nodes,
        bug call chain, and all non-module nodes inside the primary file.
        No hardcoded names — everything is derived from the live graph.
        """
        hot = self.compute_hot_nodes(graph)
        chain = self.trace_bug_chain(graph)
        by_id = {n.id: n for n in graph.nodes}

        # Identify primary bug target: node with most incoming edges
        in_deg: dict[str, int] = {}
        for e in graph.edges:
            in_deg[e.target] = in_deg.get(e.target, 0) + 1
        root_id = max(in_deg, key=lambda k: in_deg[k]) if in_deg else "__main__"
        root_node = by_id.get(root_id)
        primary_file = root_node.file_path if root_node else graph.file_path

        lines: list[str] = [
            "# hot.md — High-Centrality Nodes (Debugging Hot Path)",
            "",
            "Seed context for the Navigator Agent. Read these nodes first.",
            "",
            f"**Primary Target File:** `{primary_file}`",
            f"**Root-Cause Node:** `{root_id}`"
            f" ({in_deg.get(root_id, 0)} incoming edges)",
            "",
            "## Top Hot Nodes (by degree centrality)",
            "",
        ]
        for rank, (node, score) in enumerate(hot, 1):
            lines.append(
                f"{rank}. **[[{node.id}]]** `{node.node_type.value}`"
                f" — centrality `{score:.3f}`"
                f" (L{node.start_line}–{node.end_line}) `{node.file_path}`"
            )
            if node.docstring:
                lines.append(f"   > {node.docstring[:80]}")
            lines.append("")

        lines += ["## Bug Call Chain", "", "```text"]
        for i, nid in enumerate(chain):
            cn: Node | None = by_id.get(nid)
            prefix = "    → " if i > 0 else ""
            tag = f"  [L{cn.start_line}–{cn.end_line}, {cn.node_type.value}]" if cn else ""
            lines.append(f"{prefix}{nid}{tag}")
        lines += ["```", ""]

        # Dynamic candidate nodes from the primary file (sorted by line number)
        file_nodes = sorted(
            [n for n in graph.nodes
             if n.file_path == primary_file and n.id != "__main__"],
            key=lambda n: n.start_line,
        )
        if file_nodes:
            lines += ["## Nodes in Primary Target File", ""]
            for n in file_nodes:
                lines.append(f"- `{n.id}` ({n.node_type.value}) L{n.start_line}–{n.end_line}")
            lines.append("")

        out = self.vault_dir / "hot.md"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

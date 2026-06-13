#!/usr/bin/env python3
"""Phase 2 verification — asserts vault artefacts are correctly generated.

Exit 0 = all checks passed. Exit 1 = failures (details on stderr).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

VAULT = Path("workspace/vault")
GRAPH_JSON = VAULT / "graph.json"
INDEX_MD = VAULT / "index.md"
HOT_MD = VAULT / "hot.md"

REQUIRED_NODE_IDS = {"Polygon", "calc_polygon_details", "__main__", "draw_polygon"}
EXPECTED_BUG_CHAIN = ["__main__", "calc_polygon_details", "Polygon"]
EXPECTED_EDGE = ("calc_polygon_details", "Polygon", "instantiates")


def check_files_exist() -> list[str]:
    errors: list[str] = []
    for path in (GRAPH_JSON, INDEX_MD, HOT_MD):
        if not path.exists():
            errors.append(f"MISSING: {path}")
        elif path.stat().st_size == 0:
            errors.append(f"EMPTY:   {path}")
    return errors


def check_graph_nodes(data: dict) -> list[str]:  # type: ignore[type-arg]
    found = {n["id"] for n in data.get("nodes", [])}
    return [f"MISSING NODE: '{r}'" for r in REQUIRED_NODE_IDS if r not in found]


def check_graph_edges(data: dict) -> list[str]:  # type: ignore[type-arg]
    errors: list[str] = []
    src, tgt, etype = EXPECTED_EDGE
    match = next(
        (e for e in data.get("edges", [])
         if e["source"] == src and e["target"] == tgt and e["edge_type"] == etype),
        None,
    )
    if match is None:
        errors.append(f"MISSING EDGE: '{src}' --[{etype}]--> '{tgt}'")
    elif match.get("weight", 0) < 0.6:
        errors.append(f"LOW WEIGHT: {src}→{tgt} weight={match['weight']} (expected ≥ 0.6)")
    return errors


def check_hot_md_chain() -> list[str]:
    errors: list[str] = []
    content = HOT_MD.read_text(encoding="utf-8")
    for nid in EXPECTED_BUG_CHAIN:
        if nid not in content:
            errors.append(f"MISSING IN hot.md: '{nid}'")
    if "Bug Call Chain" not in content:
        errors.append("MISSING IN hot.md: '## Bug Call Chain' section")
    if "SyntaxError" not in content:
        errors.append("MISSING IN hot.md: 'SyntaxError' bug entry")
    try:
        start = content.index("Bug Call Chain")
        section = content[start:]
        if section.index("calc_polygon_details") >= section.index("Polygon"):
            errors.append("ORDERING ERROR in hot.md: Polygon before calc_polygon_details")
    except ValueError as exc:
        errors.append(f"PARSE ERROR in hot.md: {exc}")
    return errors


def main() -> int:
    all_errors: list[str] = []
    steps: list[tuple[str, list[str]]] = []

    steps.append(("Vault artefact existence", check_files_exist()))

    graph_errors: list[str] = []
    graph_data: dict = {}  # type: ignore[type-arg]
    if GRAPH_JSON.exists():
        try:
            graph_data = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            graph_errors.append(f"INVALID JSON: {exc}")
    steps.append(("graph.json — JSON validity", graph_errors))

    if not graph_errors:
        steps.append(("graph.json — required nodes", check_graph_nodes(graph_data)))
        steps.append(("graph.json — critical edge",  check_graph_edges(graph_data)))

    if HOT_MD.exists():
        steps.append(("hot.md — bug call chain", check_hot_md_chain()))

    print()
    for label, errors in steps:
        status = "PASS" if not errors else "FAIL"
        print(f"  [{status}] {label}")
        for err in errors:
            print(f"         ✗ {err}", file=sys.stderr)
        all_errors.extend(errors)

    print()
    if not all_errors:
        node_count = len(graph_data.get("nodes", []))
        edge_count = len(graph_data.get("edges", []))
        print("  ✓ Phase 2 verification PASSED.")
        print(f"  ✓ Vault is ready for agents: {node_count} nodes, {edge_count} edges.")
        print(f"  ✓ Bug chain confirmed: {' → '.join(EXPECTED_BUG_CHAIN)}")
        print()
        return 0

    print(f"  ✗ {len(all_errors)} check(s) failed.", file=sys.stderr)
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())

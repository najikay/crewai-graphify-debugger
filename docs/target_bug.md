# Target Bug Documentation

**Version:** 1.0.0  
**Phase:** 2 — Graph Builder & Obsidian Vault Initialization  
**Last Updated:** 2026-06-13

---

## Environment Pivot Notice

**Original target:** `soarsmu/BugsInPy` (httpie, Bug ID 1)  
**Pivot reason:** The BugsInPy bash framework (`bugsinpy-checkout`, `bugsinpy-compile`)
uses hardcoded POSIX paths and shell shebang lines (`#!/bin/bash`) that are incompatible
with the Windows/Git Bash environment. The scripts fail silently or error on path resolution
under WSL and native Windows Git Bash.  
**Decision:** In strict accordance with the assignment guideline to avoid spending excessive
time fighting the environment, we pivoted to a self-contained local target that requires
zero external tooling.

---

## New Target: `martinpeck/broken-python`

**Repository:** `workspace/target/broken-python`  
**Selected script:** `polygons/polygons.py`  
**Why this script was chosen over `mathsquiz/mathsquiz.py`:**

| Criterion | `polygons.py` | `mathsquiz.py` |
|---|---|---|
| Has classes | ✓ `Polygon` | ✗ flat script |
| Has named functions | ✓ `calc_polygon_details`, `draw_polygon` | ✗ flat script |
| Multi-hop call chain | ✓ 3 hops | ✗ none |
| Graph navigation advantage | **High** | None |
| Bugs span multiple nodes | ✓ 3 distinct nodes | ✗ all in one scope |

`mathsquiz.py` contains only Python 2 `print` statements and `=` vs `==` typos at the
module level — no structural graph can be drawn. `polygons.py` is the only file with
enough OOP structure to demonstrate the graph-guided workflow.

---

## Bug Analysis — `polygons/polygons.py`

### Structural Graph (5 nodes, 3 edges)

```
__main__ (MODULE, L1–75)
    │─[calls, w=0.9]──▶  calc_polygon_details (FUNCTION, L13–36)
    │                           │─[instantiates, w=0.8]──▶  Polygon (CLASS, L3–8)
    │                                                              └── Polygon.__init__ (METHOD, L5–8)
    └─[calls, w=0.9]──▶  draw_polygon (FUNCTION, L41–53)
```

### Bug Inventory

| # | Node | Line | Type | Description |
|---|------|------|------|-------------|
| 1 | `calc_polygon_details` | 29 | **SyntaxError** | `poly = new Polygon(...)` — Python has no `new` keyword. Fix: remove `new `. This is the **primary bug** and the hot node on the call chain. |
| 2 | `Polygon` | 3 | **NameError** | `class Polygon(Object)` — `Object` (capitalised) is not a built-in. Fix: `class Polygon(object)` or `class Polygon:`. |
| 3 | `draw_polygon` | 51 | **LogicError** | `for i in range(0, 6): t.right(60)` — hardcoded hexagon drawing regardless of `polygon_details["sides"]`. |
| 4 | `calc_polygon_details` | 26–27 | **LogicError** | `else:` branch returns `internal_angles_sum=1000, internal_angles=200` — mathematically incorrect for any polygon. |

### Why Graph Navigation Demonstrates Advantage Here

A naive agent receiving `polygons.py` as raw context sees a 75-line file and must
determine which of the 4 bugs is the **root cause** that prevents the script from
running at all. It has no structural signal to guide it.

The graph-guided agent:
1. Opens `hot.md` — immediately sees `calc_polygon_details` and `__main__` as the top
   hot nodes (centrality 0.667).
2. Follows the edge `calc_polygon_details → Polygon` (weight 0.8, type `instantiates`).
3. Reads **only lines 13–36** of `calc_polygon_details` (the targeted slice).
4. Finds `new Polygon(...)` on line 29 in 1 file read rather than scanning the full file.

**File reads to root cause:** graph-guided = 1 slice read vs naive = 1 full file read.  
**Token reduction:** slice (lines 13–36) = 24 lines vs full file = 75 lines → **68% fewer tokens**.

---

## Graph Stats

| Metric | Value |
|---|---|
| Total nodes | 5 |
| Total edges | 3 |
| Hot nodes (centrality > 0.3) | 4 |
| Bug-bearing nodes | 3 |
| Primary bug node | `calc_polygon_details` |
| Bug call chain | `__main__` → `calc_polygon_details` → `Polygon` |

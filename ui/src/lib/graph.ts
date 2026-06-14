// Pure graph helpers — mapping, node colouring, and path normalisation.
// Kept free of React so they can be unit-tested (see lib/__tests__/graph.test.ts).

import type { ApiGraph, FgData, FgLink } from "./types";

export const NODE_PATCHED = "#22c55e"; // green — file received a patch this run
export const NODE_DEFAULT = "#3b82f6"; // blue — unpatched

// Node file_path values are stored relative to the repo root, e.g.
// "workspace/target/broken-python/polygons/polygons.py". The /api/file endpoint
// resolves relative to workspace/target/, so strip that prefix for node clicks.
const TARGET_PREFIX = "workspace/target/";

/** Convert an ApiGraph into the {nodes, links} shape react-force-graph expects. */
export function mapApiGraph(data: ApiGraph): FgData {
  return {
    nodes: data.nodes.map((n) => ({ ...n, val: 4 })),
    links: data.edges.map((e): FgLink => ({ source: e.source, target: e.target })),
  };
}

/** Green when the node's file matches any patched file, blue otherwise.
 *
 * Both sides are normalised via toApiPath so a node stored as
 * "workspace/target/broken-python/x.py" matches a patched entry "broken-python/x.py".
 */
export function nodeColor(filePath: string, patched: Iterable<string>): string {
  const target = toApiPath(filePath);
  const hit = [...patched].some((f) => f.length > 0 && target.includes(toApiPath(f)));
  return hit ? NODE_PATCHED : NODE_DEFAULT;
}

/** Strip the workspace/target/ prefix so a node path maps to an /api/file path. */
export function toApiPath(filePath: string): string {
  return filePath.startsWith(TARGET_PREFIX)
    ? filePath.slice(TARGET_PREFIX.length)
    : filePath;
}

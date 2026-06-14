// Shared types for the Command Center UI — mirror the backend graph.json schema.

export interface GNode {
  id: string;
  name: string;
  node_type: string;
  file_path: string;
  start_line: number;
  end_line: number;
  val?: number;
}

export interface GEdge {
  source: string;
  target: string;
  edge_type: string;
  weight: number;
}

export interface ApiGraph {
  file_path: string;
  nodes: GNode[];
  edges: GEdge[];
}

// react-force-graph mutates link objects — keep source/target as plain strings.
export interface FgLink {
  source: string;
  target: string;
}

export interface FgData {
  nodes: GNode[];
  links: FgLink[];
}

export const EMPTY_GRAPH: FgData = { nodes: [], links: [] };

export type GraphStatus = "idle" | "loading" | "ok" | "error";

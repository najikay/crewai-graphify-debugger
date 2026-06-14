import { describe, expect, it } from "vitest";
import { mapApiGraph, NODE_DEFAULT, NODE_PATCHED, nodeColor, toApiPath } from "../graph";
import type { ApiGraph } from "../types";

const SAMPLE: ApiGraph = {
  file_path: "workspace/target",
  nodes: [
    {
      id: "Polygon",
      name: "Polygon",
      node_type: "CLASS",
      file_path: "workspace/target/broken-python/polygons/polygons.py",
      start_line: 3,
      end_line: 8,
    },
  ],
  edges: [{ source: "__main__", target: "Polygon", edge_type: "CALLS", weight: 0.9 }],
};

describe("mapApiGraph", () => {
  it("maps nodes and assigns a render val", () => {
    const fg = mapApiGraph(SAMPLE);
    expect(fg.nodes).toHaveLength(1);
    expect(fg.nodes[0].val).toBe(4);
  });

  it("maps edges to {source,target} links only", () => {
    const fg = mapApiGraph(SAMPLE);
    expect(fg.links[0]).toEqual({ source: "__main__", target: "Polygon" });
  });
});

describe("nodeColor", () => {
  it("uses the project's green/blue hex values", () => {
    expect(NODE_PATCHED).toBe("#22c55e");
    expect(NODE_DEFAULT).toBe("#3b82f6");
  });

  it("returns green when the file matches a patched entry", () => {
    expect(nodeColor("a/polygons.py", ["polygons.py"])).toBe(NODE_PATCHED);
  });

  it("matches a full node path against a target-relative patched entry", () => {
    // node file_path keeps the workspace/target/ prefix; patched entry does not
    expect(
      nodeColor(
        "workspace/target/broken-python/polygons/polygons.py",
        ["broken-python/polygons/polygons.py"],
      ),
    ).toBe(NODE_PATCHED);
  });

  it("returns blue when nothing matches", () => {
    expect(nodeColor("a/polygons.py", new Set(["other.py"]))).toBe(NODE_DEFAULT);
  });

  it("ignores empty patched entries (no false positive)", () => {
    expect(nodeColor("a/polygons.py", [""])).toBe(NODE_DEFAULT);
  });
});

describe("toApiPath", () => {
  it("strips the workspace/target/ prefix", () => {
    expect(toApiPath("workspace/target/broken-python/polygons/polygons.py")).toBe(
      "broken-python/polygons/polygons.py",
    );
  });

  it("leaves an already-relative path unchanged", () => {
    expect(toApiPath("broken-python/x.py")).toBe("broken-python/x.py");
  });
});

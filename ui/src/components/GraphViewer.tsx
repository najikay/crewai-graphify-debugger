// GraphViewer — renders the dependency graph from /api/graph via react-force-graph.
// Clicking a node opens that file in the Code Inspector; patched files turn green.

import { useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { FgData, GNode } from "../lib/types";
import { nodeColor, toApiPath } from "../lib/graph";

interface Props {
  data: FgData;
  patchedFiles: Set<string>;
  onNodeClick: (apiPath: string) => void;
}

export default function GraphViewer({ data, patchedFiles, onNodeClick }: Props) {
  const pane = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 600, h: 500 });

  useEffect(() => {
    const update = () => {
      if (pane.current)
        setDims({ w: pane.current.clientWidth, h: pane.current.clientHeight });
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  return (
    <>
      <div className="graph-legend">
        <span>🟢 Patched</span>
        <span className="legend-sep">|</span>
        <span>🔵 Unpatched</span>
        <span className="legend-hint">— Click a node (or sidebar file) to view code</span>
      </div>
      <div className="graph-canvas" ref={pane}>
        <ForceGraph2D
          graphData={data}
          width={dims.w}
          height={dims.h}
          nodeLabel="id"
          nodeColor={(n) => nodeColor((n as unknown as GNode).file_path ?? "", patchedFiles)}
          onNodeClick={(n) => {
            const fp = (n as unknown as GNode).file_path;
            if (fp) onNodeClick(toApiPath(fp));
          }}
          linkColor={() => "#30363d"}
          backgroundColor="#0d1117"
          nodeRelSize={6}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
        />
      </div>
    </>
  );
}

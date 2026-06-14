import { useCallback, useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import axios from "axios";
import { Loader, Play } from "lucide-react";
import "./index.css";

// ── Types matching graph.json schema ─────────────────────────────────────────

interface GNode {
  id: string;
  name: string;
  node_type: string;
  file_path: string;
  start_line: number;
  end_line: number;
  val?: number;
}

interface GEdge {
  source: string;
  target: string;
  edge_type: string;
  weight: number;
}

interface ApiGraph {
  file_path: string;
  nodes: GNode[];
  edges: GEdge[];          // backend uses "edges"; ForceGraph2D needs "links"
}

interface FgData {
  nodes: GNode[];
  links: GEdge[];
}

const EMPTY: FgData = { nodes: [], links: [] };

// ── Component ─────────────────────────────────────────────────────────────────

export default function App() {
  const [fg, setFg] = useState<FgData>(EMPTY);
  const [logs, setLogs] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [dims, setDims] = useState({ w: 600, h: 500 });

  const graphPane = useRef<HTMLDivElement>(null);
  const termRef = useRef<HTMLDivElement>(null);

  // ── Load graph from FastAPI on mount ───────────────────────────────────────
  useEffect(() => {
    axios
      .get<ApiGraph>("/api/graph")
      .then(({ data }) =>
        setFg({
          nodes: data.nodes.map((n) => ({ ...n, val: 4 })),
          links: data.edges,   // map edges → links
        })
      )
      .catch(() => {
        /* graph.json not yet generated — UI stays empty */
      });
  }, []);

  // ── Keep graph canvas sized to its DOM container ───────────────────────────
  const updateDims = useCallback(() => {
    if (graphPane.current) {
      setDims({
        w: graphPane.current.clientWidth,
        h: graphPane.current.clientHeight,
      });
    }
  }, []);

  useEffect(() => {
    updateDims();
    window.addEventListener("resize", updateDims);
    return () => window.removeEventListener("resize", updateDims);
  }, [updateDims]);

  // ── Auto-scroll terminal to newest line ────────────────────────────────────
  useEffect(() => {
    if (termRef.current) {
      termRef.current.scrollTop = termRef.current.scrollHeight;
    }
  }, [logs]);

  // ── Trigger run + open SSE stream ──────────────────────────────────────────
  const handleRun = async () => {
    setRunning(true);
    setLogs([]);
    try {
      await axios.post("/api/execute");
    } catch {
      setRunning(false);
      return;
    }
    const es = new EventSource("/api/stream");
    es.onmessage = (e: MessageEvent<string>) => {
      const { log } = JSON.parse(e.data) as { log: string };
      setLogs((prev) => [...prev, log]);
    };
    es.addEventListener("done", () => {
      setRunning(false);
      es.close();
    });
    es.onerror = () => {
      setRunning(false);
      es.close();
    };
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="os-shell">
      {/* ── Left sidebar: File Explorer ──────────────────────────── */}
      <aside className="sidebar-left">
        <p className="panel-title">Workspace</p>
        <ul className="file-tree">
          <li>workspace/</li>
          <li className="i1">vault/</li>
          <li className="i2">graph.json</li>
          <li className="i2">hot.md</li>
          <li className="i1">target/</li>
          <li className="i1">root_cause_report.json</li>
          <li className="i1">token_efficiency_report.md</li>
        </ul>
      </aside>

      {/* ── Center pane: Force-directed dependency graph ─────────── */}
      <main className="center-pane">
        <div className="topbar">
          <span className="panel-title" style={{ marginBottom: 0 }}>
            Dependency Graph — {fg.nodes.length} node
            {fg.nodes.length !== 1 ? "s" : ""}
          </span>
          <button
            className={`run-btn${running ? " busy" : ""}`}
            onClick={handleRun}
            disabled={running}
          >
            {running ? (
              <Loader size={13} className="spin" />
            ) : (
              <Play size={13} />
            )}
            {running ? "Running..." : "Run Debugger"}
          </button>
        </div>
        <div className="graph-canvas" ref={graphPane}>
          <ForceGraph2D
            graphData={fg}
            width={dims.w}
            height={dims.h}
            nodeLabel="id"
            nodeColor={() => "#58a6ff"}
            linkColor={() => "#30363d"}
            backgroundColor="#0d1117"
            nodeRelSize={6}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
          />
        </div>
      </main>

      {/* ── Right sidebar: Live SSE Agent Terminal ───────────────── */}
      <aside className="sidebar-right">
        <div className="topbar">
          <p className="panel-title" style={{ marginBottom: 0, color: "#3fb950" }}>
            Agent Terminal
          </p>
        </div>
        <div className="terminal" ref={termRef}>
          {logs.length === 0 ? (
            <span className="ph">Click "Run Debugger" to start...</span>
          ) : (
            logs.map((line, i) => (
              <div key={i} className={line.startsWith("ERROR") ? "err" : ""}>
                {line}
              </div>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}

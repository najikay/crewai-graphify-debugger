import { useCallback, useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import axios from "axios";
import { Loader, Play, RefreshCw } from "lucide-react";
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
  edges: GEdge[];
}

// react-force-graph mutates link objects — keep source/target strings only
interface FgLink { source: string; target: string }
interface FgData { nodes: GNode[]; links: FgLink[] }

const EMPTY: FgData = { nodes: [], links: [] };
type GraphStatus = "idle" | "loading" | "ok" | "error";

// ── Component ─────────────────────────────────────────────────────────────────

export default function App() {
  const [fg, setFg] = useState<FgData>(EMPTY);
  const [graphStatus, setGraphStatus] = useState<GraphStatus>("idle");
  const [logs, setLogs] = useState<string[]>([]);
  const [patchedFiles, setPatchedFiles] = useState<Set<string>>(new Set());
  const [running, setRunning] = useState(false);
  const [dims, setDims] = useState({ w: 600, h: 500 });

  const graphPane = useRef<HTMLDivElement>(null);
  const termRef = useRef<HTMLDivElement>(null);

  // ── Fix 1 + 2: Graph fetch with correct edge→link mapping and retry ────────
  const loadGraph = useCallback(async (retries = 4) => {
    setGraphStatus("loading");
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        const { data } = await axios.get<ApiGraph>("/api/graph");
        setFg({
          nodes: data.nodes.map((n) => ({ ...n, val: 4 })),
          // Fix 1: explicitly map edges → links, stripping extra fields
          // react-force-graph mutates these objects; extra keys cause confusion
          links: data.edges.map((e): FgLink => ({ source: e.source, target: e.target })),
        });
        setGraphStatus("ok");
        return; // success — stop retrying
      } catch {
        if (attempt < retries - 1) {
          // Fix 2: exponential back-off — 1.5s, 3s, 4.5s between attempts
          await new Promise<void>((r) => setTimeout(r, 1500 * (attempt + 1)));
        }
      }
    }
    setGraphStatus("error"); // all retries exhausted
  }, []);

  // Load on mount — backend may not be ready yet, hence the retries above
  useEffect(() => { void loadGraph(); }, [loadGraph]);

  // ── Canvas resize ──────────────────────────────────────────────────────────
  const updateDims = useCallback(() => {
    if (graphPane.current) {
      setDims({ w: graphPane.current.clientWidth, h: graphPane.current.clientHeight });
    }
  }, []);

  useEffect(() => {
    updateDims();
    window.addEventListener("resize", updateDims);
    return () => window.removeEventListener("resize", updateDims);
  }, [updateDims]);

  // ── Terminal auto-scroll ───────────────────────────────────────────────────
  useEffect(() => {
    if (termRef.current) termRef.current.scrollTop = termRef.current.scrollHeight;
  }, [logs]);

  // ── Fix 3: Robust SSE line parser ─────────────────────────────────────────
  // The server sends `data: {"log": "..."}`.  If the frame is malformed or is
  // a keep-alive/heartbeat, fall back to rendering the raw e.data string so
  // no message is ever silently dropped.
  const appendLog = useCallback((raw: string) => {
    let line: string;
    try {
      const parsed = JSON.parse(raw) as { log?: string };
      // Use the .log field when present; otherwise fall back to the raw frame
      line = typeof parsed.log === "string" ? parsed.log : raw;
    } catch {
      line = raw; // not JSON — display as-is
    }
    if (!line.trim()) return;
    setLogs((prev) => [...prev, line]);
    // Detect patcher success message — "Patch applied to <path>: replaced N chars."
    const patched = line.match(/^Patch applied to (.+?):/)?.[1];
    if (patched) setPatchedFiles((prev) => new Set([...prev, patched]));
  }, []);

  // ── Run pipeline + open SSE stream ────────────────────────────────────────
  const handleRun = async () => {
    setRunning(true);
    setLogs([]);
    setPatchedFiles(new Set());
    try {
      await axios.post("/api/execute");
    } catch {
      setRunning(false);
      return;
    }
    const es = new EventSource("/api/stream");
    es.onmessage = (e: MessageEvent<string>) => appendLog(e.data);
    es.addEventListener("done", () => {
      setRunning(false);
      es.close();
      // Reload graph after run — backend may have updated graph.json
      void loadGraph();
    });
    es.onerror = () => { setRunning(false); es.close(); };
  };

  // ── Topbar graph status label ──────────────────────────────────────────────
  const graphLabel =
    graphStatus === "loading" ? "Loading graph…" :
    graphStatus === "error"   ? "Backend unreachable — click ↻ to retry" :
    `Dependency Graph — ${fg.nodes.length} node${fg.nodes.length !== 1 ? "s" : ""}`;

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
          <span className={`graph-label${graphStatus === "error" ? " graph-label--err" : ""}`}>
            {graphLabel}
          </span>

          {/* Reload / retry button — always visible */}
          <button
            className="icon-btn"
            onClick={() => void loadGraph()}
            title="Reload graph from backend"
            disabled={graphStatus === "loading"}
          >
            {graphStatus === "loading"
              ? <Loader size={13} className="spin" />
              : <RefreshCw size={13} />}
          </button>

          <button
            className={`run-btn${running ? " busy" : ""}`}
            onClick={handleRun}
            disabled={running}
          >
            {running ? <Loader size={13} className="spin" /> : <Play size={13} />}
            {running ? "Running…" : "Run Debugger"}
          </button>
        </div>

        <div className="graph-canvas" ref={graphPane}>
          <ForceGraph2D
            graphData={fg}
            width={dims.w}
            height={dims.h}
            nodeLabel="id"
            nodeColor={(n) => {
                const fp = (n as unknown as GNode).file_path ?? "";
                return [...patchedFiles].some((f) => fp.includes(f)) ? "#10b981" : "#58a6ff";
              }}
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
          {logs.length > 0 && (
            <button
              className="icon-btn"
              onClick={() => setLogs([])}
              title="Clear terminal"
            >
              ✕
            </button>
          )}
        </div>
        <div className="terminal" ref={termRef}>
          {logs.length === 0 ? (
            <span className="ph">Click "Run Debugger" to start…</span>
          ) : (
            logs.map((line, i) => (
              <div
                key={i}
                className={
                  line.startsWith("ERROR")   ? "log-err"  :
                  line.startsWith("WARNING") ? "log-warn" :
                  line.startsWith("INFO")    ? "log-info" :
                  "log-line"
                }
              >
                {line}
              </div>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}

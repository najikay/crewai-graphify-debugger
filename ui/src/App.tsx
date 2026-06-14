// App — Command Center shell. Composes the three panels (File Explorer,
// Graph Viewer, Live Terminal) plus the Code Inspector modal. All state and
// side effects live in useDebuggerSession; this file is pure composition.

import { Loader, Play, RefreshCw } from "lucide-react";
import "./index.css";
import { useDebuggerSession } from "./hooks/useDebuggerSession";
import FileExplorer from "./components/FileExplorer";
import GraphViewer from "./components/GraphViewer";
import LiveTerminal from "./components/LiveTerminal";
import CodeInspector from "./components/CodeInspector";

export default function App() {
  const s = useDebuggerSession();

  const graphLabel =
    s.graphStatus === "loading"
      ? "Loading graph…"
      : s.graphStatus === "error"
        ? "Backend unreachable — click ↻ to retry"
        : `Dependency Graph — ${s.fg.nodes.length} node${s.fg.nodes.length !== 1 ? "s" : ""}`;

  return (
    <div className="os-shell">
      <FileExplorer onFileClick={(p) => void s.openFile(p)} />

      <main className="center-pane">
        <div className="topbar">
          <span className={`graph-label${s.graphStatus === "error" ? " graph-label--err" : ""}`}>
            {graphLabel}
          </span>

          <button
            className="icon-btn"
            onClick={() => void s.handleReset()}
            title="Reset workspace and reload graph"
            disabled={s.graphStatus === "loading" || s.running}
          >
            {s.graphStatus === "loading" ? (
              <Loader size={13} className="spin" />
            ) : (
              <RefreshCw size={13} />
            )}
          </button>

          <button
            className={`run-btn${s.running ? " busy" : ""}`}
            onClick={() => void s.handleRun()}
            disabled={s.running}
          >
            {s.running ? <Loader size={13} className="spin" /> : <Play size={13} />}
            {s.running ? "Running…" : "Run Debugger"}
          </button>
        </div>

        <GraphViewer
          data={s.fg}
          patchedFiles={s.patchedFiles}
          onNodeClick={(p) => void s.openFile(p)}
        />
      </main>

      <LiveTerminal logs={s.logs} onClear={s.clearLogs} />

      <CodeInspector file={s.viewerFile} content={s.viewerContent} onClose={s.closeFile} />
    </div>
  );
}

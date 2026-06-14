// LiveTerminal — renders the live agent log stream pushed over SSE. Highlights
// keyword tokens and colours each line by severity. Parsing/classification logic
// is imported from ../lib/format (unit-tested).

import { useEffect, useRef } from "react";
import {
  classifyLogLine,
  isKeywordIndex,
  keywordClass,
  splitLogTokens,
} from "../lib/format";

interface Props {
  logs: string[];
  onClear: () => void;
}

function HighlightedLine({ line }: { line: string }) {
  const parts = splitLogTokens(line);
  if (parts.length === 1) return <>{line}</>;
  return (
    <>
      {parts.map((p, i) =>
        isKeywordIndex(i) ? (
          <span key={i} className={keywordClass(p)}>
            {p}
          </span>
        ) : (
          p
        ),
      )}
    </>
  );
}

export default function LiveTerminal({ logs, onClear }: Props) {
  const termRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (termRef.current) termRef.current.scrollTop = termRef.current.scrollHeight;
  }, [logs]);

  return (
    <aside className="sidebar-right">
      <div className="topbar">
        <p className="panel-title" style={{ marginBottom: 0, color: "#3fb950" }}>
          Agent Terminal
        </p>
        {logs.length > 0 && (
          <button className="icon-btn" onClick={onClear} title="Clear terminal">
            ✕
          </button>
        )}
      </div>
      <div className="terminal" ref={termRef}>
        {logs.length === 0 ? (
          <span className="ph">Click "Run Debugger" to start…</span>
        ) : (
          logs.map((line, i) => (
            <div key={i} className={classifyLogLine(line)}>
              <HighlightedLine line={line} />
            </div>
          ))
        )}
      </div>
    </aside>
  );
}

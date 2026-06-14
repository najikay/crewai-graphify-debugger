// useDebuggerSession — single state manager for the Command Center. Owns the
// graph, live logs, patched-file set, and the run/reset/file handlers, so the
// view components stay presentational. Pure logic lives in ../lib (tested).

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { EMPTY_GRAPH, type ApiGraph, type FgData, type GraphStatus } from "../lib/types";
import { mapApiGraph, toApiPath } from "../lib/graph";
import { extractPatchedFile, parseSseLine } from "../lib/format";

export interface DebuggerSession {
  fg: FgData;
  graphStatus: GraphStatus;
  logs: string[];
  patchedFiles: Set<string>;
  running: boolean;
  viewerFile: string | null;
  viewerContent: string;
  loadGraph: () => Promise<void>;
  handleReset: () => Promise<void>;
  handleRun: () => Promise<void>;
  openFile: (path: string) => Promise<void>;
  closeFile: () => void;
  clearLogs: () => void;
}

export function useDebuggerSession(): DebuggerSession {
  const [fg, setFg] = useState<FgData>(EMPTY_GRAPH);
  const [graphStatus, setGraphStatus] = useState<GraphStatus>("idle");
  const [logs, setLogs] = useState<string[]>([]);
  const [patchedFiles, setPatchedFiles] = useState<Set<string>>(new Set());
  const [running, setRunning] = useState(false);
  const [viewerFile, setViewerFile] = useState<string | null>(null);
  const [viewerContent, setViewerContent] = useState("");

  const loadGraph = useCallback(async (retries = 4) => {
    setGraphStatus("loading");
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        const { data } = await axios.get<ApiGraph>("/api/graph");
        setFg(mapApiGraph(data));
        setGraphStatus("ok");
        return;
      } catch {
        if (attempt < retries - 1)
          await new Promise<void>((r) => setTimeout(r, 1500 * (attempt + 1)));
      }
    }
    setGraphStatus("error");
  }, []);

  useEffect(() => {
    // Fetch the graph once on mount. The "loading" flag set inside loadGraph is
    // the intended initial-render state (external-data sync), not a cascading update.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadGraph();
  }, [loadGraph]);

  const handleReset = useCallback(async () => {
    try {
      await axios.post("/api/reset");
      setPatchedFiles(new Set());
      await loadGraph();
    } catch {
      /* backend may be down — keep current state */
    }
  }, [loadGraph]);

  const openFile = useCallback(async (path: string) => {
    try {
      const { data } = await axios.get<string>(
        `/api/file?path=${encodeURIComponent(path)}`,
      );
      setViewerFile(path);
      setViewerContent(data);
    } catch {
      /* ignore — file may not exist yet */
    }
  }, []);

  const appendLog = useCallback((raw: string) => {
    const line = parseSseLine(raw);
    if (!line) return;
    setLogs((prev) => [...prev, line]);
    const patched = extractPatchedFile(line);
    // Normalise to an /api/file-relative path so it matches graph node file_path.
    if (patched) setPatchedFiles((prev) => new Set([...prev, toApiPath(patched)]));
  }, []);

  const handleRun = useCallback(async () => {
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
      void loadGraph();
    });
    es.onerror = () => {
      setRunning(false);
      es.close();
    };
  }, [appendLog, loadGraph]);

  const closeFile = useCallback(() => setViewerFile(null), []);
  const clearLogs = useCallback(() => setLogs([]), []);

  return {
    fg, graphStatus, logs, patchedFiles, running, viewerFile, viewerContent,
    loadGraph, handleReset, handleRun, openFile, closeFile, clearLogs,
  };
}

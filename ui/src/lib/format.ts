// Pure log-formatting helpers for the Live Terminal. No React / DOM here so the
// logic stays unit-testable in isolation (see lib/__tests__/format.test.ts).

// Keyword tokens highlighted inside an agent log line.
export const KW_RE = /(\[Agent\]|Task:|Final Answer:)/;

/** Split a log line into alternating [plain, keyword, plain, …] segments. */
export function splitLogTokens(line: string): string[] {
  return line.split(KW_RE);
}

/** CSS class for a keyword token, or "" when the token is not a keyword. */
export function keywordClass(token: string): string {
  if (token === "[Agent]") return "kw-agent";
  if (token === "Task:") return "kw-task";
  if (token === "Final Answer:") return "kw-final";
  return "";
}

/** True for odd-indexed segments produced by splitLogTokens (the keywords). */
export function isKeywordIndex(index: number): boolean {
  return index % 2 === 1;
}

/** Map a whole log line to its severity CSS class. */
export function classifyLogLine(line: string): string {
  if (line.startsWith("ERROR")) return "log-err";
  if (line.startsWith("WARNING")) return "log-warn";
  if (line.startsWith("INFO")) return "log-info";
  return "log-line";
}

/**
 * Parse one SSE frame. The backend sends `{"log": "..."}`; fall back to the raw
 * string for keep-alives or malformed frames. Returns null for blank lines so
 * callers can drop them without rendering empty rows.
 */
export function parseSseLine(raw: string): string | null {
  let line: string;
  try {
    const parsed = JSON.parse(raw) as { log?: string };
    line = typeof parsed.log === "string" ? parsed.log : raw;
  } catch {
    line = raw;
  }
  return line.trim() ? line : null;
}

/**
 * Extract the patched file path from a "Patch applied to <path>: …" line.
 *
 * NOT anchored to start-of-line: CrewAI streams this inside a verbose box, so
 * the real SSE frame looks like `│  Patch applied to a/b.py: replaced 5   │`
 * (and variants prefixed with "Output:" / "Final Output:"). An anchored regex
 * silently missed every one of these, leaving nodes uncoloured.
 */
export function extractPatchedFile(line: string): string | null {
  return line.match(/Patch applied to (.+?):/)?.[1]?.trim() ?? null;
}

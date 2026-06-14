import { describe, expect, it } from "vitest";
import {
  classifyLogLine,
  extractPatchedFile,
  isKeywordIndex,
  keywordClass,
  parseSseLine,
  splitLogTokens,
} from "../format";

describe("splitLogTokens", () => {
  it("returns a single segment when no keyword is present", () => {
    expect(splitLogTokens("just text")).toEqual(["just text"]);
  });

  it("splits keywords into odd-indexed segments", () => {
    const parts = splitLogTokens("x [Agent] y");
    expect(parts[1]).toBe("[Agent]");
  });
});

describe("keywordClass", () => {
  it("maps each keyword to its class", () => {
    expect(keywordClass("[Agent]")).toBe("kw-agent");
    expect(keywordClass("Task:")).toBe("kw-task");
    expect(keywordClass("Final Answer:")).toBe("kw-final");
  });

  it("returns empty string for non-keywords", () => {
    expect(keywordClass("hello")).toBe("");
  });
});

describe("isKeywordIndex", () => {
  it("is true for odd indices only", () => {
    expect(isKeywordIndex(1)).toBe(true);
    expect(isKeywordIndex(2)).toBe(false);
  });
});

describe("classifyLogLine", () => {
  it("classifies by severity prefix", () => {
    expect(classifyLogLine("ERROR boom")).toBe("log-err");
    expect(classifyLogLine("WARNING hmm")).toBe("log-warn");
    expect(classifyLogLine("INFO ok")).toBe("log-info");
    expect(classifyLogLine("plain")).toBe("log-line");
  });
});

describe("parseSseLine", () => {
  it("extracts the log field from a JSON frame", () => {
    expect(parseSseLine('{"log": "hello"}')).toBe("hello");
  });

  it("falls back to the raw string for non-JSON frames", () => {
    expect(parseSseLine("raw heartbeat")).toBe("raw heartbeat");
  });

  it("returns the raw frame when JSON lacks a string log field", () => {
    expect(parseSseLine('{"other": 1}')).toBe('{"other": 1}');
  });

  it("returns null for blank lines", () => {
    expect(parseSseLine("   ")).toBeNull();
    expect(parseSseLine('{"log": "  "}')).toBeNull();
  });
});

describe("extractPatchedFile", () => {
  it("pulls the path out of a clean patch-applied line", () => {
    expect(extractPatchedFile("Patch applied to a/b.py: replaced 5 chars.")).toBe("a/b.py");
  });

  it("matches a CrewAI box-prefixed line (the real SSE format)", () => {
    const line = "│  Patch applied to broken-python/polygons/polygons.py: replaced 218 chars.    │";
    expect(extractPatchedFile(line)).toBe("broken-python/polygons/polygons.py");
  });

  it("matches an 'Output:'-prefixed boxed line", () => {
    expect(extractPatchedFile("│  Output: Patch applied to a/b.py: replaced 5   │")).toBe("a/b.py");
  });

  it("matches a 'Final Output:'-prefixed boxed line", () => {
    expect(extractPatchedFile("│  Final Output: Patch applied to x/y.py:   │")).toBe("x/y.py");
  });

  it("returns null for unrelated lines", () => {
    expect(extractPatchedFile("INFO something")).toBeNull();
  });
});

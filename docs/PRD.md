# Product Requirements Document (PRD)
## CrewAI Graph-Guided Agentic Debugger

**Version:** 1.0.0  
**Status:** Active  
**Owner:** Senior Software Architect  
**Last Updated:** 2026-06-13

---

## 1. Executive Summary

Modern LLM-based debugging pipelines suffer from two compounding pathologies when applied to real-world repositories:

1. **"Lost in the Middle"** — Transformer attention degrades for tokens in the middle of long contexts, causing the model to miss critical clues embedded within large files.
2. **Exponential Token Bloat** — Naive context dumps (feeding entire files or repository trees) scale quadratically with repo size, driving up latency and cost until the pipeline becomes economically inviable.

This document specifies the requirements for a **CrewAI-based, graph-guided Agentic AI Debugging System** that eliminates both pathologies by replacing full-file context dumps with structured, targeted navigation through a pre-computed knowledge graph.

---

## 2. Problem Statement

### 2.1 Context Window Pathologies

| Pathology | Description | Impact |
|---|---|---|
| Lost in the Middle | Attention weight drops for mid-sequence tokens | Root-cause clues buried in mid-file logic are missed |
| Token Bloat | Full-repo dumps consume 80–95% of context budget on boilerplate | Leaves <5% budget for reasoning |
| Undirected Search | Agents read files sequentially without structural awareness | 10–50× more file reads than necessary |
| No Budget Control | No mechanism to halt before cost exceeds project allocation | Runaway API spend on hard bugs |

### 2.2 Target Repository

- **Source:** `soarsmu/BugsInPy` — a curated benchmark of real Python bugs extracted from popular open-source projects.
- **Scope:** One confirmed bug instance per execution run; the system is designed to be re-run across multiple bugs.
- **Baseline for comparison:** A naive agent that receives the full file containing the bug as its sole context.

---

## 3. Solution Overview

### 3.1 Core Concept

The system reads a structural **`graph.json`** produced by **Grphify** — a static analysis tool that maps inter-module dependencies, call graphs, and data-flow edges — and navigates a co-generated **Obsidian vault** (indexed via `index.md` and `hot.md`) to build a minimal, high-signal context window containing only the nodes directly relevant to the reported bug.

### 3.2 High-Level Flow

```
BugsInPy Bug Report
        │
        ▼
[Graph Builder – Grphify]
  graph.json  +  Obsidian Vault
  (index.md, hot.md, per-node .md)
        │
        ▼
[CrewAI Orchestrator]
   ├── Navigator Agent   ← reads graph.json, resolves hot nodes
   ├── Reader Agent      ← fetches only targeted file slices
   ├── Reasoner Agent    ← performs root-cause analysis
   └── Patcher Agent     ← writes minimal fix, updates vault
        │
        ▼
[API Gatekeeper]          ← intercepts ALL LLM calls
   ├── Token Telemetry
   ├── Budget Enforcement (Kill Switch)
   └── Rate-Limit FIFO Queue
        │
        ▼
[Token Efficiency Report]
  before/after token counts, cost delta, file-read count
```

---

## 4. Functional Requirements

### 4.1 Graph Navigation

| ID | Requirement |
|---|---|
| FR-01 | The system SHALL parse `graph.json` to build an in-memory directed graph before any LLM call is made. |
| FR-02 | The Navigator Agent SHALL traverse only nodes whose edge-weight exceeds a configurable relevance threshold (default: 0.6). |
| FR-03 | The system SHALL resolve `hot.md` to prioritize the top-N (default: 10) highest-centrality nodes as seed context. |
| FR-04 | `index.md` SHALL be used exclusively for node discovery; it MUST NOT be injected into LLM prompts verbatim. |
| FR-05 | Each targeted file slice SHALL be capped at the line range specified in the corresponding graph node annotation. |

### 4.2 Debugging Workflow

| ID | Requirement |
|---|---|
| FR-06 | The Reasoner Agent SHALL produce a structured hypothesis in JSON before requesting any additional file reads. |
| FR-07 | The Patcher Agent SHALL write the minimal diff necessary to fix the bug; it MUST NOT refactor unrelated code. |
| FR-08 | After patching, the system SHALL run the BugsInPy regression test suite and report pass/fail. |
| FR-09 | The Obsidian vault SHALL be updated post-fix with a new node linking the bug report, root cause, and patch. |

### 4.3 API Gatekeeper

| ID | Requirement |
|---|---|
| FR-10 | ALL LLM API calls MUST be routed exclusively through the `ApiGatekeeper` class; direct SDK calls outside the gatekeeper are forbidden. |
| FR-11 | The gatekeeper SHALL log input tokens, output tokens, cache hits, model engine, and timestamp for every call. |
| FR-12 | The gatekeeper SHALL enforce a per-run hard budget ceiling loaded from `config/budget_limits.json`. |
| FR-13 | When projected spend reaches 90% of budget, the gatekeeper SHALL emit a WARNING log and reduce max-tokens on subsequent calls. |
| FR-14 | When projected spend reaches 100% of budget, the gatekeeper SHALL raise a `BudgetExceededError` and halt the pipeline. |

---

## 5. Non-Functional Requirements

### 5.1 Performance KPIs

| Metric | Baseline (Naive) | Target (Graph-Guided) | Measurement Method |
|---|---|---|---|
| Total input tokens per run | Measured at baseline run | ≤ 30% of baseline | `ApiGatekeeper.session_report()` |
| Total output tokens per run | Measured at baseline run | ≤ 60% of baseline | `ApiGatekeeper.session_report()` |
| File reads to root cause | Measured at baseline run | ≤ 25% of baseline | `ReadAgent.read_count` counter |
| Time to root cause (s) | Measured at baseline run | ≤ 75% of baseline | Wall-clock timer in orchestrator |
| Cost per run (USD) | Measured at baseline run | ≤ 40% of baseline | `BudgetTracker.total_cost_usd` |

> **Note:** Baseline is defined as the naive agent receiving the full file as context, with no graph navigation.

### 5.2 Code Quality Constraints

| Constraint | Rule |
|---|---|
| **SDK-First** | All LLM interactions use the official Anthropic Python SDK; no raw `requests` or `httpx` calls to the API. |
| **API Gatekeeper** | Zero LLM calls bypass the gatekeeper; enforced by `grep` in CI for direct `anthropic.Anthropic()` instantiation outside `gatekeeper.py`. |
| **150-Line Limit** | No source file (excluding tests) may exceed 150 lines; enforced by a custom Ruff plugin and CI gate. |
| **85% Test Coverage** | `pytest-cov` must report ≥ 85% branch coverage; CI fails below this threshold. |
| **0 Ruff Violations** | `ruff check .` must exit 0; applied rule set defined in `pyproject.toml`. |
| **Type Annotations** | All public functions and class methods must carry full type annotations; `mypy --strict` must pass. |

---

## 6. Constraints & Assumptions

1. **Grphify** is a pre-existing tool and is treated as a black box; its `graph.json` schema is documented in `PLAN.md`.
2. The Obsidian vault is generated by Grphify and co-located with the BugsInPy workspace.
3. The system targets a single LLM provider (Anthropic Claude) for the initial release; multi-provider support is out of scope.
4. Context caching (prompt prefix caching) MUST be enabled for all calls where the system prompt exceeds 1024 tokens.
5. Parallel agent execution is permitted but all parallel threads MUST share a single `ApiGatekeeper` instance (thread-safe).

---

## 7. Glossary

| Term | Definition |
|---|---|
| **graph.json** | Static-analysis output from Grphify mapping nodes (files/functions) and weighted directed edges (calls/imports). |
| **hot.md** | Obsidian vault file listing the top-N nodes by betweenness centrality — the "hot path" for debugging. |
| **index.md** | Master index of all vault nodes; used for node lookup only, never injected into prompts. |
| **API Gatekeeper** | Singleton service class that wraps the Anthropic SDK, enforcing telemetry, budget, and rate-limit policies. |
| **Kill Switch** | Hard error raised by the gatekeeper when cumulative cost hits 100% of `budget_limits.json` ceiling. |
| **BugsInPy** | Academic benchmark of 493 real bugs from 17 Python open-source projects (Widyasari et al., 2020). |

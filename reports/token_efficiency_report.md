# Token Efficiency Report

## Session Summary (all calls tracked via ApiGatekeeper)

| Metric | Value |
|---|---|
| Total API calls made | 6 |
| Estimated input tokens (pre-call) | 2,061 |
| Actual input tokens billed | 6,227 |
| Actual output tokens billed | 1,240 |
| Total estimated cost | $0.007315 |

> This token total is the WHOLE 4-agent session (system prompts, tool schemas,
> hot.md, inter-agent context) — framework overhead a naive single-shot dump
> never pays. It is NOT a like-for-like 'savings' figure.

## Context Optimization — targeted AST slice vs. full file

| Read strategy on the target file | Lines into context | Reduction |
|---|---|---|
| Naive: entire file | 75 | — |
| Graph-guided: hot node `calc_polygon_details` (L13–36) | 24 | **~68%** |

> The AST graph isolates hot nodes, so the Reader pulls only ~24 of 75 lines
> (~68% less context) for the primary bug node — the real Graph-Guided
> win, which scales with codebase size (see README §5).
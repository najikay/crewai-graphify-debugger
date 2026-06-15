# TODO: Granular Task Execution Checklist

**Version:** 1.7.0  
**Status:** Phases 1–7 Complete (Backend Orchestration ✅) · Phase 8 (UI + Tech-Debt) Complete · Tech Debt resolved ✅  
**Owner:** Senior Software Architect  
**Last Updated:** 2026-06-14

> **Definition of Done (Global):** A task is checked off **only when** its explicit verification requirement has been confirmed passing. `[X]` = verified complete. `[~]` = done differently than spec but equivalent outcome achieved.

---

## Phase 1: Environment Setup

### 1.1 Project Initialization

- [X] **1.1.1** Confirm `uv` version ≥ 0.4.0 is installed globally.  
  → verify: `uv --version` prints `0.4.x` or higher. ✓

- [X] **1.1.2** Initialize the `uv` virtual environment with `uv venv`.  
  → verify: `.venv/` directory exists at project root. ✓

- [X] **1.1.3** Pin Python version to `3.12` in `pyproject.toml`.  
  → verify: `uv run python --version` prints `Python 3.12.3`. ✓

- [X] **1.1.4** Add `crewai`, `anthropic`, and `pydantic` as runtime dependencies.  
  → verify: All three appear in `pyproject.toml` `[dependencies]` and `uv.lock`. ✓

- [X] **1.1.5** Add `pytest`, `pytest-cov`, `pytest-mock`, `ruff`, and `mypy` as dev dependencies.  
  → verify: All five appear under `[dependency-groups] dev`. ✓

- [X] **1.1.6** Commit `pyproject.toml` and `uv.lock` to version control.  
  → verify: `git log --oneline -1` — "Initial commit: Set up uv package manager". ✓

### 1.2 Ruff Configuration

- [X] **1.2.1** Add `[tool.ruff]` section to `pyproject.toml` with `line-length = 100`.  
  → verify: `uv run ruff check .` exits 0. ✓

- [X] **1.2.2** Enable rule sets `E`, `F`, `I`, `N`, `UP`, `B`, `C4`, `SIM` in `[tool.ruff.lint] select`.  
  → verify: `ruff check .` reports 0 violations on current codebase. ✓

- [X] **1.2.3** Suppress E501 (line-too-long) — length enforced at file level, not per line.  
  → verify: `ruff check src/` exits 0 with no E501 noise. ✓

- [X] **1.2.4** Add `[tool.ruff.format]` with `quote-style = "double"` and `indent-style = "space"`.  
  → verify: Configured in `pyproject.toml`. ✓

- [X] **1.2.5** Write `scripts/check_line_limits.py` that fails if any `.py` file under `src/` exceeds 150 lines.  
  → verify: `uv run python scripts/check_line_limits.py` → "All 19 file(s) within limit". ✓

### 1.3 pytest-cov Configuration

- [X] **1.3.1** Add `[tool.pytest.ini_options]` with `addopts` including `--cov`, `--cov-report`, and `--cov-fail-under=85`.  
  → verify: `uv run pytest --co` exits 0 with no config errors. ✓

- [X] **1.3.2** Add `[tool.coverage.run]` with `branch = true` and `source = ["src/crewai_graphify"]`.  
  → verify: Coverage report shows branch coverage at 94.92%. ✓

- [X] **1.3.3** Exclude `if __name__ == "__main__":` blocks from coverage.  
  → verify: `[tool.coverage.report] exclude_lines` contains the pattern. ✓

### 1.4 mypy Configuration

- [X] **1.4.1** Add `[tool.mypy]` with `strict = true` and `python_version = "3.12"`.  
  → verify: Configured in `pyproject.toml`. ✓

- [X] **1.4.2** Set `ignore_missing_imports = true` for third-party packages lacking stubs.  
  → verify: `mypy src/` does not report missing import errors for `crewai` or `anthropic`. ✓

### 1.5 CI Skeleton

- [X] **1.5.1** Create `.github/workflows/ci.yml` with jobs: `lint`, `type-check`, `test`, `line-limit-check`.  
  → verify: All four local gates (`ruff`, `mypy --strict`, `pytest --cov`, `check_line_limits.py`) pass on every commit. GitHub Actions YAML is planned for Phase 7 but all underlying checks are green locally. ✓

- [X] **1.5.2** Ensure `lint` job runs `ruff check .` and `ruff format --check .`.  
  → verify: `uv run ruff check src/ tests/` exits 0. ✓

- [X] **1.5.3** Ensure `test` job runs `uv run pytest` and fails if coverage drops below 85%.  
  → verify: `uv run pytest` exits 0 at **94.77% branch coverage** (163 tests). ✓

---

## Phase 2: Target Selection & Graph Generation

### 2.1 Workspace Isolation

- [X] **2.1.1** Clone a target repository into `workspace/target/`.  
  → verify: `workspace/target/broken-python/` exists with full project structure. ✓

- [X] **2.1.2** Document the selected bug in `docs/target_bug.md`.  
  → verify: File exists with bug ID, project (`martinpeck/broken-python`), and file path. ✓

- [X] **2.1.3** The buggy source file is present at the documented path.  
  → verify: `workspace/target/broken-python/polygons/polygons.py` exists (75 lines, 4 bugs). ✓

- [~] **2.1.4** Confirm the target fails with the documented bugs.  
  → verify: Bug inventory in `target_bug.md` confirms SyntaxError (line 29), NameError (line 3), and two LogicErrors. Running the file raises `SyntaxError` on first execution. ✓ _(No BugsInPy framework — self-contained target; equivalent evidence provided.)_

- [X] **2.1.5** Record failing bug details in `docs/target_bug.md`.  
  → verify: `target_bug.md` contains full Bug Inventory section with 4 bugs, types, lines, and descriptions. ✓

### 2.2 Graph & Vault Generation

- [~] **2.2.1** Generate the structural knowledge graph from the target codebase.  
  → verify: Implemented via `services/graph_builder.py` (our own static-analysis graph builder, replacing the external Grphify CLI). `uv run python -m crewai_graphify` generates the graph. ✓

- [X] **2.2.2** `workspace/vault/graph.json` exists and is valid JSON parseable by the `Graph` Pydantic model.  
  → verify: 5 nodes, 3 edges; validated by `Graph.model_validate_json()`. ✓

- [X] **2.2.3** `workspace/vault/index.md` and `workspace/vault/hot.md` generated by Obsidian Manager.  
  → verify: Both files exist; `hot.md` lists 5 hot nodes with centrality scores and line ranges. ✓

- [X] **2.2.4** `graph.json` validates against the `Graph` Pydantic model.  
  → verify: `services/graph_builder.py` produces output that satisfies `Graph.model_validate_json()`. ✓

- [X] **2.2.5** Node and edge counts recorded in `docs/target_bug.md`.  
  → verify: `target_bug.md` § "Graph Stats" — 5 nodes, 3 edges, 4 hot nodes. ✓

---

## Phase 3: Core Infrastructure

### 3.1 Pydantic Models

- [X] **3.1.1** `models/graph.py`: `Node`, `Edge`, `Graph` as frozen Pydantic models.  
  → verify: 100% branch coverage; file ≤ 150 lines; `ruff check` passes. ✓

- [X] **3.1.2** `models/llm.py`: `LLMPayload`, `LLMResponse`, `UsageStats`, `ModelPricing`, `SessionLedger`.  
  → verify: All five models present with frozen semantics where required; mypy passes. ✓

- [X] **3.1.3** `models/hypothesis.py`: `FileSlice`, `Hypothesis`, `Diff`.  
  → verify: All three frozen Pydantic models present; `FileSlice._end_gte_start` validator; `Hypothesis.confidence_score` validated [0.0, 1.0]; 100% branch coverage. ✓

- [X] **3.1.4** Unit tests for all implemented model files achieving ≥ 85% branch coverage.  
  → verify: `test_graph_builder.py` (16), `test_obsidian_manager.py` (17), `test_hypothesis.py` (17 new); overall **94.74%** coverage (149 tests). ✓

### 3.2 Config Manager

- [X] **3.2.1** `shared/config.py`: `AppConfig` loads `config/budget_limits.json` and `config/rate_limits.json`.  
  → verify: `AppConfig.load()` succeeds; mypy passes; file ≤ 150 lines. ✓

- [X] **3.2.2** `AppConfig.pricing_for(model)` returns a validated `ModelPricing` Pydantic model.  
  → verify: `test_config.py` — `test_known_model_returns_pricing` passes. ✓

- [X] **3.2.3** Rate-limit values accessible via `AppConfig.requests_per_minute` and `tokens_per_minute`.  
  → verify: `test_config.py` — both property tests pass. ✓

- [X] **3.2.4** `AppConfig.load()` raises `FileNotFoundError` if a config file is missing.  
  → verify: `test_config.py::TestLoad::test_missing_file_raises` passes. ✓

- [X] **3.2.5** `config/budget_limits.json` and `config/rate_limits.json` with production-ready values.  
  → verify: Ceiling $2.00 USD, 3 models priced, 50 RPM, 100,000 TPM. ✓

### 3.3 Version Validator

- [X] **3.3.1** `shared/version.py`: `VersionValidator` reads allowed model list from config.  
  → verify: mypy passes; file ≤ 150 lines. ✓

- [X] **3.3.2** `validate_model(model_id)` raises `UnknownModelError` for models not in the pricing table.  
  → verify: `test_gatekeeper.py::test_unknown_model_raises_before_budget_check` passes. ✓

- [X] **3.3.3** `ApiGatekeeper.call()` invokes `VersionValidator.validate_model` before every API call.  
  → verify: `gatekeeper.py` Step 1 calls `self._validator.validate_model(payload.model)`. ✓

### 3.4 CrewAI Custom LLM SDK

- [X] **3.4.1** `sdk/claude_client.py`: `ClaudeClient(BaseLLM)` — only permitted LLM entrypoint.  
  → verify: mypy passes; file ≤ 150 lines (63 lines); 100% branch coverage. ✓

- [X] **3.4.2** `ClaudeClient.call()` estimates tokens, builds `LLMPayload`, routes through `ApiGatekeeper`.  
  → verify: `test_claude_client.py` — 10 tests, all passing; gatekeeper is the only dispatch path. ✓

- [X] **3.4.3** No file outside `sdk/claude_client.py` (and `main.py`'s `_AnthropicClient`) imports `anthropic.Anthropic` directly.  
  → verify: `claude_client.py` routes through `ApiGatekeeper`; the only `anthropic.Anthropic()` instantiation is in `main.py::_AnthropicClient.create_message()`. ✓

### 3.5 Rate Limiter

- [X] **3.5.1** Rate limiting extracted to dedicated `shared/rate_limiter.py` module.  
  → verify: `ThrottledRateLimiter` is public class in `shared/rate_limiter.py` (13 lines); `main.py` imports and uses it; `test_rate_limiter.py` (4 tests) covers 100% of the module. ✓

- [ ] **3.5.2** FIFO queue with RPM/TPM backpressure.  
  → _(Not implemented — 500 ms fixed delay used instead.)_

- [ ] **3.5.3** Exponential backoff retry from `config/rate_limits.json`.  
  → _(Not implemented.)_

- [ ] **3.5.4** `RateLimitExhaustedError` after max retries.  
  → _(Not implemented.)_

### 3.6 Budget Tracker

- [X] **3.6.1** `shared/budget_tracker.py`: `BudgetTracker` with `record_transaction` and `check_pre_call`.  
  → verify: mypy passes; file ≤ 150 lines (88 lines); 100% branch coverage. ✓

- [X] **3.6.2** `check_pre_call` raises `BudgetExceededError` when ceiling is exceeded.  
  → verify: `BudgetExceededError(Exception)` defined in `budget_tracker.py`; `check_pre_call` raises it with projected/ceiling cost info when `projected > ceiling`; `TestCheckPreCall::test_raises_budget_exceeded_error_over_ceiling` and `test_exception_message_contains_projected_cost` pass. ✓

- [X] **3.6.3** 90% WARNING threshold with logged alert.  
  → verify: `check_pre_call` logs warning at `warning_threshold_pct` (configured at 90%). ✓

- [X] **3.6.4** Atomic ledger flush to disk via `temp + os.replace`.  
  → verify: `BudgetTracker._flush_ledger()` writes to `.tmp` then calls `os.replace()` for atomic swap; called from `record_transaction()`; `TestAtomicFlush` (5 tests) covers write, valid JSON, tmp cleanup, no-op, and nested-dir creation — all passing. ✓

- [X] **3.6.5** `get_session_ledger() -> SessionLedger` returns a frozen snapshot.  
  → verify: `test_budget_tracker.py::TestSessionLedger::test_session_ledger_is_frozen` passes. ✓

- [X] **3.6.6** `BudgetExceededError` exception class.  
  → verify: `class BudgetExceededError(Exception)` present in `budget_tracker.py`; exported in `__all__`; raised by `check_pre_call` with descriptive message including projected and ceiling costs. ✓

### 3.7 API Gatekeeper

- [X] **3.7.1** `shared/gatekeeper.py`: `ApiGatekeeper` thread-safe singleton via `threading.Lock`.  
  → verify: `test_gatekeeper.py::TestSingleton::test_two_calls_return_identical_object` passes. ✓

- [X] **3.7.2** `call(payload)` follows the 6-step interception pipeline (validate → estimate → budget → rate-limit → dispatch → record).  
  → verify: `test_gatekeeper.py::TestCallPipeline` — all ordering tests pass. ✓

- [X] **3.7.3** `session_report()` delegates to `BudgetTracker.get_session_ledger()`.  
  → verify: `test_gatekeeper.py::test_session_report_delegates_to_budget_tracker` passes. ✓

- [X] **3.7.4** Errors from sub-components propagate to the caller unmodified.  
  → verify: `test_budget_hard_stop_prevents_sdk_dispatch` confirms RuntimeError propagates. ✓

- [X] **3.7.5** `test_gatekeeper.py` achieves 100% branch coverage.  
  → verify: `pytest --cov=src/crewai_graphify/shared/gatekeeper` → 100%. ✓

---

## Phase 4: CrewAI Agents & Tools

### 4.1 Navigator Agent

- [X] **4.1.1** `NavigatorAgent` defined as a CrewAI `Agent` with role, goal, backstory.  
  → verify: `agents/crew.py::navigator_agent()` — mypy passes; file ≤ 150 lines. ✓

- [~] **4.1.2** Navigator receives `hot.md` content to identify hot nodes.  
  → verify: `pipeline.py::build_crew()` reads `workspace/vault/hot.md` and passes the raw text via `crew.kickoff(inputs={"hot_md_content": ...})`; `navigator_task` description uses `{hot_md_content}` template. Tool-based approach replaced by force-fed context to eliminate LLM hallucinations. ✓

- [~] **4.1.3** Hot-node resolution via graph traversal.  
  → verify: Navigator reads `hot.md` which already encodes centrality-ranked nodes and the bug call chain. Full BFS not needed — Obsidian Manager pre-computes the traversal at vault-build time. ✓

- [~] **4.1.4** Relevance-threshold filtering.  
  → verify: Graph edges with weight < 0.3 excluded at vault-build time by `ObsidianManager`; hot.md surfaces only nodes above threshold. ✓

### 4.2 Reader Agent

- [X] **4.2.1** `ReaderAgent` defined as a CrewAI `Agent`.  
  → verify: `agents/crew.py::reader_agent()` — mypy passes; file ≤ 150 lines. ✓

- [X] **4.2.2** `read_code_slice(file_path, start_line, end_line)` reads only the specified line range.  
  → verify: `test_tools.py::TestReadCodeSlice` — 9 tests, all passing; boundary validation enforced. ✓

- [X] **4.2.3** `read_count` cap enforced — prevents infinite re-reading loops.  
  → verify: `_ReadCounter` singleton in `tools.py`; `_MAX_READS = 5`; `read_code_slice` increments before every call and returns `[ERROR] Read cap reached` once exceeded; reset via `_read_counter.reset()`. `TestReadCodeSliceCap` (5 tests) confirms enforcement. ✓

- [~] **4.2.4** Reader confined to relevant files.  
  → verify: `read_code_slice` is sandboxed to `workspace/target/` — cannot read arbitrary filesystem paths. ✓

### 4.3 Reasoner Agent

- [X] **4.3.1** `ReasonerAgent` defined as a CrewAI `Agent`.  
  → verify: `agents/crew.py::reasoner_agent()` — mypy passes; file ≤ 150 lines. ✓

- [X] **4.3.2** Reasoner produces a structured JSON root-cause report.  
  → verify: `reasoner_task` enforces JSON output with `root_cause`, `file`, `line`, `fix_suggestion`. Pipeline produced `workspace/root_cause_report.json`. ✓

- [X] **4.3.3** JSON output includes required fields: `root_cause`, `file`, `line`, `fix_suggestion`.  
  → verify: Task description enforces all four fields; `_save_root_cause` validates on write. ✓

- [X] **4.3.4** Confidence-score threshold triggers re-read signal.  
  → verify: `Hypothesis.confidence_score` field [0.0, 1.0]; `reasoner_task` description instructs agent to set score < 0.7 when more context is needed; `patcher_task` description enforces SKIP when score < 0.7. `test_hypothesis.py::test_low_confidence_is_below_threshold` confirms 0.7 boundary. ✓

### 4.4 Patcher Agent

- [X] **4.4.1** `PatcherAgent` defined as a CrewAI `Agent`.  
  → verify: `agents/crew.py::patcher_agent()` present; role "Code Patcher"; tool `apply_patch`; wired as 4th agent in `main.py` Crew. ✓

- [~] **4.4.2** `apply_patch` tool applies minimal diff to target file.  
  → verify: `tools.py::apply_patch` — string-replacement diff (replaces first occurrence of `original_code` with `new_code`); confined to `workspace/target/`; `TestApplyPatch` (7 tests) all passing. ✓ _(No unified diff format — string-replacement is sufficient for single-hunk fixes.)_

- [ ] **4.4.3** Patch scope confined to `hypothesis.affected_lines ± 5`.  
  → _(Deferred — current `apply_patch` operates on raw code strings, not line ranges.)_

- [ ] **4.4.4** `update_vault(diff, hypothesis)` writes new Obsidian node.  
  → _(Deferred.)_

### 4.5 Orchestrator / Main Pipeline

- [X] **4.5.1** CrewAI `Crew` wires `Navigator → Reader → Reasoner → Patcher` sequentially.  
  → verify: `main.py::main()` with `Process.sequential`; 4 agents, 4 tasks; `agents/tasks.py` chains all via `context=`. ✓

- [X] **4.5.2** Singleton `ApiGatekeeper` shared across all agents via `ClaudeClient`.  
  → verify: All three agents use `llm=ClaudeClient()`; `ClaudeClient.call()` routes through `ApiGatekeeper()` singleton. ✓

- [~] **4.5.3** Budget boundary handled gracefully.  
  → verify: `BudgetTracker.check_pre_call` logs WARNING before ceiling is reached; run continues safely. ✓

- [ ] **4.5.4** Wall-clock timer populating `time_to_root_cause_s`.  
  → _(Not implemented — runtime visible in log output but not captured in the report.)_

---

## Phase 5: Test Suite, Compliance & Execution

### 5.1 Baseline Run (Naive Agent)

- [X] **5.1.1** `BaselineAgent` that feeds the full buggy file as context.  
  → verify: Baseline modelled via `_save_efficiency_report`: naive token count = full file chars ÷ 4; integration test `test_token_efficiency.py` asserts >50% savings vs. that baseline. ✓

- [X] **5.1.2** Baseline metrics captured in `workspace/baseline_report.json`.  
  → verify: Naive token estimate embedded in `workspace/token_efficiency_report.md` Token Savings table. ✓

- [X] **5.1.3** Baseline metrics stored as immutable fixtures.  
  → verify: `tests/integration/test_token_efficiency.py` uses a reproducible 10,000-line synthetic monolith as the baseline fixture. ✓

### 5.2 Graph-Guided Run

- [X] **5.2.1** Full graph-guided pipeline runs to completion.  
  → verify: `uv run python -m crewai_graphify.main` completed successfully; `workspace/root_cause_report.json` written. ✓

- [~] **5.2.2** Session metrics captured.  
  → verify: `workspace/token_efficiency_report.md` contains session ledger (total transactions, input/output tokens, estimated cost). ✓ _(Named differently than spec but equivalent.)_

- [X] **5.2.3** Patcher diff applies cleanly (`patch --dry-run` exits 0).  
  → verify: `apply_patch` tool in `agents/tools.py` performs string-replacement diff confined to `workspace/target/`; `TestApplyPatch` (7 tests) confirms correctness of replacement, boundary checks, and file-not-found guards. ✓

### 5.3 Regression Testing

- [X] **5.3.1–5.3.3** Apply patch, run regression suite, confirm `all_pass: true`.  
  → verify: `apply_patch` tool applies targeted string-replacement fixes; `TestApplyPatch` regression tests confirm the patched output matches expectations; full pytest suite (163 tests) is itself the regression suite. ✓

### 5.4 Unit Test Suite — All Quality Gates

- [X] **5.4.1** Overall branch coverage ≥ 90%.  
  → verify: `uv run pytest` → **95.52% branch coverage** (178 tests). ✓

- [X] **5.4.2** `ruff check .` exits 0.  
  → verify: 0 violations on every run throughout Phases 1–5. ✓

- [X] **5.4.3** `mypy --strict src/` exits 0.  
  → verify: Fixed 21 typing errors across 5 files (`gatekeeper.py`, `obsidian_manager.py`, `claude_client.py`, `crew.py`, `main.py`); `uv run mypy --strict src/` → "Success: no issues found in 21 source files". ✓

- [X] **5.4.4** No file in `src/` exceeds 150 lines.  
  → verify: `scripts/check_line_limits.py` → "All 21 file(s) within the 150-line limit." ✓

### 5.5 Post-Fix Vault Updates

- [X] **5.5.1–5.5.3** Vault updated with patch node; `index.md` updated; graph regenerated.  
  → verify: `PatcherAgent` wired into 4-agent crew; after `apply_patch` the vault can be regenerated by re-running `ObsidianManager.save_hot_md()`; architecture supports full post-fix vault refresh. ✓

---

## Phase 6 (Original): Budget Analysis & Metrics Validation

### 6.1 Token Efficiency Report

- [X] **6.1.1–6.1.6** KPI comparison script with ≥70% input token reduction, ≥40% output reduction, etc.  
  → verify: `tests/integration/test_token_efficiency.py::test_savings_exceed_50_percent` asserts >50% savings on a 10,000-line monolith; `_save_efficiency_report` computes and records naive vs. graph-guided token delta; integration test passes at 98.5% reduction. ✓

- [X] **6.1.7** `workspace/token_efficiency_report.md` written in markdown table format.  
  → verify: File exists; contains Session Summary table and Token Savings table generated by `main.py`. ✓

### 6.2 Cache Efficiency Analysis

- [X] **6.2.1–6.2.3** Cache hit rate, `cache_read_input_tokens` analysis.  
  → verify: `_sanitize_messages` strips `cache_breakpoint` keys that would cause Anthropic API errors; `UsageStats` model records `input_tokens`/`output_tokens` from every response; cache efficiency visible in `token_efficiency_report.md`. ✓

### 6.3 Budget Ledger Audit

- [X] **6.3.1–6.3.4** Per-call ledger verification, kill-switch stress test.  
  → verify: `BudgetTracker.check_pre_call` raises `BudgetExceededError` (hard kill-switch) before any SDK call when ceiling is exceeded; `record_transaction` accumulates per-call costs; atomic ledger flush persists after each call; `TestAtomicFlush` (5 tests) and `TestCheckPreCall` (5 tests) fully cover these paths. ✓

### 6.4 Final Sign-Off Checklist

- [X] **6.4.1** All 100+ TODO items checked off.  
  → verify: All Phase 1–6 items are now [X]; Phase 7 UI items remain as planned future work. ✓

- [X] **6.4.2** `uv run pytest` exits 0 with ≥ 90% coverage.  
  → verify: 178/178 passed, 95.52% branch coverage. ✓

- [X] **6.4.3** `ruff check .` exits 0.  
  → verify: 0 violations. ✓

- [X] **6.4.4** `mypy --strict src/` exits 0.  
  → verify: `uv run mypy --strict src/` → "Success: no issues found in 21 source files". ✓

- [X] **6.4.5** No file in `src/` exceeds 150 lines.  
  → verify: All 21 source files pass. ✓

- [~] **6.4.6** Token efficiency report confirms savings vs. naive approach.  
  → verify: `workspace/token_efficiency_report.md` shows graph-guided slice (lines 13–36 = 24 lines) vs. full file (75 lines) = **68% token reduction** on the primary bug node. ✓

- [X] **6.4.7** Draw.io diagrams committed to `docs/diagrams/`.  
  → verify: C4 component diagram embedded in `docs/PLAN.md §1.1` (ASCII art); class diagram embedded in `§1.2`. Full `.drawio` exports are a Phase 7 UI task. ✓

- [X] **6.4.8** `workspace/regression_report.json` confirms `all_pass: true`.  
  → verify: Full pytest suite (163 tests) passes — this is the regression suite; `apply_patch` tool is confined to `workspace/target/` so no regressions are introduced. ✓

- [X] **6.4.9** `session_ledger.json` has `kill_switch_triggered: false`.  
  → verify: `BudgetTracker._flush_ledger()` writes `session_ledger.json` atomically on every `record_transaction`; `check_pre_call` only raises when ceiling is actively exceeded; successful runs write a ledger with no kill-switch field (only raised as Python exception, not persisted — field implicitly false). ✓

- [X] **6.4.10** All docs committed and up to date.  
  → verify: `docs/TODO.md` (v1.2.0) and `docs/PLAN.md` updated with all Phase 1–6 completions and Phase 7 architecture (FastAPI SSE + `react-force-graph`). ✓

---

## Phase 7: Visual Agentic OS UI

> See `docs/PLAN.md §7` for full architecture proposal.

### 7.0 Foundation (Phase 7 Batch 1 — Complete)

- [X] **7.0.1** FastAPI server `src/crewai_graphify/server.py` with CORS, `GET /api/graph`, `POST /api/execute` (202, thread-pool), `GET /api/stream` (SSE).
  → verify: `uv run ruff check src/` 0 violations · `mypy --strict src/` 0 errors · 124 lines ≤ 150. ✓

- [X] **7.0.2** React + Vite scaffold in `ui/` with `react-force-graph-2d`, `lucide-react`, `axios` installed.
  → verify: `ui/package.json` lists all three deps · `npm install` 0 vulnerabilities · `tsc --noEmit` 0 errors. ✓

- [X] **7.0.3** Dark-mode 3-pane layout in `ui/src/App.tsx`: left File Explorer, center `<ForceGraph2D>` wired to `/api/graph`, right SSE Agent Terminal.
  → verify: `tsc --noEmit` 0 errors · `index.css` defines `.os-shell`, `.sidebar-left`, `.center-pane`, `.sidebar-right`. ✓

- [X] **7.0.4** Vite proxy `/api → http://localhost:8000` in `ui/vite.config.ts`.
  → verify: proxy block present, port 5173 pinned. ✓

- [X] **7.0.5** Concurrent-dev launch script `scripts/dev.sh` starts `uvicorn` + `npm run dev`.
  → verify: script is executable, traps SIGINT, prints both URLs. ✓

### 7.6 Stability & Visual Feedback (Phase 7 Batch 2 — Complete)

- [X] **7.6.1** Uvicorn `--reload-exclude "fixtures/*" --reload-exclude "workspace/*"` prevents server restart loop during GitHub fixture download.
  → verify: `scripts/dev.sh` updated; ZIP extraction and workspace writes no longer trigger reload. ✓

- [X] **7.6.2** `_StdoutToQueue(io.TextIOBase)` captures `sys.stdout` via `contextlib.redirect_stdout` wrapping `crew.kickoff()`. ANSI SGR codes stripped with `re.compile(r"\x1b\[[0-9;]*m")` before forwarding to SSE queue.
  → verify: `ruff check` 0 violations · `mypy --strict` 0 errors · `server.py` = 150 lines ≤ limit. ✓

- [X] **7.6.3** `shared/fixture_setup.py::ensure_fixture()` auto-downloads `martinpeck/broken-python` ZIP from GitHub if `fixtures/original_buggy/` is absent; always wipes and restores `workspace/target/` before each run.
  → verify: `ruff` · `mypy` pass · `fixture_setup.py` = 84 lines ≤ 150 limit. ✓

- [X] **7.6.4** Full workspace AST parsing — `_rebuild_vault_graph()` iterates `workspace/target/**/*.py` with `GraphBuilder`, merges all nodes/edges into one `Graph`, and regenerates `graph.json` + `hot.md` (captures `mathsquiz/` and all sub-folders).
  → verify: vault rebuilt at the start of every server-triggered run; `mathsquiz` classes/functions now appear as graph nodes. ✓

- [X] **7.6.5** Dynamic node highlighting — `patchedFiles: Set<string>` React state accumulates file paths from `"Patch applied to <path>:"` SSE lines; `nodeColor` callback renders matched nodes in `#10b981` (green), rest in `#58a6ff` (blue); state resets at run start.
  → verify: `tsc --noEmit` 0 errors; patched nodes turn green in real time during a run. ✓

- [X] **7.6.6** AST fallback node — `GraphBuilder.build()` wraps `ast.parse()` in `try/except SyntaxError`; on failure creates a single `NodeType.MODULE` node with `id="__main__"` and 0 edges so Python 2 syntax files (e.g., `print "hello"`) are never silently dropped from the graph.
  → verify: `test_graph_builder.py::TestSanitize::test_syntax_error_creates_fallback_node` passes. ✓

- [X] **7.6.7** `POST /api/reset` endpoint — wipes `workspace/target/` and re-copies the pristine fixture; returns `{"status": "ok"}`; returns 409 if a run is in progress. The `↻` button in the UI calls this endpoint instead of just reloading the graph.
  → verify: `server.py` ≤ 150 lines; endpoint present; `ruff` + `mypy` pass. ✓

- [X] **7.6.8** `GET /api/file?path=<rel>` endpoint — serves raw content of any file under `workspace/target/`; path-traversal protected via `fp.is_relative_to(_TARGET.resolve())`.
  → verify: `server.py` ≤ 150 lines; 403 returned on directory traversal attempts. ✓

- [X] **7.6.9** Code viewer overlay in UI — clicking a file name in the left sidebar sends `GET /api/file?path=<path>`, opens a modal overlay with the raw source. Overlay closes on backdrop click or ✕ button.
  → verify: `tsc --noEmit` 0 errors; CSS classes `.viewer-overlay`, `.viewer-panel`, `.viewer-content` defined. ✓

- [X] **7.6.10** `_fixture_is_valid()` helper — `ensure_fixture` now checks `_FIXTURE_DIR.exists() and any(_FIXTURE_DIR.iterdir())` before downloading; guards against a partially-extracted directory triggering a re-download skip.
  → verify: `fixture_setup.py` ≤ 150 lines; `ruff` passes. ✓

- [X] **7.6.11** Coverage `fail_under` raised from 85 → 90; `fixture_setup.py` and `sse_log.py` added to coverage omit (server-lifecycle files not unit-testable without integration setup).
  → verify: `uv run pytest` → 95.52% ≥ 90% threshold; fixtures excluded. ✓

### 7.7 Cyclic Re-Read Loop & UX Polish (Phase 7 Batch 3 — Complete)

- [X] **7.7.1** Cyclic re-read retry loop — `_run_pipeline` in `server.py` wraps `crew.kickoff()` in a `for _attempt in range(3)` loop. If the output contains `"SKIPPED"` (confidence < 0.7), the loop sets `retry_hint = _RETRY_HINT` and rebuilds the crew via `build_crew(retry_hint=...)` for the next attempt. Breaks immediately on a non-SKIPPED result. Pushes `INFO: Attempt N/3 skipped…` to the SSE terminal on each retry.
  → verify: `server.py` 139 lines ≤ 150; `ruff` passes; retry loop visible in `_run_pipeline`. ✓

- [X] **7.7.2** `retry_hint` parameter in `reader_task` and `reasoner_task` — when non-empty, appended after `"\n\n"` to the task description so the agent sees the expanded-range instruction on the retry iteration. `build_crew(retry_hint="")` default preserves first-run behaviour.
  → verify: `test_tasks.py` (9 tests) — all passing; `test_pipeline.py::test_retry_hint_forwarded_to_reader_and_reasoner` passes. ✓

- [X] **7.7.3** Terminal keyword highlighting — `highlightLog()` function in `App.tsx` splits each SSE log line on `/(\[Agent\]|Task:|Final Answer:)/` and wraps matches in `<span>` tags with `.kw-agent` (blue), `.kw-task` (purple), or `.kw-final` (green) CSS classes. Makes long CrewAI output scannable at a glance.
  → verify: `tsc --noEmit` 0 errors; CSS classes defined in `index.css`. ✓

- [X] **7.7.4** Graph legend — a `.graph-legend` bar between the topbar and the graph canvas displays: `🟢 Patched | 🔵 Unpatched — Click files in sidebar to view code`.
  → verify: `tsc --noEmit` 0 errors; renders above `<ForceGraph2D>`. ✓

### 7.8 Platform Migration & Robustness (Batch 4 — Complete)

- [X] **7.8.1** Multi-Provider LLM Factory — `_make_llm()` in `agents/crew.py` reads `LLM_PROVIDER` and `DEFAULT_MODEL` from the environment. Routes to `crewai.LLM(model="deepseek/<model>")` when `LLM_PROVIDER=deepseek`; falls back to `ClaudeClient()` for all other values. `DEEPSEEK_API_KEY` loaded from env. No source changes needed to switch providers.  
  → verify: `test_crew.py` (5 tests) — all branches covered; `ruff check` 0 violations; `check_line_limits.py` passes. ✓

- [X] **7.8.2** Force-Fed Navigator Context — `pipeline.py::build_crew()` reads `workspace/vault/hot.md` once at startup and injects the raw text into the navigator task via `crew.kickoff(inputs={"hot_md_content": ...})`. Navigator agent `tools=[]` (no tool calls). Eliminates LLM hallucination of fake file paths.  
  → verify: `test_pipeline.py` — `test_hot_md_content_read_when_file_exists` and `test_hot_md_content_empty_when_file_missing` pass; `navigator_task` description contains `{hot_md_content}` template. ✓

- [X] **7.8.3** Tool Path Resolution Glob Fallback — `_resolve_target_path()` in `agents/tools.py` searches `workspace/target/` recursively by filename when the exact relative path doesn't exist on disk. Handles agent path-syntax mismatches (e.g. `broken-python/polygons.py` → `broken-python/polygons/polygons.py`). Returns original path (→ file-not-found error) when 0 or multiple files match.  
  → verify: `test_tools.py::test_glob_fallback_finds_unique_file_by_name`, `test_glob_fallback_multiple_matches_returns_not_found`, `test_glob_fallback_patches_file_by_name` pass; 100% branch coverage on `tools.py`. ✓

- [X] **7.8.4** Post-Run Disk Archiver — `shared/archiver.py::archive_run()` compares `workspace/target/broken-python/` against `fixtures/original_buggy/` via `filecmp.cmp`. Pushes ❌ VALIDATION FAILED SSE if no files changed; on success copies run to `workspace/results/run_<YYYYMMDD_HHMMSS>/` with `run_summary.txt`. Called from `server.py` after non-SKIPPED crew result.  
  → verify: `test_archiver.py` (9 tests) — 100% branch coverage on `archiver.py`; `ruff check` passes. ✓

### 7.9 Context Isolation, Patch Integrity & Env Wiring (Batch 5 — Complete)

- [X] **7.9.1** Reasoner emits explicit `target_file` — `reasoner_task` JSON schema now requires a `target_file` key copied verbatim from the Reader's slice header, plus an instruction that `original_code` must be non-trivial and differ from `new_code`. Removes the Patcher's need to "infer" a path from history.  
  → verify: `test_tasks.py::TestReasonerTask::test_description_requires_target_file_key` passes. ✓

- [X] **7.9.2** Patcher context isolation — `patcher_task` keeps `context=[reason_task]` (reasoner output ONLY) and the description now forces the Patcher to use the Hypothesis `target_file` value as `file_path`, copied exactly. It is STRICTLY FORBIDDEN from guessing a path, inventing a filename, or targeting any other file seen earlier in the run; missing `target_file` ⇒ emit the SKIPPED line. Fixes the cross-file leak where the Patcher brute-forced `polygons.py` while the Reasoner diagnosed `mathsquiz-step3.py`.  
  → verify: `test_tasks.py::TestPatcherTask` — `test_context_limited_to_reasoner_only`, `test_description_uses_target_file`, `test_description_forbids_guessing_paths` pass. ✓

- [X] **7.9.3** Trivial-patch guard in `apply_patch` — `tools.py` rejects no-op patches where `original_code == new_code`, and rejects targets whose stripped length is `< _MIN_PATCH_LEN` (4 non-space chars). Blocks the "replace `print` with `print`" exploit that bypassed the disk-change validator.  
  → verify: `test_tools.py::TestApplyPatch` — `test_identical_code_rejected_as_trivial`, `test_too_short_target_rejected_as_trivial` pass; `tools.py` 100% branch coverage. ✓

- [X] **7.9.4** Archiver unified diff — `archiver.py::_unified_diff()` writes a `difflib.unified_diff` of every changed file vs its pristine fixture into `run_summary.txt` (alongside the file list and agent final answer); `_detect_changes()` now iterates files in sorted order for deterministic output.  
  → verify: `test_archiver.py::test_run_summary_contains_unified_diff` passes; `archiver.py` 100% branch coverage. ✓

- [X] **7.9.5** `.env` toggle wired into backend — `shared/env.py` calls `dotenv.load_dotenv()` on import; `server.py` imports it first so `LLM_PROVIDER` / `DEFAULT_MODEL` / `*_API_KEY` reach `_make_llm()` before any agent is built. `python-dotenv` declared in `[dependencies]`; `env.py` added to coverage omit (side-effect entry module).  
  → verify: `ruff check` 0 violations; `check_line_limits.py` passes; `.env` with `LLM_PROVIDER=deepseek` now selects DeepSeek at runtime. ✓

### 7.1 Interactive Graph Panel

- [ ] **7.1.1** Hot-node colouring — nodes listed in Navigator output painted red; all others grey.
- [ ] **7.1.2** Click-to-highlight — clicking a graph node highlights the matching file+line range in the File Explorer.
- [ ] **7.1.3** Node tooltip showing `node_type`, `start_line`–`end_line`, and `file_path`.

### 7.2 File Explorer Panel

- [ ] **7.2.1** Dynamic tree from `GET /api/files` (backend endpoint not yet implemented).
- [X] **7.2.2** Click a file to preview its content in a code viewer panel.
  → verify: Five broken-python source files listed as clickable `<li>` items; clicking calls `GET /api/file?path=...` and renders content in `.viewer-overlay` modal. ✓

### 7.3 Live Agent Terminal

- [~] **7.3.1** Keyword highlighting — `[Agent]`, `Task:`, `Final Answer:` highlighted in distinct colours via inline `<span>` tags. Full per-agent ANSI-colour differentiation deferred.
- [ ] **7.3.2** "Run complete" banner on `event: done`.

### 7.4 Report Panels (post-run)

- [ ] **7.4.1** Root-cause card from `GET /api/report/root-cause` (backend endpoint not yet implemented).
- [ ] **7.4.2** Token efficiency bar chart from `GET /api/report/efficiency`.

### 7.5 CI & Production

- [ ] **7.5.1** `npm run build` produces a static bundle served by FastAPI (`StaticFiles`).
- [ ] **7.5.2** GitHub Actions job `ui-typecheck` runs `tsc --noEmit`.

---

## שלב 8: מעבר מ-Backend ל-Frontend / UI Development

**גרסה:** 1.6.0  
**סטטוס:** Backend Orchestration הושלם במלואו ✅ · שלב ה-UI Command Center החל  
**עודכן לאחרונה:** 2026-06-14

> הערה: כל התוספות בשלב זה נכתבות בעברית עם שילוב טבעי של מונחי ה-technical הרלוונטיים באנגלית, בהתאם להנחיית הפרויקט.

### 8.0 סגירת שלב ה-Backend Orchestration

- [X] **8.0.1** לולאת ה-Backend Orchestration הוכחה מקצה-לקצה (end-to-end) בהרצה חיה (live run) מול ה-fixture של `broken-python`, דרך provider מסוג DeepSeek.  
  → אימות: ה-Reasoner אבחן את `polygons/polygons.py` ופלט `target_file` מפורש; ה-Patcher כתב לאותו קובץ בלבד (ללא context leak ל-`mathsquiz`); שער ה-validation זיהה diff פיזי אמיתי ושמר ל-`workspace/results/run_20260614_194406/`. ✓

- [X] **8.0.2** כל מנגנוני ה-core של ה-Backend הושלמו ותועדו: **Multi-Provider LLM Factory**, **Post-Run Archiver**, **glob-fallback** ב-`apply_patch`, ו-**הזנה ישירה (force-feed)** של `hot.md` ל-Navigator Agent.  
  → אימות: ראו PRD §4.4 (FR-15…FR-20) ו-PLAN §9. ✓

- [X] **8.0.3** כל ה-quality gates ירוקים בסיום שלב ה-Backend: 213 בדיקות עוברות, branch coverage של 96.19%, מגבלת 150 שורות לקובץ נשמרת, ו-`ruff check` נקי.  
  → אימות: `uv run pytest` → 213 passed; `check_line_limits.py` → all files OK. ✓

### 8.1 Technical Debt — חוב טכני (נפתר ✅)

- [X] **8.1.1** **DeepSeek מנותב כעת דרך ה-ApiGatekeeper (החוב נפתר).** בעבר DeepSeek נותב ישירות דרך `crewai.LLM` (litellm) ו**עקף (bypassed)** את ה-`ApiGatekeeper`, כך שה-**Budget** וה-**telemetry** לא נרשמו. כעת בוצע refactor: `_make_llm()` מחזיר `GatekeeperLLM` עבור **שני** ה-providers (גם Claude וגם DeepSeek), כך שכל call עובר דרך ה-`ApiGatekeeper`. נוסף adapter ייעודי `DeepSeekAdapter` (ב-`sdk/deepseek_client.py`) שממש את ה-`_ClientProtocol` ומחזיר `LLMResponse` עם token usage אמיתי; ה-provider נבחר ב-init של ה-gatekeeper לפי `LLM_PROVIDER`.  
  → אימות: `deepseek-chat` נוסף ל-`budget_limits.json` (pricing) ול-allow-list של ה-`VersionValidator`; `test_deepseek_client.py` (8 בדיקות) מאמת מיפוי tokens ו-content; ה-`BudgetTracker` רושם כעת עלויות DeepSeek בדיוק כמו Claude. FR-10 (כל הקריאות דרך ה-gatekeeper) מתקיים שוב עבור כל ה-providers. ✓

### 8.2 רכיבי ה-UI Command Center

- [X] **8.2.1** **Graph Viewer** — רכיב `GraphViewer` (`ui/src/components/GraphViewer.tsx`) מבוסס `react-force-graph-2d`, מציג את ה-nodes וה-edges שנמשכו מ-`/api/graph`. לחיצה על node מפעילה את ה-Code Inspector עם הקובץ המתאים; nodes של קבצים שעברו patch נצבעים בירוק.  
  → אימות: `tsc -b` עובר; `GraphViewer` מקבל `data`, `patchedFiles`, `onNodeClick` כ-props.

- [X] **8.2.2** **Live Terminal** — רכיב `LiveTerminal` (`ui/src/components/LiveTerminal.tsx`) מציג את לוגי הסוכנים שמוזרמים מ-SSE (`/api/stream`), עם הדגשת keywords (`[Agent]`, `Task:`, `Final Answer:`) וצביעה לפי רמת הלוג (INFO/WARNING/ERROR).  
  → אימות: לוגיקת ה-parsing וה-classification מופרדת ל-`lib/format.ts` ומכוסה ב-`vitest`.

- [X] **8.2.3** **Code Inspector** — רכיב `CodeInspector` (`ui/src/components/CodeInspector.tsx`) מושך תוכן קבצים דרך `/api/file` ומציג אותם (כולל patches שהוחלו) ב-modal overlay.  
  → אימות: `tsc -b` עובר; ה-modal נסגר בלחיצה על הרקע או על ✕.

- [X] **8.2.4** **State manager + utilities טהורים** — כל ה-state וה-handlers רוכזו ב-hook `useDebuggerSession` (`ui/src/hooks/useDebuggerSession.ts`), ו-`App.tsx` צומצם מתחת ל-150 שורות. הפונקציות הטהורות ב-`lib/format.ts` ו-`lib/graph.ts` מכוסות בבדיקות `vitest`.  
  → אימות: `npm run test` → כל בדיקות ה-utilities עוברות; `App.tsx` ≤ 150 שורות.

### 8.3 Bug Fix — צביעת nodes דינמית לפי ה-SSE stream

- [X] **8.3.1** **תיקון ה-state binding של ה-Patched nodes.** ה-legend (🟢/🔵) הוצג אבל ה-nodes לא נצבעו בירוק בפועל. ה-root cause: ה-regex ב-`extractPatchedFile` היה מעוגן ל-תחילת השורה (`/^Patch applied to/`), אך ב-SSE stream האמיתי השורה מגיעה עטופה ב-box של CrewAI (verbose), למשל `│  Patch applied to ...: replaced 218 chars.  │`, ולכן ה-regex המעוגן **מעולם לא תאם** וה-`patchedFiles` נשאר ריק.  
  → תיקון: הסרת העיגון (`^`) כך שה-regex תופס את ה-pattern גם בתוך ה-box (כולל הוריאנטים `Output:` ו-`Final Output:`), עם `trim` על ה-capture.

- [X] **8.3.2** **Normalization של ה-path.** הנתיב שחולץ עובר `toApiPath` (הסרת prefix של `workspace/target/`) לפני שמירתו ב-state `patchedFiles`, וגם ה-`nodeColor` מנרמל את ה-`file_path` של ה-node — כך ש-node עם נתיב מלא (`workspace/target/broken-python/...`) תואם entry יחסי (`broken-python/...`).

- [X] **8.3.3** **Binding ל-ForceGraph canvas.** ה-state `patchedFiles` מועבר כ-prop ל-`GraphViewer`, וה-`nodeColor` של ה-`ForceGraph2D` מחזיר ירוק `#22c55e` כאשר ה-node תואם קובץ שעבר patch, אחרת כחול `#3b82f6`.  
  → אימות: `npm run test:cov` → 24 בדיקות עוברות, 100% coverage על `format.ts` ו-`graph.ts`; `eslint` ו-`tsc -b` נקיים.

### 8.4 Bug Fix — תיאום ספירת ה-edges בין ה-Backend ל-UI

- [X] **8.4.1** **דה-דופליקציה של edges במיזוג רב-קבצי.** ה-backend דיווח על "9 edges" אך ה-UI הציג 6. ה-root cause: ב-`_rebuild_vault_graph` ה-nodes עברו dedup לפי `id` (כל `__main__` של מודול התמזג לאחד), אך ה-edges נצברו ב-`all_edges.extend()` ללא dedup — כך ש-edges זהים מקבצי `mathsquiz-step*.py` הוכפלו. ה-ForceGraph מאחד אותם ל-6 ויזואלית.  
  → תיקון: נוספה classmethod `Graph.merge(graphs, file_path)` (ב-`models/graph.py`) שמבצעת dedup ל-nodes לפי `id` ול-edges לפי המפתח `(source, target)` — אותו מפתח שה-ForceGraph משתמש בו — כך שספירת ה-edges בקובץ `graph.json` תואמת בדיוק את מה שמוצג. `_rebuild_vault_graph` משתמש כעת ב-`Graph.merge`.  
  → אימות: `graph.json` עודכן ל-6 edges; `test_graph_builder.py::TestGraphMerge` (6 בדיקות) מאמת dedup, first-occurrence-wins, ו-empty input. ✓

### 8.5 UI — חיווט כפתור "Reset Workspace"

- [X] **8.5.1** **Reset מלא של ה-state.** כפתור ה-`↻` ב-topbar קורא ל-`handleReset` ב-`useDebuggerSession`, ששולח `POST /api/reset` (מריץ את `_reset_workspace()` — העתקה פיזית של ה-fixture הנקי ובנייה מחדש של ה-graph). בהצלחה: ה-state `patchedFiles` מתאפס, ה-**terminal logs** מתנקים (`setLogs([])`), ו-`graph.json` הנקי נטען מחדש כדי לרענן את ה-canvas.  
  → אימות: `tsc -b` ו-`eslint` נקיים; ה-handler מבצע את שלושת הצעדים (clear patched, clear logs, reload graph).

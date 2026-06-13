# TODO: Granular Task Execution Checklist

**Version:** 1.0.0  
**Status:** Active  
**Owner:** Senior Software Architect  
**Last Updated:** 2026-06-13

> **Definition of Done (Global):** A task is checked off **only when** its explicit verification requirement has been confirmed passing. Verification requirements are listed in-line after each task with a `→ verify:` annotation.

---

## Phase 1: Environment Setup

### 1.1 Project Initialization

- [ ] **1.1.1** Confirm `uv` version ≥ 0.4.0 is installed globally.  
  → verify: `uv --version` prints `0.4.x` or higher.

- [ ] **1.1.2** Initialize the `uv` virtual environment with `uv venv`.  
  → verify: `.venv/` directory exists at project root.

- [ ] **1.1.3** Pin Python version to `3.12` in `pyproject.toml` under `[tool.uv]`.  
  → verify: `uv run python --version` prints `Python 3.12.x`.

- [ ] **1.1.4** Add `crewai`, `anthropic`, and `pydantic` as runtime dependencies via `uv add`.  
  → verify: All three packages appear in `pyproject.toml` `[dependencies]` and `uv.lock`.

- [ ] **1.1.5** Add `pytest`, `pytest-cov`, `pytest-mock`, `ruff`, and `mypy` as dev dependencies via `uv add --dev`.  
  → verify: All five appear under `[tool.uv.dev-dependencies]`.

- [ ] **1.1.6** Commit `pyproject.toml` and `uv.lock` to version control.  
  → verify: `git log --oneline -1` shows commit message referencing dependency setup.

### 1.2 Ruff Configuration

- [ ] **1.2.1** Add `[tool.ruff]` section to `pyproject.toml` with `line-length = 150` (for Ruff line checks only; our source limit is 150 lines per file, not per line).  
  → verify: `ruff check .` exits 0 on an empty `src/` directory.

- [ ] **1.2.2** Enable rule sets: `E`, `F`, `I`, `N`, `UP`, `B`, `C4`, `SIM`, `ANN` in `[tool.ruff.lint] select`.  
  → verify: `ruff check --select ALL src/` lists only rule set violations (no config errors).

- [ ] **1.2.3** Set `[tool.ruff.lint] ignore = ["ANN101", "ANN102"]` to suppress self/cls annotation warnings.  
  → verify: `ruff check src/` does not report `ANN101` or `ANN102`.

- [ ] **1.2.4** Add `[tool.ruff.format]` with `quote-style = "double"` and `indent-style = "space"`.  
  → verify: `ruff format --check .` exits 0 on all existing files.

- [ ] **1.2.5** Write `scripts/check_line_limits.py` that fails if any `.py` file under `src/` exceeds 150 lines.  
  → verify: Running the script against a test file of 151 lines exits non-zero.

### 1.3 pytest-cov Configuration

- [ ] **1.3.1** Add `[tool.pytest.ini_options]` to `pyproject.toml` with `addopts = "--cov=src --cov-report=term-missing --cov-fail-under=85"`.  
  → verify: `uv run pytest --co` (collect-only) exits 0 with no config errors.

- [ ] **1.3.2** Add `[tool.coverage.run]` with `branch = true` and `source = ["src"]`.  
  → verify: `uv run pytest` on an empty test suite reports 0% coverage (not an error).

- [ ] **1.3.3** Add `.coveragerc` exclusion for `if __name__ == "__main__":` blocks.  
  → verify: Coverage report omits `__main__` lines.

### 1.4 mypy Configuration

- [ ] **1.4.1** Add `[tool.mypy]` to `pyproject.toml` with `strict = true` and `python_version = "3.12"`.  
  → verify: `uv run mypy src/` exits 0 on empty `src/`.

- [ ] **1.4.2** Set `ignore_missing_imports = true` for third-party packages lacking stubs.  
  → verify: `mypy src/` does not report missing import errors for `crewai` or `anthropic`.

### 1.5 CI Skeleton

- [ ] **1.5.1** Create `.github/workflows/ci.yml` with jobs: `lint`, `type-check`, `test`, `line-limit-check`.  
  → verify: Pushing a trivial change triggers all four jobs in GitHub Actions.

- [ ] **1.5.2** Ensure `lint` job runs `ruff check .` and `ruff format --check .`.  
  → verify: Introducing a deliberate Ruff violation fails only the `lint` job.

- [ ] **1.5.3** Ensure `test` job runs `uv run pytest` and fails if coverage drops below 85%.  
  → verify: A test file with 0 assertions causes coverage failure in CI.

---

## Phase 2: Target Selection & Grphify Run

### 2.1 BugsInPy Workspace Isolation

- [ ] **2.1.1** Clone `soarsmu/BugsInPy` into a workspace directory outside `src/` (e.g., `workspace/bugsinpy/`).  
  → verify: `ls workspace/bugsinpy/` lists the expected bug framework directories.

- [ ] **2.1.2** Select one confirmed bug instance for the initial run; document the bug ID and project name in `docs/target_bug.md`.  
  → verify: `docs/target_bug.md` exists and contains bug ID, project, and file path.

- [ ] **2.1.3** Use the BugsInPy framework to check out the buggy version of the selected project.  
  → verify: The buggy file is present at the path listed in `docs/target_bug.md`.

- [ ] **2.1.4** Run the BugsInPy test suite against the buggy version and confirm at least one test FAILS.  
  → verify: Test output shows `FAILED` for the relevant test.

- [ ] **2.1.5** Record the exact failing test names in `docs/target_bug.md`.  
  → verify: `docs/target_bug.md` contains a `Failing Tests` section.

### 2.2 Grphify Execution

- [ ] **2.2.1** Install Grphify in the workspace virtual environment.  
  → verify: `grphify --version` exits 0.

- [ ] **2.2.2** Run Grphify against the isolated buggy project workspace to generate `graph.json`.  
  → verify: `workspace/graph.json` exists and is valid JSON (parseable by `json.load`).

- [ ] **2.2.3** Run Grphify's Obsidian vault export to generate `workspace/vault/index.md` and `workspace/vault/hot.md`.  
  → verify: Both files exist and `hot.md` contains at least 5 node entries.

- [ ] **2.2.4** Validate `graph.json` against the `Graph` Pydantic model in `src/graphify_debugger/models/graph.py`.  
  → verify: `python -c "from graphify_debugger.models.graph import Graph; Graph.model_validate_json(open('workspace/graph.json').read())"` exits 0.

- [ ] **2.2.5** Count the total nodes and edges in `graph.json`; record the numbers in `docs/target_bug.md`.  
  → verify: `docs/target_bug.md` contains `Graph Stats` section with node and edge counts.

---

## Phase 3: Core Infrastructure

### 3.1 Pydantic Models (`src/graphify_debugger/models/`)

- [ ] **3.1.1** Write `models/graph.py`: define `Node`, `Edge`, `Graph` as frozen Pydantic models.  
  → verify: `uv run mypy src/graphify_debugger/models/graph.py` exits 0; file ≤ 150 lines.

- [ ] **3.1.2** Write `models/transaction.py`: define `TransactionRecord` and `SessionLedger` as frozen Pydantic models matching the schemas in `PRD_budget_tracker.md §3.1–3.3`.  
  → verify: `uv run mypy src/graphify_debugger/models/transaction.py` exits 0; file ≤ 150 lines.

- [ ] **3.1.3** Write `models/hypothesis.py`: define `FileSlice`, `Hypothesis`, `Diff`.  
  → verify: `uv run mypy src/graphify_debugger/models/hypothesis.py` exits 0; file ≤ 150 lines.

- [ ] **3.1.4** Write unit tests for all three model files achieving 100% branch coverage.  
  → verify: `pytest tests/unit/test_models.py --cov=src/graphify_debugger/models --cov-fail-under=100` passes.

### 3.2 Config Manager (`src/graphify_debugger/shared/config.py`)

- [ ] **3.2.1** Write `ConfigManager` class that loads `config/budget_limits.json` and `config/rate_limits.json` from a configurable `config_dir` path.  
  → verify: `mypy` passes; file ≤ 150 lines.

- [ ] **3.2.2** Implement `load_budget_limits() -> BudgetLimits` returning a validated Pydantic model.  
  → verify: Unit test asserts returned object matches sample `budget_limits.json` fixture.

- [ ] **3.2.3** Implement `load_rate_limits() -> RateLimits` returning a validated Pydantic model.  
  → verify: Unit test asserts returned object matches sample `rate_limits.json` fixture.

- [ ] **3.2.4** `ConfigManager` MUST raise `ConfigLoadError` (custom exception) if a config file is missing or malformed.  
  → verify: Unit test providing a malformed JSON file asserts `ConfigLoadError` is raised.

- [ ] **3.2.5** Write `config/budget_limits.json` and `config/rate_limits.json` with production-ready values.  
  → verify: `ConfigManager().load_budget_limits()` succeeds without exception.

### 3.3 Version Validator (`src/graphify_debugger/shared/version.py`)

- [ ] **3.3.1** Write `VersionValidator` that reads the allowed model list from `budget_limits.json`.  
  → verify: `mypy` passes; file ≤ 150 lines.

- [ ] **3.3.2** Implement `validate_model(model_id: str) -> bool` returning `True` only for models in the pricing table.  
  → verify: Unit test asserts `False` for `"gpt-4o"` and `True` for `"claude-sonnet-4-6"`.

- [ ] **3.3.3** `ApiGatekeeper` MUST call `VersionValidator.validate_model` before every API call.  
  → verify: Unit test with an unknown model asserts `UnknownModelError` is raised.

### 3.4 SDK Client (`src/graphify_debugger/sdk/claude_client.py`)

- [ ] **3.4.1** Write `ClaudeClient` as a thin wrapper around `anthropic.Anthropic()`.  
  → verify: `mypy` passes; file ≤ 150 lines; only file in `src/` allowed to import `anthropic.Anthropic`.

- [ ] **3.4.2** Implement `create_message(payload: LLMPayload) -> LLMResponse` mapping to `client.messages.create(...)`.  
  → verify: Unit test with mocked `anthropic.Anthropic` asserts the call is dispatched with correct parameters.

- [ ] **3.4.3** Enforce via CI `grep` that no file outside `sdk/claude_client.py` imports `anthropic.Anthropic` directly.  
  → verify: Adding `import anthropic; anthropic.Anthropic()` to a service file fails the `lint` CI job.

### 3.5 Rate Limiter (`src/graphify_debugger/shared/rate_limiter.py`)

- [ ] **3.5.1** Write `RateLimiter` with a `collections.deque`-backed FIFO queue.  
  → verify: `mypy` passes; file ≤ 150 lines.

- [ ] **3.5.2** Implement `enqueue(payload: LLMPayload) -> None` with backpressure logic per `PLAN.md §3.2`.  
  → verify: Unit test submitting 51 requests to a 50 RPM limiter confirms the 51st request is queued.

- [ ] **3.5.3** Implement exponential backoff retry with values from `config/rate_limits.json`.  
  → verify: Unit test with mocked sleep confirms backoff intervals are `[1, 2, 4, 8, 16]` seconds.

- [ ] **3.5.4** Raise `RateLimitExhaustedError` after `max_retries` exhausted.  
  → verify: Unit test simulating 6 consecutive rate-limit responses confirms the error is raised on attempt 6.

### 3.6 Budget Tracker (`src/graphify_debugger/shared/budget_tracker.py`)

- [ ] **3.6.1** Write `BudgetTracker` with `record_transaction` and `check_pre_call` methods.  
  → verify: `mypy` passes; file ≤ 150 lines.

- [ ] **3.6.2** Implement `check_pre_call(estimated_cost: float)` that raises `BudgetExceededError` when ceiling would be breached.  
  → verify: Unit test providing `estimated_cost` that pushes total to 100.01% raises `BudgetExceededError`.

- [ ] **3.6.3** Implement the 90% WARNING threshold with `max_tokens` reduction flag.  
  → verify: Unit test at 90.1% spend asserts `WARNING` log emitted and `reduce_max_tokens = True` returned.

- [ ] **3.6.4** Implement atomic ledger flush to `session_ledger.json` via temp-file + `os.replace`.  
  → verify: Unit test simulating mid-write crash (interrupting `os.replace`) confirms no partial JSON on disk.

- [ ] **3.6.5** Implement `get_session_ledger() -> SessionLedger` returning a snapshot of current state.  
  → verify: Unit test confirms returned model is frozen and equals recorded transactions.

- [ ] **3.6.6** Write `BudgetExceededError` with the payload fields defined in `PRD_budget_tracker.md §5`.  
  → verify: Unit test catching `BudgetExceededError` confirms all four payload fields are accessible.

### 3.7 API Gatekeeper (`src/graphify_debugger/shared/gatekeeper.py`)

- [ ] **3.7.1** Write `ApiGatekeeper` as a thread-safe singleton using `threading.Lock`.  
  → verify: Unit test asserting two `ApiGatekeeper()` calls return the same object instance.

- [ ] **3.7.2** Implement `call(payload: LLMPayload) -> LLMResponse` following the 8-step sequence in `PLAN.md §3.1`.  
  → verify: Unit test with mocked sub-components confirms steps execute in order 1–8.

- [ ] **3.7.3** Implement `session_report() -> SessionLedger` delegating to `BudgetTracker.get_session_ledger()`.  
  → verify: Unit test after 3 mock calls asserts `session_report().total_transactions == 3`.

- [ ] **3.7.4** Confirm `BudgetExceededError` is NOT caught inside `call()` — it propagates to caller.  
  → verify: Unit test catching only `Exception` in agent tool code does NOT suppress `BudgetExceededError`.

- [ ] **3.7.5** Write unit tests for `gatekeeper.py` achieving ≥ 95% branch coverage.  
  → verify: `pytest tests/unit/test_gatekeeper.py --cov=src/graphify_debugger/shared/gatekeeper --cov-fail-under=95` passes.

---

## Phase 4: CrewAI Agents & Diagnostic Tools

### 4.1 Navigator Agent (`src/graphify_debugger/agents/navigator_agent.py`)

- [ ] **4.1.1** Define `NavigatorAgent` as a CrewAI `Agent` with role, goal, and backstory fields.  
  → verify: `mypy` passes; file ≤ 150 lines.

- [ ] **4.1.2** Implement `select_hot_nodes(graph: Graph, top_n: int) -> list[Node]` reading `hot.md`.  
  → verify: Unit test with sample `hot.md` fixture asserts exactly `top_n` nodes returned.

- [ ] **4.1.3** Implement `resolve_subgraph(seed_nodes: list[Node], depth: int) -> list[Node]` via BFS on `graph.json`.  
  → verify: Unit test with a 5-node chain graph at `depth=2` returns exactly 3 nodes.

- [ ] **4.1.4** Implement relevance-threshold filtering (default 0.6) on edge weights.  
  → verify: Unit test confirms nodes connected by edges weighted < 0.6 are excluded.

### 4.2 Reader Agent (`src/graphify_debugger/agents/reader_agent.py`)

- [ ] **4.2.1** Define `ReaderAgent` as a CrewAI `Agent`.  
  → verify: `mypy` passes; file ≤ 150 lines.

- [ ] **4.2.2** Implement `read_slice(node: Node) -> FileSlice` reading only the line range from the node annotation.  
  → verify: Unit test confirms only lines `[node.start_line, node.end_line]` are returned.

- [ ] **4.2.3** Implement `read_count` property returning number of distinct file slices read in the session.  
  → verify: Unit test after 3 `read_slice` calls (2 unique files) asserts `read_count == 3`.

- [ ] **4.2.4** `ReaderAgent` MUST refuse to read any file not present in the current subgraph.  
  → verify: Unit test requesting a file outside the subgraph raises `UnauthorizedReadError`.

### 4.3 Reasoner Agent (`src/graphify_debugger/agents/reasoner_agent.py`)

- [ ] **4.3.1** Define `ReasonerAgent` as a CrewAI `Agent` with structured output enforced via Pydantic.  
  → verify: `mypy` passes; file ≤ 150 lines.

- [ ] **4.3.2** Implement `generate_hypothesis(slices: list[FileSlice]) -> Hypothesis` producing a `Hypothesis` Pydantic model.  
  → verify: Unit test with mocked gatekeeper asserts returned object is a valid `Hypothesis` instance.

- [ ] **4.3.3** The hypothesis JSON MUST include: `root_cause_node`, `affected_lines`, `confidence_score`, `explanation`.  
  → verify: Unit test asserts all four fields are non-null on returned object.

- [ ] **4.3.4** If `confidence_score < 0.7`, the agent MUST request one additional `read_slice` from `ReaderAgent`.  
  → verify: Integration test with low-confidence mock response confirms a second read call is made.

### 4.4 Patcher Agent (`src/graphify_debugger/agents/patcher_agent.py`)

- [ ] **4.4.1** Define `PatcherAgent` as a CrewAI `Agent`.  
  → verify: `mypy` passes; file ≤ 150 lines.

- [ ] **4.4.2** Implement `write_patch(hypothesis: Hypothesis) -> Diff` producing the minimal unified diff.  
  → verify: Unit test with a known bug confirms `Diff.lines_changed` is minimal (≤ 10 lines for a simple bug).

- [ ] **4.4.3** `PatcherAgent` MUST NOT modify lines outside `hypothesis.affected_lines` ± 5 context lines.  
  → verify: Unit test confirms patch touches no lines outside the allowed range.

- [ ] **4.4.4** Implement `update_vault(diff: Diff, hypothesis: Hypothesis) -> None` writing a new Obsidian markdown node.  
  → verify: Unit test confirms a new `.md` file is created in `workspace/vault/` with correct frontmatter.

### 4.5 Orchestrator (`src/graphify_debugger/orchestrator.py`)

- [ ] **4.5.1** Define the CrewAI `Crew` wiring `NavigatorAgent → ReaderAgent → ReasonerAgent → PatcherAgent`.  
  → verify: `mypy` passes; file ≤ 150 lines.

- [ ] **4.5.2** Inject the singleton `ApiGatekeeper` into all agents at startup.  
  → verify: Unit test confirms all four agents share the same gatekeeper instance.

- [ ] **4.5.3** Implement top-level `BudgetExceededError` handler that writes the final ledger before exiting.  
  → verify: Integration test triggering kill switch confirms ledger file exists and is valid JSON after termination.

- [ ] **4.5.4** Implement a wall-clock timer wrapping the full run for KPI measurement.  
  → verify: Unit test confirms `time_to_root_cause_s` field is populated in the final report.

---

## Phase 5: Debugging, Regression Testing & Vault Updates

### 5.1 Baseline Run (Naive Agent)

- [ ] **5.1.1** Implement a `BaselineAgent` that feeds the full buggy file as context (no graph navigation).  
  → verify: `BaselineAgent` exists in `agents/baseline_agent.py`; `mypy` passes.

- [ ] **5.1.2** Run `BaselineAgent` against the target bug and capture: total input tokens, output tokens, file reads, time, cost.  
  → verify: `workspace/baseline_report.json` exists with all five metrics.

- [ ] **5.1.3** Store baseline metrics as immutable fixtures in `tests/fixtures/baseline_metrics.json`.  
  → verify: File exists and JSON is parseable.

### 5.2 Graph-Guided Run

- [ ] **5.2.1** Run the full graph-guided pipeline against the same target bug.  
  → verify: Pipeline completes without `BudgetExceededError`; `session_ledger.json` is written.

- [ ] **5.2.2** Capture the same five metrics from `session_ledger.json` for KPI comparison.  
  → verify: `workspace/guided_report.json` exists with all five metrics.

- [ ] **5.2.3** Verify the Patcher's output diff applies cleanly to the buggy file.  
  → verify: `patch --dry-run` exits 0 on the generated diff.

### 5.3 Regression Testing

- [ ] **5.3.1** Apply the patch to the buggy file.  
  → verify: `patch` command exits 0 with no rejects.

- [ ] **5.3.2** Run the BugsInPy regression test suite against the patched version.  
  → verify: ALL previously failing tests now PASS; no previously passing tests now FAIL.

- [ ] **5.3.3** Record regression test results in `workspace/regression_report.json`.  
  → verify: File contains `all_pass: true` and counts of previously-failing tests now passing.

### 5.4 Unit Test Suite Completion

- [ ] **5.4.1** Ensure overall branch coverage ≥ 85% across `src/`.  
  → verify: `uv run pytest --cov=src --cov-fail-under=85` exits 0.

- [ ] **5.4.2** Ensure `ruff check .` exits 0 (0 violations).  
  → verify: CI `lint` job passes on the final commit.

- [ ] **5.4.3** Ensure `mypy --strict src/` exits 0.  
  → verify: CI `type-check` job passes on the final commit.

- [ ] **5.4.4** Ensure no file in `src/` exceeds 150 lines.  
  → verify: CI `line-limit-check` job passes on the final commit.

### 5.5 Post-Fix Obsidian Vault Updates

- [ ] **5.5.1** Confirm `PatcherAgent.update_vault` created a new vault node for the fix.  
  → verify: `workspace/vault/` contains a new `.md` file whose name includes the bug ID.

- [ ] **5.5.2** Confirm `index.md` has been updated with a pointer to the new node.  
  → verify: `grep "<bug_id>" workspace/vault/index.md` returns a match.

- [ ] **5.5.3** Re-run Grphify on the patched workspace to regenerate `graph.json` and `hot.md`.  
  → verify: New `graph.json` differs from the pre-patch version (new patch node appears).

---

## Phase 6: Budget Analysis & Metrics Validation

### 6.1 Token Efficiency Report Generation

- [ ] **6.1.1** Write `scripts/generate_efficiency_report.py` that reads `baseline_report.json` and `guided_report.json` and computes percentage reductions for all five KPI metrics.  
  → verify: Script exits 0 and prints a markdown table.

- [ ] **6.1.2** Assert input token reduction ≥ 70% (guided uses ≤ 30% of baseline tokens).  
  → verify: Report shows `input_token_reduction_pct >= 70.0`.

- [ ] **6.1.3** Assert output token reduction ≥ 40% (guided uses ≤ 60% of baseline tokens).  
  → verify: Report shows `output_token_reduction_pct >= 40.0`.

- [ ] **6.1.4** Assert file-read count reduction ≥ 75% (guided reads ≤ 25% of baseline file reads).  
  → verify: Report shows `file_read_reduction_pct >= 75.0`.

- [ ] **6.1.5** Assert time-to-root-cause reduction ≥ 25%.  
  → verify: Report shows `time_reduction_pct >= 25.0`.

- [ ] **6.1.6** Assert cost reduction ≥ 60%.  
  → verify: Report shows `cost_reduction_pct >= 60.0`.

- [ ] **6.1.7** Write the final report to `workspace/token_efficiency_report.md` in markdown table format.  
  → verify: File exists and is valid markdown (parseable by a markdown linter).

### 6.2 Cache Efficiency Analysis

- [ ] **6.2.1** Extract `total_cache_savings_usd` from `session_ledger.json`.  
  → verify: Value is > 0, confirming prompt caching was active.

- [ ] **6.2.2** Compute cache hit rate: `cache_read_input_tokens / (input_tokens + cache_read_input_tokens)`.  
  → verify: Cache hit rate > 0% is reported in `token_efficiency_report.md`.

- [ ] **6.2.3** Confirm context caching was enabled for all calls where system prompt > 1024 tokens.  
  → verify: All `TransactionRecord` entries for long-system-prompt calls have `cache_creation_input_tokens > 0`.

### 6.3 Budget Ledger Audit

- [ ] **6.3.1** Confirm every API call in the guided run has a corresponding entry in `session_ledger.json`.  
  → verify: `total_transactions` in ledger equals the number of `gatekeeper.call()` invocations logged at `DEBUG` level.

- [ ] **6.3.2** Confirm `kill_switch_triggered: false` in `session_ledger.json` for a successful run.  
  → verify: JSON field equals `false`.

- [ ] **6.3.3** Run a kill-switch stress test: set `budget_ceiling_usd` to $0.001 and confirm `BudgetExceededError` is raised before the second API call.  
  → verify: Integration test exits with `BudgetExceededError`; `session_ledger.json` shows `kill_switch_triggered: true`.

- [ ] **6.3.4** Confirm the sum of all `total_cost_usd` in `transactions[]` equals `total_cost_usd` in the ledger header (within floating-point tolerance of 0.0001 USD).  
  → verify: Python assertion `abs(sum_txn_costs - ledger_total) < 0.0001` passes.

### 6.4 Final Sign-Off Checklist

- [ ] **6.4.1** All 100+ TODO items above are checked off.  
  → verify: Manual review of this document shows no unchecked boxes.

- [ ] **6.4.2** `uv run pytest` exits 0 with ≥ 85% coverage.  
  → verify: CI `test` job green on `main` branch.

- [ ] **6.4.3** `ruff check .` exits 0.  
  → verify: CI `lint` job green on `main` branch.

- [ ] **6.4.4** `mypy --strict src/` exits 0.  
  → verify: CI `type-check` job green on `main` branch.

- [ ] **6.4.5** No file in `src/` exceeds 150 lines.  
  → verify: CI `line-limit-check` job green on `main` branch.

- [ ] **6.4.6** `workspace/token_efficiency_report.md` confirms all five KPI targets met.  
  → verify: Report file exists and all six KPI assertions in §6.1 pass.

- [ ] **6.4.7** Draw.io diagrams (`block_diagram.drawio`, `class_diagram.drawio`) committed to `docs/diagrams/`.  
  → verify: Both files exist and open without error in Draw.io desktop app.

- [ ] **6.4.8** `workspace/regression_report.json` confirms `all_pass: true`.  
  → verify: JSON field equals `true`.

- [ ] **6.4.9** `session_ledger.json` has `kill_switch_triggered: false` for the production run.  
  → verify: JSON field equals `false`.

- [ ] **6.4.10** All docs (`PRD.md`, `PRD_budget_tracker.md`, `PLAN.md`, `TODO.md`) are committed and up to date.  
  → verify: `git log --oneline docs/` shows recent commits for all four files.

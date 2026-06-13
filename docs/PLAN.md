# Architecture & Technical Design Plan

**Version:** 1.0.0  
**Status:** Active  
**Owner:** Senior Software Architect  
**Last Updated:** 2026-06-13

---

## 1. Architecture Model

### 1.1 C4 Component Overview

The system is structured across four C4 levels. This section details **Level 3 – Components**.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  System: CrewAI Graph-Guided Debugger                                        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Container: Python Application (uv-managed)                         │    │
│  │                                                                     │    │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐   │    │
│  │  │  Navigator   │   │   Reader     │   │     Reasoner         │   │    │
│  │  │   Agent      │──▶│   Agent      │──▶│      Agent           │   │    │
│  │  │              │   │              │   │                      │   │    │
│  │  │ graph.json   │   │ file slices  │   │ hypothesis JSON      │   │    │
│  │  │ hot.md       │   │ (targeted)   │   │ root-cause report    │   │    │
│  │  └──────┬───────┘   └──────┬───────┘   └──────────┬───────────┘   │    │
│  │         │                  │                       │               │    │
│  │         └──────────────────┴───────────────────────┘               │    │
│  │                             │                                       │    │
│  │                             ▼                                       │    │
│  │                  ┌─────────────────────┐                           │    │
│  │                  │    Patcher Agent    │                           │    │
│  │                  │  minimal diff write │                           │    │
│  │                  │  vault node update  │                           │    │
│  │                  └──────────┬──────────┘                           │    │
│  │                             │                                       │    │
│  │  ┌──────────────────────────▼──────────────────────────────────┐  │    │
│  │  │              API Gatekeeper (Singleton)                      │  │    │
│  │  │  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐   │  │    │
│  │  │  │  Budget Tracker  │  │  Rate-Limit  │  │  Token       │   │  │    │
│  │  │  │  (Kill Switch)   │  │  FIFO Queue  │  │  Telemetry   │   │  │    │
│  │  │  └─────────────────┘  └──────────────┘  └──────────────┘   │  │    │
│  │  └──────────────────────────┬──────────────────────────────────┘  │    │
│  │                             │                                       │    │
│  └─────────────────────────────┼───────────────────────────────────────┘   │
│                                │                                            │
│  External: Anthropic Claude API (claude-sonnet-4-6)                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Draw.io Diagrams

Two diagrams SHALL be produced and committed to `docs/diagrams/`:

#### Block Diagram (`block_diagram.drawio`)

Represents the **data-flow** perspective:

- **Blocks:** `BugsInPy Workspace`, `Grphify`, `graph.json`, `Obsidian Vault`, `CrewAI Orchestrator`, `API Gatekeeper`, `Anthropic API`, `Session Ledger`, `Token Efficiency Report`
- **Arrows:** labelled with payload type (e.g., `graph.json`, `targeted_file_slice`, `llm_payload`, `transaction_record`)
- **Color coding:** Blue = data stores; Green = agents; Orange = external services; Red = enforcement components

#### Class Diagram (`class_diagram.drawio`)

Represents the **OOP structure**:

```
ApiGatekeeper
  ├── + call(payload: LLMPayload) -> LLMResponse
  ├── + session_report() -> SessionLedger
  ├── - _budget_tracker: BudgetTracker
  ├── - _rate_limiter: RateLimiter
  └── - _client: anthropic.Anthropic

BudgetTracker
  ├── + record_transaction(tx: TransactionRecord) -> None
  ├── + check_pre_call(estimated_cost: float) -> None
  ├── + get_session_ledger() -> SessionLedger
  └── - _ledger: SessionLedger

RateLimiter (FIFO Queue)
  ├── + enqueue(payload: LLMPayload) -> None
  ├── + drain() -> Iterator[LLMPayload]
  └── - _queue: deque[LLMPayload]

ConfigManager
  ├── + load_budget_limits() -> BudgetLimits
  ├── + load_rate_limits() -> RateLimits
  └── - _config_dir: Path

VersionValidator
  ├── + validate_model(model_id: str) -> bool
  └── - _allowed_models: list[str]

NavigatorAgent (CrewAI Agent)
  ├── + select_hot_nodes(graph: Graph, top_n: int) -> list[Node]
  └── - _graph: Graph

ReaderAgent (CrewAI Agent)
  ├── + read_slice(node: Node) -> FileSlice
  └── - _read_count: int

ReasonerAgent (CrewAI Agent)
  └── + generate_hypothesis(slices: list[FileSlice]) -> Hypothesis

PatcherAgent (CrewAI Agent)
  ├── + write_patch(hypothesis: Hypothesis) -> Diff
  └── + update_vault(diff: Diff, hypothesis: Hypothesis) -> None
```

---

## 2. Directory Structure

```
crewai-graphify-debugger/
│
├── config/
│   ├── rate_limits.json          # RPM/TPM ceilings and FIFO queue settings
│   └── budget_limits.json        # Budget ceiling, pricing table, multipliers
│
├── docs/
│   ├── PRD.md
│   ├── PRD_budget_tracker.md
│   ├── PLAN.md
│   ├── TODO.md
│   └── diagrams/
│       ├── block_diagram.drawio
│       └── class_diagram.drawio
│
├── src/
│   └── graphify_debugger/        # Main package (≤150 lines per file)
│       │
│       ├── sdk/                  # All direct Anthropic SDK usage lives here
│       │   └── claude_client.py  # Thin wrapper: constructs anthropic.Anthropic()
│       │                         #   and exposes a typed call interface
│       │
│       ├── services/             # Business logic services
│       │   ├── graph_navigator.py    # Parses graph.json, resolves hot nodes
│       │   ├── file_reader.py        # Reads targeted line ranges from files
│       │   ├── patch_writer.py       # Applies minimal diffs
│       │   └── vault_updater.py      # Writes post-fix Obsidian vault nodes
│       │
│       ├── agents/               # CrewAI agent definitions
│       │   ├── navigator_agent.py
│       │   ├── reader_agent.py
│       │   ├── reasoner_agent.py
│       │   └── patcher_agent.py
│       │
│       ├── shared/               # Shared infrastructure — singleton classes
│       │   ├── gatekeeper.py     # ApiGatekeeper: intercepts ALL LLM calls
│       │   ├── budget_tracker.py # BudgetTracker + BudgetExceededError
│       │   ├── rate_limiter.py   # FIFO rate-limit queue
│       │   ├── config.py         # ConfigManager: loads config/*.json
│       │   └── version.py        # VersionValidator: allowed model list
│       │
│       ├── models/               # Pydantic data models (schemas)
│       │   ├── transaction.py    # TransactionRecord, SessionLedger
│       │   ├── graph.py          # Node, Edge, Graph
│       │   └── hypothesis.py     # Hypothesis, Diff, FileSlice
│       │
│       └── orchestrator.py       # Top-level CrewAI Crew + task wiring
│
├── tests/
│   ├── unit/
│   │   ├── test_gatekeeper.py
│   │   ├── test_budget_tracker.py
│   │   ├── test_rate_limiter.py
│   │   ├── test_config.py
│   │   ├── test_graph_navigator.py
│   │   └── test_file_reader.py
│   ├── integration/
│   │   ├── test_full_pipeline.py     # End-to-end with mocked Anthropic API
│   │   └── test_budget_kill_switch.py
│   └── fixtures/
│       ├── sample_graph.json
│       ├── sample_budget_limits.json
│       └── sample_vault/
│
├── pyproject.toml                # uv / ruff / pytest-cov configuration
├── main.py                       # CLI entry point
└── README.md
```

### 2.1 File Size Enforcement

The 150-line limit is enforced at two levels:

1. **Pre-commit hook** (`ruff` custom rule or a shell script counting lines per file).
2. **CI gate** — a step in the GitHub Actions workflow that runs:
   ```bash
   python scripts/check_line_limits.py --max-lines 150 src/
   ```
   This step fails the build if any source file under `src/` exceeds 150 lines.

---

## 3. Token Telemetry Design

### 3.1 `ApiGatekeeper` Interception Flow

Every LLM call in the system MUST use the gatekeeper. The following sequence describes the full interception lifecycle:

```
Agent Tool
    │
    │  call(payload: LLMPayload)
    ▼
ApiGatekeeper.call()
    │
    ├─[1] ConfigManager.load_budget_limits()        # Verify limits loaded
    ├─[2] BudgetTracker.check_pre_call(estimate)    # Pre-call budget gate
    │       └─ raises BudgetExceededError if over    #   (HARD STOP before call)
    │
    ├─[3] VersionValidator.validate_model(model)    # Reject unknown models
    │
    ├─[4] RateLimiter.enqueue(payload)              # FIFO queue admission
    │       └─ blocks if RPM/TPM ceiling reached    #   (backpressure)
    │
    ├─[5] claude_client.messages.create(**payload)  # SDK call (only here!)
    │
    ├─[6] Build TransactionRecord from response     # Token counts + cost
    ├─[7] BudgetTracker.record_transaction(tx)      # Update cumulative state
    │       └─ emits WARNING log at 90% threshold
    │       └─ writes ledger to disk (atomic write)
    │
    └─[8] return LLMResponse                        # Back to agent tool
```

### 3.2 FIFO Rate-Limit Queue

The queue enforces two independent ceilings loaded from `config/rate_limits.json`:

```json
{
  "requests_per_minute": 50,
  "tokens_per_minute": 100000,
  "tokens_per_day": 2000000,
  "retry_backoff_seconds": [1, 2, 4, 8, 16],
  "max_retries": 5
}
```

**Queue Algorithm:**

1. When a call arrives, estimate its token count (input + max_output).
2. If `current_rpm < requests_per_minute` AND `current_tpm + estimate < tokens_per_minute`, admit immediately.
3. Otherwise, place the call at the **back** of the FIFO queue and start the exponential backoff timer.
4. The queue drains in FIFO order — no priority inversion.
5. After `max_retries` exhausted, raise `RateLimitExhaustedError`.

### 3.3 Ledger Persistence

The ledger is written atomically to prevent corruption on kill-switch interruption:

```python
# Atomic write pattern in budget_tracker.py
import tempfile, os, json

def _flush_ledger(self) -> None:
    tmp_path = self._ledger_path.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(self._ledger.model_dump(), f, indent=2)
    os.replace(tmp_path, self._ledger_path)  # atomic on POSIX
```

### 3.4 Budget Pre-Call Estimation

Before any call is dispatched, the gatekeeper estimates the maximum possible cost:

```python
def _estimate_call_cost(self, payload: LLMPayload) -> float:
    pricing = self._config.model_pricing[payload.model]
    # Worst case: no cache hits, full output
    input_cost = (payload.input_token_estimate / 1_000_000) * pricing.input_per_million
    output_cost = (payload.max_tokens / 1_000_000) * pricing.output_per_million
    return (input_cost + output_cost) * self._config.local_cost_multiplier
```

If `cumulative_cost + estimated_cost > ceiling`, `BudgetExceededError` is raised immediately.

---

## 4. OOP Design Principles

| Principle | Application |
|---|---|
| **Single Responsibility** | Each file has one class with one clear purpose; the 150-line limit enforces this structurally. |
| **Dependency Inversion** | Agents depend on abstract `LLMGateway` protocol; `ApiGatekeeper` is the concrete implementation injected at runtime. |
| **Open/Closed** | New models are added via `budget_limits.json`; no source changes required. |
| **Fail Fast** | `BudgetExceededError` and `RateLimitExhaustedError` are raised at the earliest possible point, never swallowed. |
| **Immutability** | `TransactionRecord` and `SessionLedger` are frozen Pydantic models; mutation is only permitted via the tracker's controlled API. |

---

## 5. Configuration Reference

### `config/rate_limits.json` (Full Schema)

```json
{
  "requests_per_minute": 50,
  "tokens_per_minute": 100000,
  "tokens_per_day": 2000000,
  "retry_backoff_seconds": [1, 2, 4, 8, 16],
  "max_retries": 5,
  "queue_max_size": 100,
  "queue_drain_interval_ms": 200
}
```

### `config/budget_limits.json` (Full Schema)

See `PRD_budget_tracker.md §3.4`.

---

## 6. Testing Strategy

### 6.1 Coverage Requirements

| Layer | Minimum Branch Coverage |
|---|---|
| `shared/` (gatekeeper, budget, rate limiter) | 95% |
| `services/` | 90% |
| `agents/` | 85% |
| `models/` | 80% |
| `sdk/` | 75% (integration-tested separately) |
| **Overall** | **≥ 85%** |

### 6.2 Test Doubles

- The Anthropic SDK is mocked via `pytest-mock` in all unit and integration tests.
- A `MockAnthropicClient` fixture is defined in `tests/fixtures/` and injected via dependency injection into `claude_client.py`.
- Real API calls are made only in a dedicated `tests/e2e/` suite gated behind an `E2E_TEST=1` environment variable.

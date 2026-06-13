# PRD: Token & Cost Budget Tracker Sub-System

**Version:** 1.0.0  
**Status:** Active  
**Parent PRD:** `PRD.md`  
**Owner:** Senior Software Architect  
**Last Updated:** 2026-06-13

---

## 1. Purpose

This document specifies the requirements for the **Token and Cost Budget Tracker**, a dedicated sub-system managed entirely by the centralized `ApiGatekeeper`. Its sole mandate is to provide real-time financial observability and hard enforcement of pre-allocated project budgets across every LLM interaction in the pipeline.

The tracker is **not optional**. Every agent, every tool call, and every retry that touches an LLM MUST register a transaction with this sub-system before the API call is dispatched.

---

## 2. Core Requirements

### 2.1 Completeness

| ID | Requirement |
|---|---|
| BT-01 | The tracker SHALL record telemetry for **every** LLM API call without exception, including retries and cache-hit calls. |
| BT-02 | The tracker SHALL operate as a context manager so telemetry is captured even when downstream code raises an exception. |
| BT-03 | The tracker SHALL persist its state to a JSON ledger file after each transaction so that partial runs are recoverable. |
| BT-04 | The tracker SHALL be the **sole** source of truth for cumulative cost; agents MUST NOT compute cost independently. |

### 2.2 Real-Time Logging

| ID | Requirement |
|---|---|
| BT-05 | Each transaction log entry SHALL be written to both the JSON ledger and the Python `logging` facility at `DEBUG` level within 10ms of the API response being received. |
| BT-06 | A human-readable "financial decay" summary SHALL be emitted at `INFO` level every N calls (configurable, default: 5). |
| BT-07 | The decay summary SHALL include: calls so far, total USD spent, USD remaining, % of budget consumed, and projected final cost. |

### 2.3 Kill Switch

| ID | Requirement |
|---|---|
| BT-08 | When cumulative spend reaches **90%** of the budget ceiling, the tracker SHALL downgrade `max_tokens` on subsequent calls by 40% and emit a `WARNING`. |
| BT-09 | When cumulative spend reaches **100%** of the budget ceiling, the tracker SHALL raise `BudgetExceededError` with a structured payload before the API call is dispatched. |
| BT-10 | `BudgetExceededError` SHALL be uncatchable within agent tool code; it MUST propagate to the top-level orchestrator which logs the final ledger and terminates. |
| BT-11 | The budget ceiling SHALL be loaded exclusively from `config/budget_limits.json`; hard-coded ceiling values in source code are forbidden. |

---

## 3. Data Schemas

### 3.1 Transaction Record

A single `TransactionRecord` is created per API call.

```json
{
  "transaction_id": "txn_20260613_001",
  "timestamp_utc": "2026-06-13T14:23:01.412Z",
  "agent_name": "ReasonerAgent",
  "tool_name": "analyze_hypothesis",
  "model_engine": "claude-sonnet-4-6",
  "input_tokens": 1842,
  "output_tokens": 317,
  "cache_creation_input_tokens": 1024,
  "cache_read_input_tokens": 512,
  "local_cost_multiplier": 1.0,
  "input_cost_usd": 0.005526,
  "output_cost_usd": 0.004755,
  "total_cost_usd": 0.010281,
  "cumulative_cost_usd": 0.043211,
  "budget_ceiling_usd": 2.00,
  "budget_remaining_usd": 1.956789,
  "budget_consumed_pct": 2.16,
  "cache_savings_usd": 0.003072,
  "retry_attempt": 0,
  "rate_limited": false,
  "status": "success"
}
```

### 3.2 Field Definitions

| Field | Type | Source | Description |
|---|---|---|---|
| `transaction_id` | `str` | Generated | `txn_<YYYYMMDD>_<seq>` — unique per run |
| `timestamp_utc` | `str` | `datetime.utcnow()` | ISO-8601 timestamp at response receipt |
| `agent_name` | `str` | CrewAI context | Name of the CrewAI agent that initiated the call |
| `tool_name` | `str` | CrewAI context | Name of the tool/task that triggered the call |
| `model_engine` | `str` | API response | Exact model string returned by the API (e.g., `claude-sonnet-4-6`) |
| `input_tokens` | `int` | `response.usage.input_tokens` | Prompt tokens billed; excludes cache reads |
| `output_tokens` | `int` | `response.usage.output_tokens` | Completion tokens billed |
| `cache_creation_input_tokens` | `int` | `response.usage.cache_creation_input_tokens` | Tokens written into the prompt cache (1.25× rate) |
| `cache_read_input_tokens` | `int` | `response.usage.cache_read_input_tokens` | Tokens served from cache (0.1× rate) |
| `local_cost_multiplier` | `float` | `config/budget_limits.json` | Region/tier pricing correction factor (default `1.0`) |
| `input_cost_usd` | `float` | Computed | `input_tokens × input_price_per_token × local_cost_multiplier` |
| `output_cost_usd` | `float` | Computed | `output_tokens × output_price_per_token × local_cost_multiplier` |
| `total_cost_usd` | `float` | Computed | `input_cost_usd + output_cost_usd` |
| `cumulative_cost_usd` | `float` | Ledger state | Running sum across all transactions in this run |
| `budget_ceiling_usd` | `float` | `config/budget_limits.json` | Hard stop limit for the current run |
| `budget_remaining_usd` | `float` | Computed | `budget_ceiling_usd - cumulative_cost_usd` |
| `budget_consumed_pct` | `float` | Computed | `(cumulative_cost_usd / budget_ceiling_usd) × 100` |
| `cache_savings_usd` | `float` | Computed | Cost avoided due to cache reads vs. full prompt billing |
| `retry_attempt` | `int` | Gatekeeper state | 0 for first attempt; incremented on rate-limit retry |
| `rate_limited` | `bool` | Gatekeeper state | `true` if this call was delayed by the FIFO rate-limit queue |
| `status` | `str` | Gatekeeper state | `"success"` \| `"rate_limited"` \| `"budget_exceeded"` \| `"error"` |

### 3.3 Session Ledger

The `session_ledger.json` file accumulates all `TransactionRecord` objects and a header:

```json
{
  "run_id": "run_20260613_bugsinpy_pandas_142",
  "started_utc": "2026-06-13T14:22:58.001Z",
  "completed_utc": null,
  "bug_target": "pandas#142",
  "total_transactions": 7,
  "total_input_tokens": 12483,
  "total_output_tokens": 2814,
  "total_cache_savings_usd": 0.021440,
  "total_cost_usd": 0.183921,
  "budget_ceiling_usd": 2.00,
  "budget_consumed_pct": 9.20,
  "kill_switch_triggered": false,
  "transactions": [ ]
}
```

### 3.4 `budget_limits.json` Schema

```json
{
  "default_ceiling_usd": 2.00,
  "warning_threshold_pct": 90,
  "max_tokens_reduction_pct_at_warning": 40,
  "local_cost_multiplier": 1.0,
  "model_pricing": {
    "claude-sonnet-4-6": {
      "input_per_million_tokens_usd": 3.00,
      "output_per_million_tokens_usd": 15.00,
      "cache_write_per_million_tokens_usd": 3.75,
      "cache_read_per_million_tokens_usd": 0.30
    },
    "claude-haiku-4-5-20251001": {
      "input_per_million_tokens_usd": 0.80,
      "output_per_million_tokens_usd": 4.00,
      "cache_write_per_million_tokens_usd": 1.00,
      "cache_read_per_million_tokens_usd": 0.08
    }
  }
}
```

---

## 4. Financial Control Rules

### 4.1 Budget Thresholds

```
0%        50%       90%              100%
│──────────│─────────│────────────────│
  NORMAL      NORMAL   WARNING        KILL SWITCH
                       (max_tokens-40%)
```

| Threshold | Trigger Condition | System Behavior |
|---|---|---|
| **Normal** | `consumed_pct < 90` | Standard operation; decay summary every 5 calls. |
| **Warning** | `90 ≤ consumed_pct < 100` | Log `WARNING`; reduce `max_tokens` by 40% on all subsequent calls; emit decay summary on every call. |
| **Kill Switch** | `consumed_pct ≥ 100` | Raise `BudgetExceededError` before dispatching the call; write final ledger; terminate orchestrator. |

### 4.2 Cost Projection

At the Warning threshold, the tracker SHALL compute a linear projection:

```
projected_final_usd = cumulative_cost_usd / (calls_completed / total_expected_calls)
```

`total_expected_calls` is an estimate loaded from the orchestrator config. If projection exceeds the ceiling, the kill switch activates immediately regardless of current percentage.

### 4.3 Pre-Call Budget Check

The gatekeeper MUST execute the following check **before** dispatching any API call:

```python
projected_call_cost = estimate_call_cost(payload)
if cumulative_cost_usd + projected_call_cost > budget_ceiling_usd:
    raise BudgetExceededError(...)
```

This prevents partial-budget overruns caused by expensive single calls.

---

## 5. Error Definitions

### `BudgetExceededError`

```python
class BudgetExceededError(RuntimeError):
    """
    Raised by ApiGatekeeper when a call would exceed the budget ceiling.
    Not catchable within agent tool code — propagates to orchestrator only.
    """
    def __init__(
        self,
        cumulative_cost_usd: float,
        projected_call_cost_usd: float,
        budget_ceiling_usd: float,
        ledger_path: str,
    ) -> None: ...
```

The exception payload MUST include:
- Cumulative spend to date
- Estimated cost of the blocked call
- Budget ceiling
- Absolute path to the session ledger for post-mortem analysis

---

## 6. Acceptance Criteria

| ID | Criterion | Verification |
|---|---|---|
| AC-01 | Every API call in a full pipeline run appears in `session_ledger.json` | Compare `total_transactions` to mock call count in integration test |
| AC-02 | Kill switch halts execution before cumulative cost exceeds ceiling | Inject mock calls that push spend to 99.9%; verify `BudgetExceededError` on next call |
| AC-03 | `max_tokens` is reduced at 90% threshold | Assert gatekeeper payload modification in unit test |
| AC-04 | Ledger is written to disk after partial run that hits kill switch | Read ledger file after `BudgetExceededError` is caught in integration test |
| AC-05 | Cache savings are correctly computed | Use known token counts and pricing; assert `cache_savings_usd` within 0.0001 USD tolerance |
| AC-06 | `BudgetExceededError` propagates past agent tool `try/except` blocks | Unit test catching only `Exception` must NOT suppress `BudgetExceededError` |

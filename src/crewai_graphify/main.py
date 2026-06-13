"""Entry point — wires up the graph-guided debugging crew and reports results."""
from __future__ import annotations

import contextlib
import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import anthropic
from anthropic.types import TextBlock
from crewai import Crew, Process

from crewai_graphify.agents.crew import navigator_agent, patcher_agent, reader_agent, reasoner_agent
from crewai_graphify.agents.tasks import navigator_task, patcher_task, reader_task, reasoner_task
from crewai_graphify.models.llm import LLMPayload, LLMResponse, UsageStats
from crewai_graphify.shared.budget_tracker import BudgetTracker, SessionLedger
from crewai_graphify.shared.config import AppConfig
from crewai_graphify.shared.gatekeeper import ApiGatekeeper
from crewai_graphify.shared.rate_limiter import ThrottledRateLimiter

_log = logging.getLogger(__name__)
_WORKSPACE = Path("workspace")
_TARGET_PY = _WORKSPACE / "target" / "broken-python" / "polygons" / "polygons.py"
_CHARS_PER_TOKEN = 4
_VALID_MSG_KEYS = frozenset({"role", "content"})


def _sanitize_messages(psystem: str, msgs: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Hoist system-role messages; strip non-standard keys; return (system, msgs)."""
    sys_parts = [m["content"] for m in msgs if m.get("role") == "system"]
    rest = [m for m in msgs if m.get("role") != "system"]
    if sys_parts:
        _log.warning("Hoisted %d system message(s) to top-level param.", len(sys_parts))
    cleaned = [{k: v for k, v in m.items() if k in _VALID_MSG_KEYS} for m in rest]
    if extras := [set(m) - _VALID_MSG_KEYS for m in rest if set(m) - _VALID_MSG_KEYS]:
        _log.warning("Stripped non-standard message keys: %s", extras)
    return ("\n\n".join(sys_parts) if sys_parts else psystem), cleaned


class _AnthropicClient:
    """Minimal Anthropic SDK adapter satisfying _ClientProtocol."""

    def __init__(self) -> None:
        self._sdk = anthropic.Anthropic()

    def create_message(self, payload: LLMPayload) -> LLMResponse:
        system, clean_msgs = _sanitize_messages(payload.system, payload.messages)
        msg = self._sdk.messages.create(
            model=payload.model,
            max_tokens=payload.max_tokens,
            system=system,
            messages=clean_msgs,  # type: ignore[arg-type]
        )
        text_blocks = [b for b in msg.content if isinstance(b, TextBlock)]
        return LLMResponse(
            id=msg.id,
            model=msg.model,
            content=text_blocks[0].text if text_blocks else "",
            usage=UsageStats(
                input_tokens=msg.usage.input_tokens,
                output_tokens=msg.usage.output_tokens,
            ),
            stop_reason=msg.stop_reason or "end_turn",
        )


@contextlib.contextmanager
def _budget_session(config: AppConfig) -> Iterator[BudgetTracker]:
    """Yield a fresh BudgetTracker after wiring it into ApiGatekeeper."""
    tracker = BudgetTracker(config)
    ApiGatekeeper().initialize(
        client=_AnthropicClient(),
        budget_tracker=tracker,
        rate_limiter=ThrottledRateLimiter(),
    )
    yield tracker


def _save_root_cause(raw: str) -> None:
    """Persist the Reasoner's final output to workspace/root_cause_report.json."""
    _WORKSPACE.mkdir(exist_ok=True)
    path = _WORKSPACE / "root_cause_report.json"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"raw_output": raw}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    _log.info("Root-cause report → %s", path)


def _save_efficiency_report(ledger: SessionLedger) -> None:
    """Write workspace/token_efficiency_report.md with session telemetry."""
    naive = max(1, len(_TARGET_PY.read_text(encoding="utf-8")) // _CHARS_PER_TOKEN) if _TARGET_PY.exists() else 0
    savings = max(0, naive - ledger.actual_input_tokens)
    pct = savings / naive * 100 if naive else 0.0
    lines = [
        "# Token Efficiency Report\n",
        "## Session Summary\n",
        "| Metric | Value |",
        "|---|---|",
        f"| Total API calls made | {ledger.total_transactions} |",
        f"| Estimated input tokens (pre-call) | {ledger.estimated_input_tokens:,} |",
        f"| Actual input tokens billed | {ledger.actual_input_tokens:,} |",
        f"| Actual output tokens billed | {ledger.actual_output_tokens:,} |",
        f"| Total estimated cost | ${ledger.total_cost_usd:.6f} |\n",
        "## Token Savings — Graph-Guided Slicing vs. Naive Full-File Dump\n",
        "| Approach | Input tokens |",
        "|---|---|",
        f"| Naive: read all of `polygons.py` into context | {naive:,} |",
        f"| Graph-guided: actual billed input (this run) | {ledger.actual_input_tokens:,} |",
        f"| **Savings** | **{savings:,} tokens ({pct:.1f}% reduction)** |\n",
        "> Graph-guided slicing reads only hot-node line ranges identified by the dependency",
        "> graph (Polygon L3–8, calc\\_polygon\\_details L13–36, \\_\\_main\\_\\_ L1–69),",
        "> eliminating irrelevant code from the context window and reducing token cost proportionally.",
    ]
    (_WORKSPACE / "token_efficiency_report.md").write_text("\n".join(lines), encoding="utf-8")
    _log.info("Efficiency report → %s", _WORKSPACE / "token_efficiency_report.md")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    config = AppConfig.load()
    nav = navigator_agent()
    rdr = reader_agent()
    rsn = reasoner_agent()
    ptr = patcher_agent()
    t1 = navigator_task(nav)
    t2 = reader_task(rdr, t1)
    t3 = reasoner_task(rsn, t2)
    t4 = patcher_task(ptr, t3)
    crew = Crew(agents=[nav, rdr, rsn, ptr], tasks=[t1, t2, t3, t4], process=Process.sequential, verbose=True)
    with _budget_session(config) as tracker:
        result = crew.kickoff()
    _save_root_cause(str(result))
    ledger = tracker.get_session_ledger()
    _save_efficiency_report(ledger)
    _log.info("Run complete — %d call(s), $%.6f total.", ledger.total_transactions, ledger.total_cost_usd)


if __name__ == "__main__":
    main()

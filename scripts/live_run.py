"""Standalone end-to-end live debugging run.

Drives the exact pipeline functions the FastAPI backend uses
(``build_crew`` → ``crew.kickoff(inputs=...)`` → ``archive_run``) but without
the uvicorn/SSE layer, so a full graph-guided debugging loop can be triggered
from the command line.  Provider is selected from ``.env`` (LLM_PROVIDER).
"""
from __future__ import annotations

import os
import sys

import crewai_graphify.shared.env  # noqa: F401  — load_dotenv() side effect on import
from crewai_graphify.agents.pipeline import build_crew
from crewai_graphify.main import _AnthropicClient
from crewai_graphify.sdk.deepseek_client import DeepSeekAdapter
from crewai_graphify.shared.archiver import archive_run
from crewai_graphify.shared.budget_tracker import BudgetTracker
from crewai_graphify.shared.config import AppConfig
from crewai_graphify.shared.fixture_setup import ensure_fixture
from crewai_graphify.shared.gatekeeper import ApiGatekeeper
from crewai_graphify.shared.rate_limiter import ThrottledRateLimiter

_SKIP = "SKIPPED"
_RETRY_HINT = (
    "Previous read was insufficient. You MUST expand your line range "
    "(e.g., read lines 15-50) to find the missing implementation details."
)


def _log(msg: str) -> None:
    print(msg, flush=True)


def _init_gatekeeper() -> BudgetTracker:
    """Wire the ApiGatekeeper with a provider-appropriate SDK adapter."""
    ApiGatekeeper._instance = None
    tracker = BudgetTracker(AppConfig.load())
    is_deepseek = os.getenv("LLM_PROVIDER", "claude").lower() == "deepseek"
    client = DeepSeekAdapter() if is_deepseek else _AnthropicClient()
    ApiGatekeeper().initialize(
        client=client, budget_tracker=tracker, rate_limiter=ThrottledRateLimiter()
    )
    return tracker


def main() -> int:
    _log(f"=== LIVE RUN — provider={os.getenv('LLM_PROVIDER')} model={os.getenv('DEFAULT_MODEL')} ===")

    _log("\n[1/5] Resetting workspace/target and rebuilding vault graph…")
    ensure_fixture(_log)

    _log("\n[2/5] Initialising ApiGatekeeper (budget + telemetry) for the provider…")
    tracker = _init_gatekeeper()

    _log("\n[3/5] Running the 4-agent crew (Navigator → Reader → Reasoner → Patcher)…")
    retry_hint = ""
    result = ""
    for attempt in range(3):
        crew, inputs = build_crew(retry_hint=retry_hint)
        result = str(crew.kickoff(inputs=inputs))
        if _SKIP not in result:
            break
        retry_hint = _RETRY_HINT
        _log(f"INFO: Attempt {attempt + 1}/3 skipped — retrying with expanded context…")

    _log("\n[4/5] Crew final answer:")
    _log(result)

    ledger = tracker.get_session_ledger()
    _log(
        f"\n[budget] provider tracked via ApiGatekeeper — "
        f"{ledger.total_transactions} call(s), "
        f"in={ledger.actual_input_tokens} out={ledger.actual_output_tokens} tokens, "
        f"${ledger.total_cost_usd:.6f}"
    )

    _log("\n[5/5] Post-run validation gate + archiver:")
    archive_run(result, _log)
    return 0


if __name__ == "__main__":
    sys.exit(main())

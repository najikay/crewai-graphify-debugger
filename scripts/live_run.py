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
from crewai_graphify.shared.archiver import archive_run
from crewai_graphify.shared.fixture_setup import ensure_fixture

_SKIP = "SKIPPED"
_RETRY_HINT = (
    "Previous read was insufficient. You MUST expand your line range "
    "(e.g., read lines 15-50) to find the missing implementation details."
)


def _log(msg: str) -> None:
    print(msg, flush=True)


def main() -> int:
    _log(f"=== LIVE RUN — provider={os.getenv('LLM_PROVIDER')} model={os.getenv('DEFAULT_MODEL')} ===")

    _log("\n[1/4] Resetting workspace/target and rebuilding vault graph…")
    ensure_fixture(_log)

    _log("\n[2/4] Running the 4-agent crew (Navigator → Reader → Reasoner → Patcher)…")
    retry_hint = ""
    result = ""
    for attempt in range(3):
        crew, inputs = build_crew(retry_hint=retry_hint)
        result = str(crew.kickoff(inputs=inputs))
        if _SKIP not in result:
            break
        retry_hint = _RETRY_HINT
        _log(f"INFO: Attempt {attempt + 1}/3 skipped — retrying with expanded context…")

    _log("\n[3/4] Crew final answer:")
    _log(result)

    _log("\n[4/4] Post-run validation gate + archiver:")
    archive_run(result, _log)
    return 0


if __name__ == "__main__":
    sys.exit(main())

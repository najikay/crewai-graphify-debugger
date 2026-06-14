"""FastAPI server — REST + SSE endpoints for the Visual Agentic OS UI."""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse

import crewai_graphify.shared.env  # noqa: F401  — load_dotenv() side effect on import
from crewai_graphify.agents.pipeline import build_crew
from crewai_graphify.main import _AnthropicClient, _save_efficiency_report, _save_root_cause
from crewai_graphify.shared.archiver import archive_run
from crewai_graphify.shared.budget_tracker import BudgetTracker
from crewai_graphify.shared.config import AppConfig
from crewai_graphify.shared.fixture_setup import ensure_fixture
from crewai_graphify.shared.gatekeeper import ApiGatekeeper
from crewai_graphify.shared.rate_limiter import ThrottledRateLimiter
from crewai_graphify.shared.sse_log import _QueueLogHandler, _StdoutToQueue

_VAULT_GRAPH = Path("workspace/vault/graph.json")
_TARGET = Path("workspace/target")
_RESULTS = Path("workspace/results")
_EXECUTOR: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1)
_SSE_QUEUE: asyncio.Queue[str | None] = asyncio.Queue()
_run_active: bool = False
_SKIP = "SKIPPED"
_RETRY_HINT = "Previous read was insufficient. You MUST expand your line range (e.g., read lines 15-50) to find the missing implementation details."

app = FastAPI(title="CrewAI Graphify — Visual Agentic OS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_pipeline(loop: asyncio.AbstractEventLoop) -> None:
    """Build and run the 4-agent crew; push log lines into the SSE queue."""
    global _run_active

    def _push(msg: str) -> None:
        loop.call_soon_threadsafe(_SSE_QUEUE.put_nowait, msg)

    handler = _QueueLogHandler(loop, _SSE_QUEUE)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    try:
        ensure_fixture(_push)
        ApiGatekeeper._instance = None  # reset singleton for a fresh run
        config = AppConfig.load()
        tracker = BudgetTracker(config)
        ApiGatekeeper().initialize(
            client=_AnthropicClient(),
            budget_tracker=tracker,
            rate_limiter=ThrottledRateLimiter(),
        )
        retry_hint = ""
        result: Any = ""
        for _attempt in range(3):
            crew, inputs = build_crew(retry_hint=retry_hint)
            with redirect_stdout(_StdoutToQueue(loop, _SSE_QUEUE, sys.stdout)):
                result = crew.kickoff(inputs=inputs)
            if _SKIP not in str(result):
                break
            retry_hint = _RETRY_HINT
            _push(f"INFO: Attempt {_attempt + 1}/3 skipped — retrying with expanded context…")
        _save_root_cause(str(result))
        _save_efficiency_report(tracker.get_session_ledger())
        if _SKIP not in str(result):
            archive_run(str(result), _push)
    except Exception as exc:  # noqa: BLE001
        loop.call_soon_threadsafe(_SSE_QUEUE.put_nowait, f"ERROR: {exc}")
    finally:
        root_logger.removeHandler(handler)
        loop.call_soon_threadsafe(_SSE_QUEUE.put_nowait, None)  # sentinel → done
        _run_active = False


@app.get("/api/graph")
async def get_graph() -> dict[str, Any]:
    if not _VAULT_GRAPH.exists():
        raise HTTPException(status_code=404, detail="workspace/vault/graph.json not found")
    data: dict[str, Any] = json.loads(_VAULT_GRAPH.read_text(encoding="utf-8"))
    return data


@app.post("/api/execute", status_code=202)
async def execute_pipeline() -> dict[str, str]:
    global _run_active
    if _run_active:
        raise HTTPException(status_code=409, detail="A run is already in progress.")
    _run_active = True
    while not _SSE_QUEUE.empty():
        _SSE_QUEUE.get_nowait()
    loop = asyncio.get_running_loop()
    _EXECUTOR.submit(_run_pipeline, loop)
    return {"status": "started"}


@app.post("/api/reset")
async def reset_workspace() -> dict[str, str]:
    """Wipe workspace/target/, copy pristine fixture, rebuild graph.json."""
    if _run_active:
        raise HTTPException(status_code=409, detail="A run is in progress.")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_EXECUTOR, lambda: ensure_fixture(lambda _msg: None))
    return {"status": "ok"}


@app.get("/api/file")
async def get_file(path: str) -> PlainTextResponse:
    """Serve files from workspace/target/ or workspace/results/ (traversal-safe).

    Accepts both relative paths (joined with the base dir) and absolute paths
    (resolved directly then checked to be inside an allowed base dir).
    """
    p = Path(path)
    for base in (_TARGET, _RESULTS):
        candidate = (p if p.is_absolute() else base / p).resolve()
        if candidate.is_relative_to(base.resolve()) and candidate.exists():
            return PlainTextResponse(candidate.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail=f"{path} not found.")


@app.get("/api/stream")
async def stream_logs() -> StreamingResponse:
    async def _sse() -> AsyncGenerator[str, None]:
        while True:
            line = await _SSE_QUEUE.get()
            if line is None:
                yield "event: done\ndata: {}\n\n"
                break
            yield f"data: {json.dumps({'log': line})}\n\n"

    return StreamingResponse(_sse(), media_type="text/event-stream")

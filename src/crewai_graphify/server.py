"""FastAPI server — REST + SSE endpoints for the Visual Agentic OS UI."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import sys
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

from crewai import Crew, Process
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from crewai_graphify.agents.crew import navigator_agent, patcher_agent, reader_agent, reasoner_agent
from crewai_graphify.agents.tasks import navigator_task, patcher_task, reader_task, reasoner_task
from crewai_graphify.main import _AnthropicClient, _save_efficiency_report, _save_root_cause
from crewai_graphify.shared.budget_tracker import BudgetTracker
from crewai_graphify.shared.config import AppConfig
from crewai_graphify.shared.fixture_setup import ensure_fixture
from crewai_graphify.shared.gatekeeper import ApiGatekeeper
from crewai_graphify.shared.rate_limiter import ThrottledRateLimiter

_VAULT_GRAPH = Path("workspace/vault/graph.json")
_EXECUTOR: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1)
_SSE_QUEUE: asyncio.Queue[str | None] = asyncio.Queue()
_run_active: bool = False
_ANSI_RE: re.Pattern[str] = re.compile(r"\x1b\[[0-9;]*m")

app = FastAPI(title="CrewAI Graphify — Visual Agentic OS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class _QueueLogHandler(logging.Handler):
    """Push every log record onto the SSE queue from inside a worker thread."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self._loop = loop

    def emit(self, record: logging.LogRecord) -> None:
        self._loop.call_soon_threadsafe(_SSE_QUEUE.put_nowait, self.format(record))


class _StdoutToQueue(io.TextIOBase):
    """Mirror sys.stdout writes into the SSE queue (captures CrewAI verbose output)."""
    def __init__(self, loop: asyncio.AbstractEventLoop, orig: Any) -> None:
        super().__init__()
        self._loop = loop
        self._orig = orig

    def write(self, text: str) -> int:
        self._orig.write(text)
        for line in text.splitlines():
            if line.strip():
                self._loop.call_soon_threadsafe(_SSE_QUEUE.put_nowait, _ANSI_RE.sub("", line))
        return len(text)

    def flush(self) -> None:
        self._orig.flush()


def _run_pipeline(loop: asyncio.AbstractEventLoop) -> None:
    """Build and run the 4-agent crew; push log lines into the SSE queue."""
    global _run_active
    def _push(msg: str) -> None:
        loop.call_soon_threadsafe(_SSE_QUEUE.put_nowait, msg)
    handler = _QueueLogHandler(loop)
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
        nav, rdr, rsn, ptr = (
            navigator_agent(), reader_agent(), reasoner_agent(), patcher_agent()
        )
        t1 = navigator_task(nav)
        t2 = reader_task(rdr, t1)
        t3 = reasoner_task(rsn, t2)
        t4 = patcher_task(ptr, t3)
        crew = Crew(
            agents=[nav, rdr, rsn, ptr],
            tasks=[t1, t2, t3, t4],
            process=Process.sequential,
            verbose=True,
        )
        with redirect_stdout(_StdoutToQueue(loop, sys.stdout)):
            result = crew.kickoff()
        _save_root_cause(str(result))
        _save_efficiency_report(tracker.get_session_ledger())
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

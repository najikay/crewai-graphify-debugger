"""SSE log helpers — queue-backed logging handler and stdout mirror."""
from __future__ import annotations

import asyncio
import io
import logging
import re
from typing import Any

__all__ = ["_ANSI_RE", "_QueueLogHandler", "_StdoutToQueue"]

_ANSI_RE: re.Pattern[str] = re.compile(r"\x1b\[[0-9;]*m")


class _QueueLogHandler(logging.Handler):
    """Push every log record onto the SSE queue from inside a worker thread."""

    def __init__(
        self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue[str | None]
    ) -> None:
        super().__init__()
        self._loop = loop
        self._queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        self._loop.call_soon_threadsafe(self._queue.put_nowait, self.format(record))


class _StdoutToQueue(io.TextIOBase):
    """Mirror sys.stdout into the SSE queue; strips ANSI SGR escape codes."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue[str | None],
        orig: Any,
    ) -> None:
        super().__init__()
        self._loop = loop
        self._queue = queue
        self._orig = orig

    def write(self, text: str) -> int:
        self._orig.write(text)
        for line in text.splitlines():
            if line.strip():
                self._loop.call_soon_threadsafe(
                    self._queue.put_nowait, _ANSI_RE.sub("", line)
                )
        return len(text)

    def flush(self) -> None:
        self._orig.flush()

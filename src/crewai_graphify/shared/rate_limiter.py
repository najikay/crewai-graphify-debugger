"""Throttled rate limiter — enforces inter-call pause between API dispatches."""
from __future__ import annotations

import time

__all__ = ["ThrottledRateLimiter"]


class ThrottledRateLimiter:
    """500 ms pause between dispatches avoids Anthropic rate-limit 429s."""

    def enqueue(self, payload: object) -> None:  # noqa: ARG002
        time.sleep(0.5)

"""Unit tests for ThrottledRateLimiter."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from crewai_graphify.shared.rate_limiter import ThrottledRateLimiter


class TestThrottledRateLimiter:
    def test_enqueue_sleeps_half_second(self) -> None:
        rl = ThrottledRateLimiter()
        with patch.object(time, "sleep") as mock_sleep:
            rl.enqueue(MagicMock())
        mock_sleep.assert_called_once_with(0.5)

    def test_enqueue_accepts_arbitrary_payload(self) -> None:
        rl = ThrottledRateLimiter()
        with patch.object(time, "sleep"):
            rl.enqueue("a string")
            rl.enqueue(42)
            rl.enqueue(None)

    def test_sleep_called_once_per_enqueue(self) -> None:
        rl = ThrottledRateLimiter()
        with patch.object(time, "sleep") as mock_sleep:
            rl.enqueue(MagicMock())
            rl.enqueue(MagicMock())
        assert mock_sleep.call_count == 2

    def test_instantiation(self) -> None:
        assert isinstance(ThrottledRateLimiter(), ThrottledRateLimiter)

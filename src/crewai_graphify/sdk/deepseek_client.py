"""DeepSeek SDK adapter — lets DeepSeek runs flow through the ApiGatekeeper.

Implements the gatekeeper's ``_ClientProtocol`` (``create_message``) using the
DeepSeek OpenAI-compatible API via litellm.  Because every DeepSeek call now
returns an ``LLMResponse`` with real token usage, ``BudgetTracker`` records and
prices DeepSeek runs exactly like the Anthropic path — closing the telemetry gap.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from crewai_graphify.models.llm import LLMPayload, LLMResponse, UsageStats

__all__ = ["DeepSeekAdapter"]

_VALID_KEYS = frozenset({"role", "content"})


def _default_completion(**kwargs: Any) -> Any:  # pragma: no cover - real network boundary
    """Lazily import litellm so unit tests stay offline and imports stay cheap."""
    import litellm

    return litellm.completion(**kwargs)


class DeepSeekAdapter:
    """Gatekeeper ``_client`` adapter that dispatches a payload to DeepSeek.

    Args:
        completion: Injected ``litellm.completion``-style callable. Defaults to
            the real litellm call; tests pass a stub so no network is hit.
    """

    def __init__(self, completion: Callable[..., Any] | None = None) -> None:
        self._completion = completion or _default_completion

    def create_message(self, payload: LLMPayload) -> LLMResponse:
        """Dispatch *payload* to DeepSeek and wrap the reply as an LLMResponse."""
        messages = [{"role": "system", "content": payload.system}]
        messages += [
            {k: v for k, v in m.items() if k in _VALID_KEYS} for m in payload.messages
        ]
        resp = self._completion(
            model=f"deepseek/{payload.model}",
            messages=messages,
            max_tokens=payload.max_tokens,
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        )
        choice = resp.choices[0]
        return LLMResponse(
            id=str(getattr(resp, "id", "deepseek")),
            model=payload.model,
            content=choice.message.content or "",
            usage=UsageStats(
                input_tokens=int(resp.usage.prompt_tokens),
                output_tokens=int(resp.usage.completion_tokens),
            ),
            stop_reason=getattr(choice, "finish_reason", "stop") or "stop",
        )

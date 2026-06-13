"""CrewAI Custom LLM — routes all calls through ApiGatekeeper for telemetry.

``ClaudeClient`` is the only permitted entrypoint for Anthropic SDK calls.
Direct ``anthropic.Anthropic()`` usage outside this file is forbidden.
"""
from __future__ import annotations

from typing import Any

from crewai import BaseLLM
from pydantic import model_validator

from crewai_graphify.models.llm import LLMPayload
from crewai_graphify.shared.gatekeeper import ApiGatekeeper

__all__ = ["ClaudeClient"]

_CHARS_PER_TOKEN = 4
_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_SYSTEM = "You are an expert Python debugger."
_DEFAULT_MAX_TOKENS = 1024


class ClaudeClient(BaseLLM):
    """CrewAI-compatible LLM that routes every call through ApiGatekeeper."""

    model: str = _DEFAULT_MODEL  # default so ClaudeClient() needs no arguments
    llm_type: str = "claude-gatekeeper"
    system_prompt: str = _DEFAULT_SYSTEM

    @model_validator(mode="before")
    @classmethod
    def _inject_default_model(cls, data: Any) -> Any:
        """Provide a default model so ``ClaudeClient()`` needs no arguments."""
        if isinstance(data, dict) and not data.get("model"):
            data = {**data, "model": _DEFAULT_MODEL}
        return data

    def call(  # type: ignore[override]
        self,
        messages: str | list[dict[str, Any]],
        tools: list[Any] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: Any | None = None,
    ) -> str:
        """Estimate tokens, build payload, and route through ApiGatekeeper."""
        if isinstance(messages, str):
            prompt = messages
            msg_list: list[dict[str, Any]] = [{"role": "user", "content": messages}]
        else:
            prompt = str(messages[-1].get("content", "")) if messages else ""
            msg_list = [dict(m) for m in messages]
        max_tok = int(self.max_tokens) if self.max_tokens else _DEFAULT_MAX_TOKENS
        payload = LLMPayload(
            model=self.model,
            system=self.system_prompt,
            messages=msg_list,
            max_tokens=max_tok,
            input_token_estimate=max(1, len(prompt) // _CHARS_PER_TOKEN),
        )
        return ApiGatekeeper().call(payload).content

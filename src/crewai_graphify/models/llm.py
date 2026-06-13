"""Pydantic models for LLM request payloads, responses, and pricing data.

These are the shared data contracts used by the API Gatekeeper, Budget
Tracker, and all agent tool code.  All models are frozen (immutable) so
that accidental mutation is caught at runtime.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "LLMPayload",
    "LLMResponse",
    "ModelPricing",
    "UsageStats",
]


class LLMPayload(BaseModel, frozen=True):
    """Encapsulates everything required for one Anthropic messages.create() call.

    ``input_token_estimate`` is a *caller-supplied* conservative upper-bound
    on the number of input tokens.  It is used exclusively for pre-call budget
    gating — the actual billed count comes from the API response.
    """

    model: str
    system: str
    messages: list[dict[str, Any]]
    max_tokens: int = Field(default=1024, gt=0)
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    input_token_estimate: int = Field(
        default=2048,
        gt=0,
        description="Conservative over-estimate of prompt tokens for budget gating.",
    )
    use_cache: bool = Field(
        default=True,
        description="Whether to request prompt-prefix caching on the system prompt.",
    )

    @field_validator("model")
    @classmethod
    def model_must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("model must not be an empty string")
        return v

    @field_validator("messages")
    @classmethod
    def messages_must_not_be_empty(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not v:
            raise ValueError("messages list must contain at least one entry")
        return v


class UsageStats(BaseModel, frozen=True):
    """Token-usage statistics as reported by the Anthropic API response."""

    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


class LLMResponse(BaseModel, frozen=True):
    """Typed envelope wrapping the raw Anthropic messages.create() response."""

    id: str
    model: str
    content: str
    usage: UsageStats
    stop_reason: str


class ModelPricing(BaseModel, frozen=True):
    """Per-model pricing loaded from ``config/budget_limits.json``.

    All rates are expressed in USD per one million tokens.
    ``local_cost_multiplier`` is a region/tier correction factor (default 1.0).
    """

    input_per_million_tokens_usd: float = Field(gt=0)
    output_per_million_tokens_usd: float = Field(gt=0)
    cache_write_per_million_tokens_usd: float = Field(gt=0)
    cache_read_per_million_tokens_usd: float = Field(gt=0)
    local_cost_multiplier: float = Field(default=1.0, gt=0)

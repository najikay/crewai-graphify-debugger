"""Shared pytest fixtures for the shared/ unit-test suite.

Provides the singleton reset, typed model instances, and three protocol mocks
(client, budget_tracker, rate_limiter) that are composed into a ready-to-use
``gk`` fixture by every test module in this directory.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from crewai_graphify.models.llm import LLMPayload, LLMResponse, ModelPricing, UsageStats
from crewai_graphify.shared.gatekeeper import ApiGatekeeper

# ---------------------------------------------------------------------------
# Singleton hygiene — runs automatically before AND after every test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_gatekeeper_singleton() -> None:  # type: ignore[return]
    """Wipe the singleton so each test starts with a clean slate."""
    ApiGatekeeper._instance = None
    yield
    ApiGatekeeper._instance = None


# ---------------------------------------------------------------------------
# Typed model fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def pricing() -> ModelPricing:
    """sonnet-4-6 pricing; local_cost_multiplier defaults to 1.0."""
    return ModelPricing(
        input_per_million_tokens_usd=3.00,
        output_per_million_tokens_usd=15.00,
        cache_write_per_million_tokens_usd=3.75,
        cache_read_per_million_tokens_usd=0.30,
    )


@pytest.fixture()
def payload() -> LLMPayload:
    """A minimal valid payload: 1 000 estimated input tokens, 512 max output."""
    return LLMPayload(
        model="claude-sonnet-4-6",
        system="You are an expert Python debugger.",
        messages=[{"role": "user", "content": "Find the root cause."}],
        max_tokens=512,
        input_token_estimate=1_000,
    )


@pytest.fixture()
def llm_response() -> LLMResponse:
    return LLMResponse(
        id="msg_abc123",
        model="claude-sonnet-4-6",
        content="Root cause: utils.py line 42.",
        usage=UsageStats(input_tokens=980, output_tokens=41),
        stop_reason="end_turn",
    )


# ---------------------------------------------------------------------------
# Protocol mocks
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_client(llm_response: LLMResponse) -> MagicMock:
    m = MagicMock()
    m.create_message.return_value = llm_response
    return m


@pytest.fixture()
def mock_budget_tracker(pricing: ModelPricing) -> MagicMock:
    m = MagicMock()
    m.pricing_for.return_value = pricing
    m.get_session_ledger.return_value = MagicMock(
        model_dump=lambda: {"total_cost_usd": 0.0, "total_transactions": 0}
    )
    return m


@pytest.fixture()
def mock_rate_limiter() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# Composed gatekeeper fixture — initialized and ready to call
# ---------------------------------------------------------------------------


@pytest.fixture()
def gk(
    mock_client: MagicMock,
    mock_budget_tracker: MagicMock,
    mock_rate_limiter: MagicMock,
) -> ApiGatekeeper:
    instance = ApiGatekeeper()
    instance.initialize(mock_client, mock_budget_tracker, mock_rate_limiter)
    return instance

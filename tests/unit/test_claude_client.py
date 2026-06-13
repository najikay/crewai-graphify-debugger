"""Unit tests for ClaudeClient."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from crewai_graphify.models.llm import LLMPayload, LLMResponse, UsageStats
from crewai_graphify.sdk.claude_client import ClaudeClient
from crewai_graphify.shared.gatekeeper import ApiGatekeeper


@pytest.fixture(autouse=True)
def reset_singleton() -> None:  # type: ignore[return]
    ApiGatekeeper._instance = None
    yield
    ApiGatekeeper._instance = None


@pytest.fixture()
def llm_response() -> LLMResponse:
    return LLMResponse(
        id="msg_1",
        model="claude-sonnet-4-6",
        content="Root cause: line 29.",
        usage=UsageStats(input_tokens=100, output_tokens=10),
        stop_reason="end_turn",
    )


@pytest.fixture()
def client() -> ClaudeClient:
    return ClaudeClient()


class TestInit:
    def test_default_model(self, client: ClaudeClient) -> None:
        assert client.model == "claude-sonnet-4-6"

    def test_llm_type(self, client: ClaudeClient) -> None:
        assert client.llm_type == "claude-gatekeeper"

    def test_custom_model(self) -> None:
        c = ClaudeClient(model="claude-opus-4-6")
        assert c.model == "claude-opus-4-6"


class TestCallWithString:
    def test_routes_through_gatekeeper(
        self, client: ClaudeClient, llm_response: LLMResponse
    ) -> None:
        with patch.object(ApiGatekeeper, "call", return_value=llm_response) as mock_call:
            result = client.call("Fix the bug.")
            mock_call.assert_called_once()
            assert result == "Root cause: line 29."

    def test_returns_content_string(
        self, client: ClaudeClient, llm_response: LLMResponse
    ) -> None:
        with patch.object(ApiGatekeeper, "call", return_value=llm_response):
            assert client.call("prompt") == llm_response.content

    def test_token_estimate_from_length(
        self, client: ClaudeClient, llm_response: LLMResponse
    ) -> None:
        with patch.object(ApiGatekeeper, "call", return_value=llm_response) as mock_call:
            client.call("x" * 400)  # 400 chars / 4 = 100 tokens
            payload: LLMPayload = mock_call.call_args[0][0]
            assert payload.input_token_estimate == 100

    def test_minimum_estimate_is_one(
        self, client: ClaudeClient, llm_response: LLMResponse
    ) -> None:
        with patch.object(ApiGatekeeper, "call", return_value=llm_response) as mock_call:
            client.call("")
            payload: LLMPayload = mock_call.call_args[0][0]
            assert payload.input_token_estimate >= 1

    def test_payload_model_matches_client(
        self, client: ClaudeClient, llm_response: LLMResponse
    ) -> None:
        with patch.object(ApiGatekeeper, "call", return_value=llm_response) as mock_call:
            client.call("test")
            payload: LLMPayload = mock_call.call_args[0][0]
            assert payload.model == client.model


class TestCallWithMessages:
    def test_list_of_messages(
        self, client: ClaudeClient, llm_response: LLMResponse
    ) -> None:
        msgs = [{"role": "user", "content": "Describe the bug"}]
        with patch.object(ApiGatekeeper, "call", return_value=llm_response):
            assert client.call(msgs) == llm_response.content

    def test_token_estimate_from_last_message(
        self, client: ClaudeClient, llm_response: LLMResponse
    ) -> None:
        msgs = [
            {"role": "system", "content": "context"},
            {"role": "user", "content": "x" * 400},
        ]
        with patch.object(ApiGatekeeper, "call", return_value=llm_response) as mock_call:
            client.call(msgs)
            payload: LLMPayload = mock_call.call_args[0][0]
            assert payload.input_token_estimate == 100

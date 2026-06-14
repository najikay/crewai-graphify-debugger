"""Unit tests for the multi-provider LLM factory in crew.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from crewai_graphify.agents.crew import _make_llm

_CLAUDE = "crewai_graphify.agents.crew.ClaudeClient"
_CREWLLM = "crewai_graphify.agents.crew.LLM"


class TestMakeLlm:
    def test_default_returns_claude_client(self) -> None:
        """With no LLM_PROVIDER set, _make_llm() instantiates ClaudeClient."""
        with patch.dict("os.environ", {"LLM_PROVIDER": "claude"}), patch(_CLAUDE) as mock:
            result = _make_llm()
        assert result is mock.return_value

    def test_deepseek_provider_returns_crew_llm(self) -> None:
        """LLM_PROVIDER=deepseek routes to CrewLLM instead of ClaudeClient."""
        with patch.dict("os.environ", {"LLM_PROVIDER": "deepseek"}), patch(_CREWLLM) as mock:
            result = _make_llm()
        assert result is mock.return_value

    def test_deepseek_model_from_default_model_env(self) -> None:
        """DEFAULT_MODEL env var is embedded in the CrewLLM model string."""
        env = {"LLM_PROVIDER": "deepseek", "DEFAULT_MODEL": "deepseek-coder"}
        with patch.dict("os.environ", env), patch(_CREWLLM) as mock:
            _make_llm()
        assert "deepseek-coder" in mock.call_args.kwargs["model"]

    def test_deepseek_fallback_model_when_default_model_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Uses 'deepseek-chat' when DEFAULT_MODEL is not in the environment."""
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")
        monkeypatch.delenv("DEFAULT_MODEL", raising=False)
        with patch(_CREWLLM) as mock:
            _make_llm()
        assert "deepseek-chat" in mock.call_args.kwargs["model"]

    def test_unknown_provider_falls_back_to_claude(self) -> None:
        """Any unrecognised LLM_PROVIDER value falls back to ClaudeClient."""
        with patch.dict("os.environ", {"LLM_PROVIDER": "openai"}), patch(_CLAUDE) as mock:
            result = _make_llm()
        assert result is mock.return_value

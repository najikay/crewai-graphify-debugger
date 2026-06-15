"""Unit tests for the gatekept multi-provider LLM factory in crew.py.

Both providers now return a GatekeeperLLM so every call routes through the
ApiGatekeeper (budget + telemetry) — only the payload model differs.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from crewai_graphify.agents.crew import _make_llm
from crewai_graphify.sdk.claude_client import GatekeeperLLM

_GK = "crewai_graphify.agents.crew.GatekeeperLLM"


class TestMakeLlm:
    def test_default_returns_gatekeeper_llm(self) -> None:
        with patch.dict("os.environ", {"LLM_PROVIDER": "claude"}), patch(_GK) as mock:
            result = _make_llm()
        assert result is mock.return_value

    def test_claude_path_uses_builtin_default_model(self) -> None:
        """Claude branch constructs GatekeeperLLM() with no explicit model kwarg."""
        with patch.dict("os.environ", {"LLM_PROVIDER": "claude"}), patch(_GK) as mock:
            _make_llm()
        assert "model" not in mock.call_args.kwargs

    def test_deepseek_returns_gatekeeper_llm(self) -> None:
        with patch.dict("os.environ", {"LLM_PROVIDER": "deepseek"}), patch(_GK) as mock:
            result = _make_llm()
        assert result is mock.return_value

    def test_deepseek_model_from_default_model_env(self) -> None:
        env = {"LLM_PROVIDER": "deepseek", "DEFAULT_MODEL": "deepseek-coder"}
        with patch.dict("os.environ", env), patch(_GK) as mock:
            _make_llm()
        assert mock.call_args.kwargs["model"] == "deepseek-coder"

    def test_deepseek_fallback_model_when_default_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")
        monkeypatch.delenv("DEFAULT_MODEL", raising=False)
        with patch(_GK) as mock:
            _make_llm()
        assert mock.call_args.kwargs["model"] == "deepseek-chat"

    def test_unknown_provider_falls_back_to_default(self) -> None:
        with patch.dict("os.environ", {"LLM_PROVIDER": "openai"}), patch(_GK) as mock:
            result = _make_llm()
        assert result is mock.return_value

    def test_deepseek_builds_real_gatekept_llm_carrying_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unmocked: deepseek yields a real GatekeeperLLM with the model set."""
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")
        monkeypatch.setenv("DEFAULT_MODEL", "deepseek-chat")
        llm = _make_llm()
        assert isinstance(llm, GatekeeperLLM)
        assert llm.model == "deepseek-chat"

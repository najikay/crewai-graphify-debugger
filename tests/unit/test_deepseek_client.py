"""Unit tests for the DeepSeek gatekeeper adapter (sdk/deepseek_client.py)."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from crewai_graphify.models.llm import LLMPayload
from crewai_graphify.sdk.deepseek_client import DeepSeekAdapter, _default_completion


def _fake_response(content: str | None = "hello", pin: int = 12, pout: int = 5) -> Any:
    return SimpleNamespace(
        id="ds-1",
        choices=[SimpleNamespace(
            message=SimpleNamespace(content=content),
            finish_reason="stop",
        )],
        usage=SimpleNamespace(prompt_tokens=pin, completion_tokens=pout),
    )


def _payload(model: str = "deepseek-chat") -> LLMPayload:
    return LLMPayload(model=model, system="sys",
                      messages=[{"role": "user", "content": "hi"}], max_tokens=64)


class TestDeepSeekAdapter:
    def test_default_adapter_uses_litellm_completion(self) -> None:
        """Constructing without an override wires the lazy litellm callable."""
        assert DeepSeekAdapter()._completion is _default_completion

    def test_returns_response_content(self) -> None:
        adapter = DeepSeekAdapter(completion=lambda **k: _fake_response(content="patched!"))
        assert adapter.create_message(_payload()).content == "patched!"

    def test_maps_token_usage_for_budget(self) -> None:
        adapter = DeepSeekAdapter(completion=lambda **k: _fake_response(pin=100, pout=20))
        resp = adapter.create_message(_payload())
        assert resp.usage.input_tokens == 100 and resp.usage.output_tokens == 20

    def test_prefixes_model_with_provider(self) -> None:
        captured: dict[str, Any] = {}

        def completion(**kwargs: Any) -> Any:
            captured.update(kwargs)
            return _fake_response()

        DeepSeekAdapter(completion=completion).create_message(_payload("deepseek-chat"))
        assert captured["model"] == "deepseek/deepseek-chat"

    def test_prepends_system_message(self) -> None:
        captured: dict[str, Any] = {}

        def completion(**kwargs: Any) -> Any:
            captured.update(kwargs)
            return _fake_response()

        DeepSeekAdapter(completion=completion).create_message(_payload())
        assert captured["messages"][0] == {"role": "system", "content": "sys"}

    def test_strips_non_standard_message_keys(self) -> None:
        captured: dict[str, Any] = {}

        def completion(**kwargs: Any) -> Any:
            captured.update(kwargs)
            return _fake_response()

        payload = LLMPayload(model="deepseek-chat", system="s",
                             messages=[{"role": "user", "content": "hi", "extra": "x"}],
                             max_tokens=32)
        DeepSeekAdapter(completion=completion).create_message(payload)
        assert "extra" not in captured["messages"][1]

    def test_none_content_falls_back_to_empty(self) -> None:
        adapter = DeepSeekAdapter(completion=lambda **k: _fake_response(content=None))
        assert adapter.create_message(_payload()).content == ""

    def test_response_model_is_bare_model_name(self) -> None:
        adapter = DeepSeekAdapter(completion=lambda **k: _fake_response())
        assert adapter.create_message(_payload("deepseek-chat")).model == "deepseek-chat"

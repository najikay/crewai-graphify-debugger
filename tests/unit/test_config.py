"""Unit tests for AppConfig (config manager)."""
from __future__ import annotations

from pathlib import Path

import pytest

from crewai_graphify.models.llm import ModelPricing
from crewai_graphify.shared.config import AppConfig

CONFIG_DIR = Path("config")


@pytest.fixture()
def cfg() -> AppConfig:
    return AppConfig.load(CONFIG_DIR)


class TestLoad:
    def test_loads_without_error(self, cfg: AppConfig) -> None:
        assert cfg is not None

    def test_loads_from_custom_dir(self, tmp_path: Path) -> None:
        budget = (
            '{"model_pricing": {}, "default_ceiling_usd": 1.5,'
            ' "warning_threshold_pct": 80, "local_cost_multiplier": 1.0}'
        )
        rate = (
            '{"requests_per_minute": 10, "tokens_per_minute": 5000,'
            ' "retry_backoff_seconds": [1], "tokens_per_day": 100000}'
        )
        (tmp_path / "budget_limits.json").write_text(budget)
        (tmp_path / "rate_limits.json").write_text(rate)
        c = AppConfig.load(tmp_path)
        assert c.ceiling_usd == pytest.approx(1.5)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            AppConfig.load(tmp_path)


class TestPricingFor:
    def test_known_model_returns_pricing(self, cfg: AppConfig) -> None:
        p = cfg.pricing_for("claude-sonnet-4-6")
        assert isinstance(p, ModelPricing)
        assert p.input_per_million_tokens_usd > 0

    def test_unknown_model_raises_key_error(self, cfg: AppConfig) -> None:
        with pytest.raises(KeyError, match="unknown-model"):
            cfg.pricing_for("unknown-model")

    def test_all_three_models_present(self, cfg: AppConfig) -> None:
        for m in ("claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"):
            assert cfg.pricing_for(m) is not None

    def test_deepseek_chat_is_priced(self, cfg: AppConfig) -> None:
        """DeepSeek must be priced so the gatekeeper can budget/track its runs."""
        p = cfg.pricing_for("deepseek-chat")
        assert p.input_per_million_tokens_usd > 0
        assert p.output_per_million_tokens_usd > 0

    def test_local_cost_multiplier_applied(self, cfg: AppConfig) -> None:
        p = cfg.pricing_for("claude-sonnet-4-6")
        assert p.local_cost_multiplier == pytest.approx(1.0)

    def test_output_more_expensive_than_input(self, cfg: AppConfig) -> None:
        p = cfg.pricing_for("claude-sonnet-4-6")
        assert p.output_per_million_tokens_usd > p.input_per_million_tokens_usd


class TestProperties:
    def test_ceiling_usd_is_two(self, cfg: AppConfig) -> None:
        assert cfg.ceiling_usd == pytest.approx(2.0)

    def test_warning_threshold_is_ninety(self, cfg: AppConfig) -> None:
        assert cfg.warning_threshold_pct == pytest.approx(90.0)

    def test_requests_per_minute_positive(self, cfg: AppConfig) -> None:
        assert cfg.requests_per_minute > 0

    def test_tokens_per_minute_positive(self, cfg: AppConfig) -> None:
        assert cfg.tokens_per_minute > 0

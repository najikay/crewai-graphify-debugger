"""Config Manager — loads JSON configuration from the config/ directory."""
from __future__ import annotations

import json
from pathlib import Path

from crewai_graphify.models.llm import ModelPricing

__all__ = ["AppConfig"]

_CONFIG_DIR = Path("config")


class AppConfig:
    """Lightweight config manager.  Instantiate via ``AppConfig.load()``."""

    def __init__(
        self,
        models: dict[str, ModelPricing],
        ceiling_usd: float,
        warning_threshold_pct: float,
        requests_per_minute: int,
        tokens_per_minute: int,
    ) -> None:
        self._models = models
        self._ceiling_usd = ceiling_usd
        self._warning_threshold_pct = warning_threshold_pct
        self._requests_per_minute = requests_per_minute
        self._tokens_per_minute = tokens_per_minute

    @classmethod
    def load(cls, config_dir: Path | None = None) -> AppConfig:
        """Load from *config_dir* (default: ``config/``)."""
        d = config_dir or _CONFIG_DIR
        budget = json.loads((d / "budget_limits.json").read_text(encoding="utf-8"))
        rate = json.loads((d / "rate_limits.json").read_text(encoding="utf-8"))
        mult = float(budget.get("local_cost_multiplier", 1.0))
        models = {
            name: ModelPricing(**{**pricing, "local_cost_multiplier": mult})
            for name, pricing in budget["model_pricing"].items()
        }
        return cls(
            models=models,
            ceiling_usd=float(budget["default_ceiling_usd"]),
            warning_threshold_pct=float(budget["warning_threshold_pct"]),
            requests_per_minute=int(rate["requests_per_minute"]),
            tokens_per_minute=int(rate["tokens_per_minute"]),
        )

    def pricing_for(self, model: str) -> ModelPricing:
        """Return ``ModelPricing`` for *model*, or raise ``KeyError``."""
        try:
            return self._models[model]
        except KeyError:
            raise KeyError(f"Unknown model: {model!r}") from None

    @property
    def ceiling_usd(self) -> float:
        return self._ceiling_usd

    @property
    def warning_threshold_pct(self) -> float:
        return self._warning_threshold_pct

    @property
    def requests_per_minute(self) -> int:
        return self._requests_per_minute

    @property
    def tokens_per_minute(self) -> int:
        return self._tokens_per_minute

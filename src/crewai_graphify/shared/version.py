"""Application version constant and model allow-list validator.

``VersionValidator`` is used by the API Gatekeeper to reject calls that
reference model IDs not present in the approved pricing table.  This prevents
accidental use of unknown (and potentially unpriced) models.
"""

from __future__ import annotations

__all__ = ["APP_VERSION", "UnknownModelError", "VersionValidator"]

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

APP_VERSION: str = "1.0.0"
"""Canonical application version string.  Bump this on every release."""

# ---------------------------------------------------------------------------
# Default allow-list
# This list is the fallback when no external config is provided.  The
# gatekeeper loads the authoritative list from budget_limits.json at runtime.
# ---------------------------------------------------------------------------

_DEFAULT_ALLOWED_MODELS: frozenset[str] = frozenset(
    {
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    }
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class UnknownModelError(ValueError):
    """Raised when a requested model ID is not in the approved allow-list.

    Attributes:
        model_id: The model string that was rejected.
        allowed_models: The sorted list of currently allowed model IDs.
    """

    def __init__(self, model_id: str, allowed_models: frozenset[str]) -> None:
        self.model_id = model_id
        self.allowed_models = allowed_models
        super().__init__(
            f"Model '{model_id}' is not in the approved allow-list. "
            f"Allowed models: {sorted(allowed_models)}"
        )


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class VersionValidator:
    """Validates that a requested LLM model engine is on the approved list.

    Args:
        allowed_models: Override the default allow-list.  Pass ``None`` to use
            the built-in defaults (``_DEFAULT_ALLOWED_MODELS``).

    Example::

        validator = VersionValidator()
        validator.validate_model("claude-sonnet-4-6")   # returns True
        validator.validate_model("gpt-4o")              # raises UnknownModelError
    """

    def __init__(
        self,
        allowed_models: frozenset[str] | None = None,
    ) -> None:
        self._allowed_models: frozenset[str] = (
            allowed_models if allowed_models is not None else _DEFAULT_ALLOWED_MODELS
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_model(self, model_id: str) -> bool:
        """Return ``True`` if *model_id* is approved; raise otherwise.

        Args:
            model_id: The model string to validate (e.g. ``"claude-sonnet-4-6"``).

        Returns:
            ``True`` — always, on success.

        Raises:
            UnknownModelError: When *model_id* is not in the allow-list.
        """
        if model_id not in self._allowed_models:
            raise UnknownModelError(model_id, self._allowed_models)
        return True

    @property
    def allowed_models(self) -> frozenset[str]:
        """Read-only view of the current allow-list."""
        return self._allowed_models

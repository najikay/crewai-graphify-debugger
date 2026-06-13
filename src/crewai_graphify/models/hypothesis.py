"""Pydantic models for root-cause hypotheses, file slices, and code diffs."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

__all__ = ["Diff", "FileSlice", "Hypothesis"]


class FileSlice(BaseModel, frozen=True):
    """A bounded excerpt of a source file, identified by line range."""

    file: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content: str

    @model_validator(mode="after")
    def _end_gte_start(self) -> FileSlice:
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self


class Diff(BaseModel, frozen=True):
    """A minimal two-sided code change: original → new."""

    original_code: str
    new_code: str


class Hypothesis(BaseModel, frozen=True):
    """Root-cause hypothesis produced by the Reasoner agent.

    ``confidence_score`` in [0, 1]; values below 0.7 signal that the Patcher
    should skip applying the diff and the Reader should re-read more context.
    """

    root_cause: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    requested_diff: Diff

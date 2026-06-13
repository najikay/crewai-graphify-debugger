"""Unit tests for hypothesis Pydantic models (FileSlice, Diff, Hypothesis)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from crewai_graphify.models.hypothesis import Diff, FileSlice, Hypothesis


class TestFileSlice:
    def test_valid_construction(self) -> None:
        fs = FileSlice(file="main.py", start_line=1, end_line=5, content="code")
        assert fs.file == "main.py" and fs.content == "code"

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValidationError):
            FileSlice(file="f.py", start_line=5, end_line=3, content="x")

    def test_start_line_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            FileSlice(file="f.py", start_line=0, end_line=1, content="x")

    def test_negative_start_raises(self) -> None:
        with pytest.raises(ValidationError):
            FileSlice(file="f.py", start_line=-1, end_line=1, content="x")

    def test_equal_start_end_valid(self) -> None:
        fs = FileSlice(file="f.py", start_line=3, end_line=3, content="x")
        assert fs.start_line == fs.end_line

    def test_frozen_immutable(self) -> None:
        fs = FileSlice(file="f.py", start_line=1, end_line=2, content="x")
        with pytest.raises(ValidationError):
            fs.file = "other.py"  # type: ignore[misc]

    def test_stores_all_fields(self) -> None:
        fs = FileSlice(file="a.py", start_line=10, end_line=20, content="body")
        assert fs.start_line == 10 and fs.end_line == 20


class TestDiff:
    def test_valid_construction(self) -> None:
        d = Diff(original_code="x = 1", new_code="x = 2")
        assert d.original_code == "x = 1" and d.new_code == "x = 2"

    def test_empty_strings_allowed(self) -> None:
        d = Diff(original_code="", new_code="")
        assert d.original_code == ""

    def test_frozen_immutable(self) -> None:
        d = Diff(original_code="a", new_code="b")
        with pytest.raises(ValidationError):
            d.new_code = "c"  # type: ignore[misc]


class TestHypothesis:
    def _diff(self) -> Diff:
        return Diff(original_code="old", new_code="new")

    def test_valid_construction(self) -> None:
        h = Hypothesis(root_cause="NameError", confidence_score=0.9, requested_diff=self._diff())
        assert h.root_cause == "NameError"
        assert h.confidence_score == pytest.approx(0.9)

    def test_confidence_below_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            Hypothesis(root_cause="x", confidence_score=-0.1, requested_diff=self._diff())

    def test_confidence_above_one_raises(self) -> None:
        with pytest.raises(ValidationError):
            Hypothesis(root_cause="x", confidence_score=1.1, requested_diff=self._diff())

    def test_confidence_zero_valid(self) -> None:
        h = Hypothesis(root_cause="x", confidence_score=0.0, requested_diff=self._diff())
        assert h.confidence_score == pytest.approx(0.0)

    def test_confidence_one_valid(self) -> None:
        h = Hypothesis(root_cause="x", confidence_score=1.0, requested_diff=self._diff())
        assert h.confidence_score == pytest.approx(1.0)

    def test_frozen_immutable(self) -> None:
        h = Hypothesis(root_cause="x", confidence_score=0.5, requested_diff=self._diff())
        with pytest.raises(ValidationError):
            h.root_cause = "y"  # type: ignore[misc]

    def test_low_confidence_is_below_threshold(self) -> None:
        """confidence_score < 0.7 signals re-read-needed to the Patcher."""
        h = Hypothesis(root_cause="uncertain", confidence_score=0.6, requested_diff=self._diff())
        assert h.confidence_score < 0.7

    def test_high_confidence_meets_threshold(self) -> None:
        h = Hypothesis(root_cause="certain", confidence_score=0.7, requested_diff=self._diff())
        assert h.confidence_score >= 0.7

    def test_requested_diff_accessible(self) -> None:
        d = self._diff()
        h = Hypothesis(root_cause="x", confidence_score=0.8, requested_diff=d)
        assert h.requested_diff.original_code == "old"
        assert h.requested_diff.new_code == "new"

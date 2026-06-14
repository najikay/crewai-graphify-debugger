"""Unit tests for Task factory functions in agents/tasks.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from crewai_graphify.agents.tasks import navigator_task, patcher_task, reader_task, reasoner_task


class TestReaderTask:
    def test_no_hint_omits_retry_text(self) -> None:
        """Default call must not inject any retry instruction into the description."""
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            reader_task(MagicMock(), MagicMock())
            assert "Previous read" not in mock_task.call_args.kwargs["description"]

    def test_hint_appended_to_description(self) -> None:
        """A non-empty retry_hint must appear at the end of the task description."""
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            reader_task(MagicMock(), MagicMock(), retry_hint="expand lines 15-50")
            assert "expand lines 15-50" in mock_task.call_args.kwargs["description"]

    def test_hint_preceded_by_double_newline(self) -> None:
        """The hint must be visually separated from the base description."""
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            reader_task(MagicMock(), MagicMock(), retry_hint="MUST expand")
            assert "\n\nMUST expand" in mock_task.call_args.kwargs["description"]

    def test_returns_task_instance(self) -> None:
        """reader_task must return the Task mock's return value."""
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            result = reader_task(MagicMock(), MagicMock())
            assert result is mock_task.return_value


class TestReasonerTask:
    def test_no_hint_omits_retry_text(self) -> None:
        """Default call must not inject any retry instruction."""
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            reasoner_task(MagicMock(), MagicMock())
            assert "Previous read" not in mock_task.call_args.kwargs["description"]

    def test_hint_appended_to_description(self) -> None:
        """A non-empty retry_hint must appear in the reasoner task description."""
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            reasoner_task(MagicMock(), MagicMock(), retry_hint="must expand range")
            assert "must expand range" in mock_task.call_args.kwargs["description"]

    def test_returns_task_instance(self) -> None:
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            result = reasoner_task(MagicMock(), MagicMock())
            assert result is mock_task.return_value

    def test_description_requires_target_file_key(self) -> None:
        """Reasoner output schema must demand an explicit target_file field."""
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            reasoner_task(MagicMock(), MagicMock())
            assert "target_file" in mock_task.call_args.kwargs["description"]


class TestNavigatorTask:
    def test_returns_task_instance(self) -> None:
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            result = navigator_task(MagicMock())
            assert result is mock_task.return_value

    def test_description_forbids_guessing(self) -> None:
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            navigator_task(MagicMock())
            assert "DO NOT invent" in mock_task.call_args.kwargs["description"]

    def test_description_contains_hot_md_template(self) -> None:
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            navigator_task(MagicMock())
            assert "{hot_md_content}" in mock_task.call_args.kwargs["description"]


class TestPatcherTask:
    def test_returns_task_instance(self) -> None:
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            result = patcher_task(MagicMock(), MagicMock())
            assert result is mock_task.return_value

    def test_context_limited_to_reasoner_only(self) -> None:
        """Patcher context must contain exactly the reasoner task (no history leak)."""
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            reason = MagicMock()
            patcher_task(MagicMock(), reason)
            assert mock_task.call_args.kwargs["context"] == [reason]

    def test_description_uses_target_file(self) -> None:
        """Patcher must take the path from the Hypothesis target_file field."""
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            patcher_task(MagicMock(), MagicMock())
            assert "target_file" in mock_task.call_args.kwargs["description"]

    def test_description_forbids_guessing_paths(self) -> None:
        """Patcher must be explicitly forbidden from inventing/guessing paths."""
        with patch("crewai_graphify.agents.tasks.Task") as mock_task:
            patcher_task(MagicMock(), MagicMock())
            assert "STRICTLY FORBIDDEN" in mock_task.call_args.kwargs["description"]

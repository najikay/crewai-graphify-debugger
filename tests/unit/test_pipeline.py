"""Unit tests for build_crew() in agents/pipeline.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from crewai import Process

from crewai_graphify.agents.pipeline import build_crew

_PATCHES = [
    "crewai_graphify.agents.pipeline.navigator_agent",
    "crewai_graphify.agents.pipeline.reader_agent",
    "crewai_graphify.agents.pipeline.reasoner_agent",
    "crewai_graphify.agents.pipeline.patcher_agent",
    "crewai_graphify.agents.pipeline.navigator_task",
    "crewai_graphify.agents.pipeline.reader_task",
    "crewai_graphify.agents.pipeline.reasoner_task",
    "crewai_graphify.agents.pipeline.patcher_task",
    "crewai_graphify.agents.pipeline.Crew",
]


@pytest.fixture()
def mocked_crew():  # type: ignore[no-untyped-def]
    """Start all pipeline patches; yield a name→mock dict; stop on teardown."""
    patchers = [patch(p) for p in _PATCHES]
    mocks = [p.start() for p in patchers]
    names = [
        "nav_agent", "rdr_agent", "rsn_agent", "ptr_agent",
        "nav_task", "rdr_task", "rsn_task", "ptr_task", "Crew",
    ]
    yield dict(zip(names, mocks, strict=True))
    for p in patchers:
        p.stop()


class TestBuildCrew:
    def test_returns_crew_instance(self, mocked_crew) -> None:  # type: ignore[no-untyped-def]
        """build_crew() must return the Crew() return value."""
        result = build_crew()
        assert result is mocked_crew["Crew"].return_value

    def test_all_four_agents_created(self, mocked_crew) -> None:  # type: ignore[no-untyped-def]
        """All four agent factories must be called exactly once."""
        build_crew()
        for key in ("nav_agent", "rdr_agent", "rsn_agent", "ptr_agent"):
            mocked_crew[key].assert_called_once()

    def test_tasks_wired_sequentially(self, mocked_crew) -> None:  # type: ignore[no-untyped-def]
        """Each task receives the previous task's output as its context argument."""
        build_crew()
        m = mocked_crew
        m["rdr_task"].assert_called_once_with(m["rdr_agent"].return_value, m["nav_task"].return_value, retry_hint="")
        m["rsn_task"].assert_called_once_with(m["rsn_agent"].return_value, m["rdr_task"].return_value, retry_hint="")
        m["ptr_task"].assert_called_once_with(m["ptr_agent"].return_value, m["rsn_task"].return_value)

    def test_retry_hint_forwarded_to_reader_and_reasoner(self, mocked_crew) -> None:  # type: ignore[no-untyped-def]
        """retry_hint must reach reader_task and reasoner_task but not patcher_task."""
        build_crew(retry_hint="expand lines 15-50")
        m = mocked_crew
        assert m["rdr_task"].call_args.kwargs["retry_hint"] == "expand lines 15-50"
        assert m["rsn_task"].call_args.kwargs["retry_hint"] == "expand lines 15-50"
        assert "retry_hint" not in (m["ptr_task"].call_args.kwargs or {})

    def test_crew_uses_sequential_process_and_verbose(self, mocked_crew) -> None:  # type: ignore[no-untyped-def]
        """Crew must be constructed with Process.sequential and verbose=True."""
        build_crew()
        _, kwargs = mocked_crew["Crew"].call_args
        assert kwargs["process"] == Process.sequential
        assert kwargs["verbose"] is True

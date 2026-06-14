"""Wire the four-agent debugging crew into a ready-to-run CrewAI Crew."""
from __future__ import annotations

from crewai import Crew, Process

from crewai_graphify.agents.crew import (
    navigator_agent,
    patcher_agent,
    reader_agent,
    reasoner_agent,
)
from crewai_graphify.agents.tasks import (
    navigator_task,
    patcher_task,
    reader_task,
    reasoner_task,
)

__all__ = ["build_crew"]


def build_crew() -> Crew:
    """Instantiate all four agents, chain their tasks, return a ready Crew."""
    nav = navigator_agent()
    rdr = reader_agent()
    rsn = reasoner_agent()
    ptr = patcher_agent()
    t1 = navigator_task(nav)
    t2 = reader_task(rdr, t1)
    t3 = reasoner_task(rsn, t2)
    t4 = patcher_task(ptr, t3)
    return Crew(
        agents=[nav, rdr, rsn, ptr],
        tasks=[t1, t2, t3, t4],
        process=Process.sequential,
        verbose=True,
    )

"""Wire the four-agent debugging crew into a ready-to-run CrewAI Crew."""
from __future__ import annotations

from pathlib import Path

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
from crewai_graphify.agents.tools import reset_read_cap

__all__ = ["build_crew"]

_HOT_MD = Path("workspace/vault/hot.md")


def build_crew(retry_hint: str = "") -> tuple[Crew, dict[str, str]]:
    """Instantiate all four agents, chain their tasks, return (Crew, kickoff inputs).

    The hot.md vault report is read once here and injected directly into the
    navigator task via ``crew.kickoff(inputs=...)`` so the Navigator agent
    never needs to call a tool — eliminating hallucinated file names.
    """
    reset_read_cap()  # clear the process-global read counter so re-runs aren't bricked
    hot_md_content = _HOT_MD.read_text(encoding="utf-8") if _HOT_MD.exists() else ""
    nav = navigator_agent()
    rdr = reader_agent()
    rsn = reasoner_agent()
    ptr = patcher_agent()
    t1 = navigator_task(nav)
    t2 = reader_task(rdr, t1, retry_hint=retry_hint)
    t3 = reasoner_task(rsn, t2, retry_hint=retry_hint)
    t4 = patcher_task(ptr, t3)
    crew = Crew(
        agents=[nav, rdr, rsn, ptr],
        tasks=[t1, t2, t3, t4],
        process=Process.sequential,
        verbose=True,
    )
    return crew, {"hot_md_content": hot_md_content}

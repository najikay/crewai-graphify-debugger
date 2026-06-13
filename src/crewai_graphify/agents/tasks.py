"""Task definitions for the graph-guided debugging pipeline.

Tasks are created via factory functions.  Each function returns a configured
``crewai.Task`` and accepts the agents and upstream tasks it depends on so
that the caller controls wiring (no module-level singletons).

Sequential order: navigator_task → reader_task → reasoner_task.
"""
from __future__ import annotations

from crewai import Agent, Task

from crewai_graphify.agents.tools import read_code_slice, read_vault_document

__all__ = ["navigator_task", "reader_task", "reasoner_task"]


def navigator_task(navigator: Agent) -> Task:
    """Task 1 — read hot.md and map the bug dependency chain."""
    return Task(
        name="navigator_task",
        description=(
            "Read the file ``hot.md`` from the vault using the "
            "``read_vault_document`` tool.  Extract:\n"
            "1. The name of the source file most likely to contain the bug.\n"
            "2. The class or function at the root of the hot call chain.\n"
            "3. The ordered list of nodes in the dependency chain (hottest first).\n"
            "Return these three items as a structured plain-text summary."
        ),
        expected_output=(
            "A plain-text summary containing: the target source file name, "
            "the root-cause class/function name, and an ordered dependency chain."
        ),
        agent=navigator,
        tools=[read_vault_document],
    )


def reader_task(reader: Agent, nav_task: Task) -> Task:
    """Task 2 — fetch exact code slices for every node in the chain."""
    return Task(
        name="reader_task",
        description=(
            "Using the Navigator's output, call ``read_code_slice`` for each "
            "class or function in the dependency chain.  You MUST supply "
            "``start_line`` and ``end_line`` for every call — never read an "
            "entire file.  Collect all slices and return them verbatim, "
            "labelled by node name and line range."
        ),
        expected_output=(
            "All relevant code slices, each labelled with its node name and "
            "line range, ready for root-cause analysis."
        ),
        agent=reader,
        context=[nav_task],
        tools=[read_code_slice],
    )


def reasoner_task(reasoner: Agent, read_task: Task) -> Task:
    """Task 3 — synthesise a JSON root-cause report from the code slices."""
    return Task(
        name="reasoner_task",
        description=(
            "Analyse the code slices from the Reader and produce a JSON "
            "root-cause report.  The JSON MUST contain exactly these keys:\n"
            '  "root_cause"    — one-sentence description of the bug\n'
            '  "file"          — relative path of the affected source file\n'
            '  "line"          — integer line number of the defect\n'
            '  "fix_suggestion"— concrete code change that fixes the bug\n'
            "Output raw JSON only; no markdown fences, no preamble."
        ),
        expected_output=(
            'A raw JSON object with keys "root_cause", "file", "line", '
            'and "fix_suggestion".'
        ),
        agent=reasoner,
        context=[read_task],
        tools=[],
    )

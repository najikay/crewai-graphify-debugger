"""Task definitions for the graph-guided debugging pipeline.

Tasks are created via factory functions.  Each function returns a configured
``crewai.Task`` and accepts the agents and upstream tasks it depends on so
that the caller controls wiring (no module-level singletons).

Sequential order: navigator_task → reader_task → reasoner_task → patcher_task.
"""
from __future__ import annotations

from crewai import Agent, Task

from crewai_graphify.agents.tools import apply_patch, read_code_slice, read_vault_document

__all__ = ["navigator_task", "patcher_task", "reader_task", "reasoner_task"]


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
    """Task 2 — fetch exact code slices (capped by _MAX_READS)."""
    return Task(
        name="reader_task",
        description=(
            "Using the Navigator's output, call ``read_code_slice`` for each "
            "class or function in the dependency chain.  Supply ``start_line`` "
            "and ``end_line`` for every call — never read an entire file.  "
            "If the tool returns a read-cap error, stop immediately and pass "
            "whatever slices you have collected to the Reasoner."
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
    """Task 3 — synthesise a Hypothesis JSON from the code slices."""
    return Task(
        name="reasoner_task",
        description=(
            "Analyse the code slices from the Reader.  Output a JSON object "
            "with exactly these keys:\n"
            '  "root_cause"       — one-sentence bug description\n'
            '  "confidence_score" — float 0.0–1.0; set < 0.7 if you need\n'
            "                       more slices (signals re-read to Patcher)\n"
            '  "requested_diff"   — {"original_code": ..., "new_code": ...}\n'
            "Output raw JSON only — no markdown fences or preamble."
        ),
        expected_output=(
            'A raw JSON Hypothesis: {"root_cause": ..., "confidence_score": ..., '
            '"requested_diff": {"original_code": ..., "new_code": ...}}'
        ),
        agent=reasoner,
        context=[read_task],
        tools=[],
    )


def patcher_task(patcher: Agent, reason_task: Task) -> Task:
    """Task 4 — apply the diff if confidence >= 0.7, else skip."""
    return Task(
        name="patcher_task",
        description=(
            "Parse the Hypothesis JSON from the Reasoner.  "
            "If ``confidence_score >= 0.7``, call ``apply_patch`` with the "
            "``file_path`` inferred from context, ``original_code``, and "
            "``new_code`` from ``requested_diff``.  "
            "If ``confidence_score < 0.7``, output exactly:\n"
            "``SKIPPED: confidence too low (<0.7) — re-read required``"
            " and take no further action."
        ),
        expected_output=(
            "Either 'Patch applied to <file>: replaced N chars.' on success, or "
            "'SKIPPED: confidence too low (<0.7) — re-read required' if skipped."
        ),
        agent=patcher,
        context=[reason_task],
        tools=[apply_patch],
    )

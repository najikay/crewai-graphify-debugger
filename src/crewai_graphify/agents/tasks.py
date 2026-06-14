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
            "You MUST physically call the ``read_vault_document`` tool with "
            "filename='hot.md'. You are STRICTLY FORBIDDEN from guessing, "
            "imagining, or predicting file names, node names, or any content. "
            "Your output MUST contain only the actual file paths and component "
            "names returned by the tool — nothing invented.\n"
            "Extract and report:\n"
            "1. The Primary Target File path (from the tool output).\n"
            "2. The Root-Cause Node name (from the tool output).\n"
            "3. The ordered dependency chain (hottest first, from tool output)."
        ),
        expected_output=(
            "A plain-text summary with: the exact target source file path, "
            "the root-cause class/function name, and an ordered dependency chain "
            "— all sourced from the vault document, nothing invented."
        ),
        agent=navigator,
        tools=[read_vault_document],
    )


def reader_task(reader: Agent, nav_task: Task, retry_hint: str = "") -> Task:
    """Task 2 — fetch exact code slices (capped by _MAX_READS)."""
    hint = f"\n\n{retry_hint}" if retry_hint else ""
    return Task(
        name="reader_task",
        description=(
            "Using the Navigator's output, call ``read_code_slice`` for each "
            "class or function in the dependency chain.  Supply ``start_line`` "
            "and ``end_line`` for every call — never read an entire file.  "
            "If the tool returns a read-cap error, stop immediately and pass "
            f"whatever slices you have collected to the Reasoner.{hint}"
        ),
        expected_output=(
            "All relevant code slices, each labelled with its node name and "
            "line range, ready for root-cause analysis."
        ),
        agent=reader,
        context=[nav_task],
        tools=[read_code_slice],
    )


def reasoner_task(reasoner: Agent, read_task: Task, retry_hint: str = "") -> Task:
    """Task 3 — synthesise a Hypothesis JSON from the code slices."""
    hint = f"\n\n{retry_hint}" if retry_hint else ""
    return Task(
        name="reasoner_task",
        description=(
            "Analyse the code slices from the Reader.  Output a JSON object "
            "with exactly these keys:\n"
            '  "root_cause"       — one-sentence bug description\n'
            '  "confidence_score" — float 0.0–1.0; set < 0.7 if you need\n'
            "                       more slices (signals re-read to Patcher)\n"
            '  "requested_diff"   — {"original_code": ..., "new_code": ...}\n'
            f"Output raw JSON only — no markdown fences or preamble.{hint}"
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

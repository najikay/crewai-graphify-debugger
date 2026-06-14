"""Task definitions for the graph-guided debugging pipeline.

Tasks are created via factory functions.  Each function returns a configured
``crewai.Task`` and accepts the agents and upstream tasks it depends on so
that the caller controls wiring (no module-level singletons).

Sequential order: navigator_task → reader_task → reasoner_task → patcher_task.
"""
from __future__ import annotations

from crewai import Agent, Task

from crewai_graphify.agents.tools import apply_patch, read_code_slice

__all__ = ["navigator_task", "patcher_task", "reader_task", "reasoner_task"]


def navigator_task(navigator: Agent) -> Task:
    """Task 1 — analyse the injected vault report and map the bug dependency chain."""
    return Task(
        name="navigator_task",
        description=(
            "Analyze the following vault report to find the root cause of the bug. "
            "DO NOT invent or guess any files. You MUST strictly use the file paths "
            "and node names exactly as they appear in this report:\n\n{hot_md_content}"
        ),
        expected_output=(
            "A plain-text summary with: the exact target source file path, "
            "the root-cause class/function name, and an ordered dependency chain "
            "— all taken verbatim from the vault report above, nothing invented."
        ),
        agent=navigator,
        tools=[],
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
            '  "target_file"      — the EXACT file path of the buggy file,\n'
            "                       copied verbatim from the Reader's slice\n"
            "                       header (the one you actually diagnosed).\n"
            '  "root_cause"       — one-sentence bug description\n'
            '  "confidence_score" — float 0.0–1.0; set < 0.7 if you need\n'
            "                       more slices (signals re-read to Patcher)\n"
            '  "requested_diff"   — {"original_code": ..., "new_code": ...}\n'
            "The ``original_code`` MUST be a real, non-trivial snippet from the "
            "diagnosed file and MUST differ from ``new_code``.\n"
            f"Output raw JSON only — no markdown fences or preamble.{hint}"
        ),
        expected_output=(
            'A raw JSON Hypothesis: {"target_file": ..., "root_cause": ..., '
            '"confidence_score": ..., "requested_diff": {"original_code": ..., '
            '"new_code": ...}}'
        ),
        agent=reasoner,
        context=[read_task],
        tools=[],
    )


def patcher_task(patcher: Agent, reason_task: Task) -> Task:
    """Task 4 — apply the diff if confidence >= 0.7, else skip.

    Context is restricted to ``reason_task`` ONLY so the Patcher cannot pick up
    stray filenames from earlier tasks in the run history.
    """
    return Task(
        name="patcher_task",
        description=(
            "Your ONLY input is the Reasoner's Hypothesis JSON in your context. "
            "Parse it and act strictly on its fields:\n"
            "1. Read ``confidence_score``. If it is < 0.7, output EXACTLY:\n"
            "   ``SKIPPED: confidence too low (<0.7) — re-read required``\n"
            "   and take NO further action.\n"
            "2. If it is >= 0.7, call ``apply_patch`` with:\n"
            "   - ``file_path``  = the Hypothesis ``target_file`` value, copied\n"
            "                      EXACTLY as written. You are STRICTLY FORBIDDEN\n"
            "                      from guessing a path, inventing a filename, or\n"
            "                      targeting any other file you saw earlier in the\n"
            "                      run. If ``target_file`` is missing, output the\n"
            "                      SKIPPED line above.\n"
            "   - ``original_code`` and ``new_code`` = verbatim from\n"
            "                      ``requested_diff``. They MUST differ; never\n"
            "                      submit a no-op patch (e.g. 'print' -> 'print')."
        ),
        expected_output=(
            "Either 'Patch applied to <file>: replaced N chars.' on success, or "
            "'SKIPPED: confidence too low (<0.7) — re-read required' if skipped."
        ),
        agent=patcher,
        context=[reason_task],
        tools=[apply_patch],
    )

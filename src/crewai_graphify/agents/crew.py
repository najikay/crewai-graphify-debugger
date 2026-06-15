"""CrewAI agent definitions for the graph-guided debugging pipeline.

Each agent uses ``_make_llm()`` which reads ``LLM_PROVIDER`` / ``DEFAULT_MODEL``
from the environment so the backend can be swapped (Claude ↔ DeepSeek) without
touching source code.  Agents are created via factory functions so callers can
instantiate fresh agents per run without sharing state.
"""
from __future__ import annotations

import os

from crewai import Agent

from crewai_graphify.agents.tools import apply_patch, read_code_slice
from crewai_graphify.sdk.claude_client import GatekeeperLLM

__all__ = ["navigator_agent", "patcher_agent", "reader_agent", "reasoner_agent"]


def _make_llm() -> GatekeeperLLM:
    """Return the gatekept LLM selected by ``LLM_PROVIDER`` (default: ``claude``).

    Both providers return a ``GatekeeperLLM`` so EVERY call routes through the
    ``ApiGatekeeper`` (budget + telemetry).  Only the payload ``model`` differs;
    the concrete API is chosen by which ``_ClientProtocol`` adapter the gatekeeper
    was initialised with (Anthropic for ``claude``, DeepSeek for ``deepseek``).
    """
    provider = os.getenv("LLM_PROVIDER", "claude").lower()
    if provider == "deepseek":
        return GatekeeperLLM(model=os.getenv("DEFAULT_MODEL", "deepseek-chat"))
    return GatekeeperLLM()


def navigator_agent() -> Agent:
    """Return a Navigator agent that analyses the injected vault report."""
    return Agent(
        role="Graph Navigator",
        goal=(
            "Analyze the vault report already provided in your task to identify "
            "the buggy file, the affected class or function, and the full "
            "dependency chain — using only the data given, never inventing names."
        ),
        backstory=(
            "You are an expert at reading code-dependency graphs represented "
            "as Obsidian markdown.  You extract structured information about "
            "which nodes are hottest and trace the call chain to the root cause."
        ),
        llm=_make_llm(),
        tools=[],
        verbose=False,
        allow_delegation=False,
    )


def reader_agent() -> Agent:
    """Return a Reader agent that fetches code slices (capped at _MAX_READS)."""
    return Agent(
        role="Code Slice Reader",
        goal=(
            "Retrieve only the exact lines of source code identified by the "
            "Navigator, keeping token usage minimal by never reading entire files.  "
            "Stop immediately if the tool returns a read-cap error."
        ),
        backstory=(
            "You are a precision code inspector.  Given a file name and line "
            "range you fetch exactly those lines and nothing more, so the "
            "Reasoner receives focused, high-signal input."
        ),
        llm=_make_llm(),
        tools=[read_code_slice],
        verbose=False,
        allow_delegation=False,
    )


def reasoner_agent() -> Agent:
    """Return a Reasoner agent that synthesises a Hypothesis JSON report."""
    return Agent(
        role="Root Cause Reasoner",
        goal=(
            "Analyse the code slices provided by the Reader and produce a "
            "precise Hypothesis JSON.  Set confidence_score >= 0.7 only when "
            "certain; a score below 0.7 signals the Patcher to skip and "
            "indicates that more context is needed."
        ),
        backstory=(
            "You are a senior Python debugger.  You read code evidence "
            "synthesised from the dependency graph and identify the exact "
            "logical error, its location, and the minimal change required."
        ),
        llm=_make_llm(),
        tools=[],
        verbose=False,
        allow_delegation=False,
    )


def patcher_agent() -> Agent:
    """Return a Patcher agent that applies diffs when confidence >= 0.7."""
    return Agent(
        role="Code Patcher",
        goal=(
            "Apply the minimal diff from the Hypothesis to the target file "
            "only when confidence_score >= 0.7; output SKIPPED if below."
        ),
        backstory=(
            "You are a careful code editor.  You receive a Hypothesis JSON "
            "and use apply_patch to replace original_code with new_code in "
            "the target file — only when confidence is sufficient."
        ),
        llm=_make_llm(),
        tools=[apply_patch],
        verbose=False,
        allow_delegation=False,
    )

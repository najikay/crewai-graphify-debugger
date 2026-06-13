"""CrewAI agent definitions for the graph-guided debugging pipeline.

Each agent uses ``ClaudeClient`` as its LLM so every call is routed through
``ApiGatekeeper`` for telemetry.  Agents are created via factory functions so
callers can instantiate fresh agents per run without sharing state.
"""
from __future__ import annotations

from crewai import Agent

from crewai_graphify.agents.tools import read_code_slice, read_vault_document
from crewai_graphify.sdk.claude_client import ClaudeClient

__all__ = ["navigator_agent", "reader_agent", "reasoner_agent"]


def navigator_agent() -> Agent:
    """Return a Navigator agent that reads vault documents to map the bug."""
    return Agent(
        role="Graph Navigator",
        goal=(
            "Read the vault's hot-node document to identify the buggy file, "
            "the affected class or function, and the full dependency chain."
        ),
        backstory=(
            "You are an expert at reading code-dependency graphs represented "
            "as Obsidian markdown.  You extract structured information about "
            "which nodes are hottest and trace the call chain to the root cause."
        ),
        llm=ClaudeClient(),
        tools=[read_vault_document],
        verbose=False,
        allow_delegation=False,
    )


def reader_agent() -> Agent:
    """Return a Reader agent that fetches specific code slices."""
    return Agent(
        role="Code Slice Reader",
        goal=(
            "Retrieve only the exact lines of source code identified by the "
            "Navigator, keeping token usage minimal by never reading entire files."
        ),
        backstory=(
            "You are a precision code inspector.  Given a file name and line "
            "range you fetch exactly those lines and nothing more, so the "
            "Reasoner receives focused, high-signal input."
        ),
        llm=ClaudeClient(),
        tools=[read_code_slice],
        verbose=False,
        allow_delegation=False,
    )


def reasoner_agent() -> Agent:
    """Return a Reasoner agent that synthesises a JSON root-cause report."""
    return Agent(
        role="Root Cause Reasoner",
        goal=(
            "Analyse the code slices provided by the Reader and produce a "
            "precise JSON root-cause report identifying the bug, its location, "
            "and a concrete fix suggestion."
        ),
        backstory=(
            "You are a senior Python debugger.  You read code evidence "
            "synthesised from the dependency graph and identify the exact "
            "logical error, the file and line it appears on, and the minimal "
            "change required to fix it."
        ),
        llm=ClaudeClient(),
        tools=[],
        verbose=False,
        allow_delegation=False,
    )

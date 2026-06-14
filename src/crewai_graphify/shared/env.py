"""Side-effect module: hydrate process env from the project ``.env`` file.

Importing this module calls :func:`dotenv.load_dotenv` exactly once so that
``LLM_PROVIDER``, ``DEFAULT_MODEL`` and the provider API keys are available to
the multi-provider LLM factory (``agents/crew.py::_make_llm``) before any agent
is constructed.  Kept as a dedicated module so application entry points can make
loading the first import without tripping ruff E402 on subsequent imports.
"""
from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

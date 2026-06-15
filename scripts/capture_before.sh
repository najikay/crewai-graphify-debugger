#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# capture_before.sh — snapshot the pristine "Before" baseline into obsidian/.
#
#   1. Backend reset: restore the pristine, buggy martinpeck/broken-python code
#      to workspace/target/  (via ensure_fixture — the SAME function the
#      POST /api/reset endpoint calls).
#   2. AST graph builder: ensure_fixture also re-parses workspace/target/ and
#      regenerates the raw vault (graph.json + index.md + hot.md).
#   3. Clear obsidian/ and copy the raw baseline vault into it.
#
# NOTE: produces the RAW, generated vault only — no Hebrew assignment docs.
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")/.."   # project root

# 1 + 2) Trigger the backend reset (restores pristine buggy code) and rebuild
#        the AST vault. ensure_fixture() performs both, exactly like /api/reset.
uv run python -c "from crewai_graphify.shared.fixture_setup import ensure_fixture; ensure_fixture(print)"

# 3) Replace obsidian/ with the raw baseline vault (no Hebrew docs).
rm -rf obsidian
mkdir -p obsidian
cp workspace/vault/graph.json workspace/vault/hot.md workspace/vault/index.md obsidian/

echo "✅ Before-state captured into obsidian/:"
ls -1 obsidian/

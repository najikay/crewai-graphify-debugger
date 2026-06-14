#!/usr/bin/env bash
# dev.sh — start FastAPI backend + React frontend concurrently
# Usage: bash scripts/dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "[dev] Starting FastAPI backend on http://localhost:8000 ..."
cd "$ROOT"
uv run uvicorn crewai_graphify.server:app --reload --reload-exclude "fixtures/*" --reload-exclude "workspace/*" --port 8000 &
BACKEND_PID=$!

echo "[dev] Starting React frontend on http://localhost:5173 ..."
cd "$ROOT/ui"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
echo "  API docs → http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Clean shutdown on Ctrl-C
trap 'echo ""; echo "[dev] Stopping..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0' INT TERM
wait

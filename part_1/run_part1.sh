#!/usr/bin/env bash

# Simple orchestrator script to run all Part 1 services and the Streamlit UI.
#
# Usage:
#   cd path/to/kpmg/part_1
#   chmod +x run_part1.sh
#   ./run_part1.sh
#

set -euo pipefail

# Resolve script directory to run commands from project root (part_1)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Graceful shutdown on Ctrl-C
pids=()
cleanup() {
  echo
  echo "Stopping services..."
  for pid in "${pids[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  exit 0
}
trap cleanup INT TERM

# Helper to run a service in the background
run_service() {
  local name="$1"
  shift
  echo "Starting $name..."
  "$@" &
  local pid=$!
  pids+=("$pid")
  echo "  -> $name (pid $pid)"
}

# Start OCR, Extraction, and Validation services
run_service "OCR service" \
  uvicorn ocr-service.app:app --host 0.0.0.0 --port 8001 --reload

run_service "Extraction service" \
  uvicorn extraction-service.app:app --host 0.0.0.0 --port 8002 --reload

run_service "Validation service" \
  uvicorn validation-service.app:app --host 0.0.0.0 --port 8003 --reload

# Give services a moment to come up
sleep 3

echo
echo "Starting Streamlit UI..."
streamlit run ui-service/app.py

# If Streamlit exits, clean up background services
cleanup

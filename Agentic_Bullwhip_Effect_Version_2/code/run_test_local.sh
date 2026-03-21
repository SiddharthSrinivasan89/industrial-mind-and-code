#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Local smoke test — 1 run per condition, baselines + E1 + E2
#
# Purpose: verify local Ollama backend, model availability, JSON parsing,
#          and output files without spending Azure credits.
#
# Models used (from .env.local):
#   E1 lightweight: MODEL_LIGHTWEIGHT (default: phi4:14b)
#   E2 reasoning:   MODEL_REASONING   (default: gpt-oss:120b)
#
# Usage:
#   chmod +x run_test_local.sh
#   ./run_test_local.sh
#
# Prerequisites:
#   - Ollama running: ollama serve
#   - Models pulled: pull the models configured in .env.local (defaults: ollama pull phi4:14b && ollama pull gpt-oss:120b)
#   - .env.local configured — first-time setup: cp env.local.template .env.local
#     The template includes all required variables with inline documentation,
#     including the temperature design rationale (blind=0.0, context=0.3).
#
# Timing estimates (NVIDIA GB10, Q4_K_M):
#   E1 (phi4:14b):     ~6 min  (144 calls × ~2.3s)
#   E2 (gpt-oss:120b): ~12 min (144 calls × ~5.0s)
#
# Output: test_runs/<experiment>/<timestamp>/
# ---------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Agentic Bullwhip V2 — Local Smoke Test ==="
echo "Backend: Local Ollama"
echo "Runs per condition: 1"
echo "Output: test_runs/"
echo ""

# Check Ollama is reachable
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434. Run: ollama serve"
    exit 1
fi

# Activate virtualenv if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

LOG_FILE="test_runs/smoke_local_$(date +%Y%m%dT%H%M%S).log"
mkdir -p test_runs
echo "Logging to $LOG_FILE"

# Run baselines + E1 + E2 with 1 run each, output to test_runs/
# nohup keeps the process alive if the terminal closes mid-run (remote client safety).
# This call is intentionally blocking — the shell waits for it to finish before
# running validation. To run in the background instead, add & and track the PID.
nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --runs 1 \
    --env .env.local \
    --results-dir test_runs \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== Smoke test complete. Results in test_runs/ ==="
echo "Full log: $LOG_FILE"

# Extract exact run timestamps from the log — avoids race condition if another
# run lands in test_runs/ concurrently (ls -1t would pick the wrong directory).
BASELINES_TS=$(grep "baselines complete.*results at" "$LOG_FILE" | grep -o 'baselines/[0-9T]*' | cut -d/ -f2 | tail -1 || true)
E1_TS=$(grep "E1 complete.*results at" "$LOG_FILE" | grep -o 'E1/[0-9T]*' | cut -d/ -f2 | tail -1 || true)
E2_TS=$(grep "E2 complete.*results at" "$LOG_FILE" | grep -o 'E2/[0-9T]*' | cut -d/ -f2 | tail -1 || true)

if [ -z "$BASELINES_TS" ] || [ -z "$E1_TS" ] || [ -z "$E2_TS" ]; then
    echo "ERROR: Could not extract run timestamps from log. Check $LOG_FILE for failures." >&2
    exit 1
fi


# Validate only the runs created by this invocation
python verify_smoke_outputs.py \
    --results-dir test_runs \
    --run-dirs "baselines=${BASELINES_TS}" "E1=${E1_TS}" "E2=${E2_TS}" \
    --runs 1

#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Sarvam-30b smoke test — 1 run per condition, baselines + E1 + E2
#
# Model: sarvam-30b (both lightweight and reasoning tiers)
# Output: test_runs/
# Session: sarvam-smoke
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-smoke"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# If not inside tmux, launch a new session and run this script inside it
if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== Agentic Bullwhip V2a — Sarvam-30b Smoke Test ==="
echo "Backend: Local Ollama (sarvam-30b)"
echo "Runs per condition: 1"
echo "Output: test_runs/"
echo ""

# Check Ollama is reachable
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434. Run: ollama serve"
    exit 1
fi

# Check llama-server is running with sarvam-30b
if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080. Start with run_sarvam_server.sh"
    exit 1
fi

# Activate virtualenv if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

mkdir -p test_runs
LOG_FILE="test_runs/smoke_sarvam_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --runs 1 \
    --env .env.sarvam \
    --results-dir test_runs \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== Smoke test complete. Results in test_runs/ ==="
echo "Full log: $LOG_FILE"

BASELINES_TS=$(grep "baselines complete.*results at" "$LOG_FILE" | grep -o 'baselines/[0-9T]*' | cut -d/ -f2 | tail -1 || true)
E1_TS=$(grep "E1 complete.*results at" "$LOG_FILE" | grep -o 'E1/[0-9T]*' | cut -d/ -f2 | tail -1 || true)
E2_TS=$(grep "E2 complete.*results at" "$LOG_FILE" | grep -o 'E2/[0-9T]*' | cut -d/ -f2 | tail -1 || true)

if [ -z "$BASELINES_TS" ] || [ -z "$E1_TS" ] || [ -z "$E2_TS" ]; then
    echo "ERROR: Could not extract run timestamps from log. Check $LOG_FILE for failures." >&2
    exit 1
fi

python verify_smoke_outputs.py \
    --results-dir test_runs \
    --run-dirs "baselines=${BASELINES_TS}" "E1=${E1_TS}" "E2=${E2_TS}" \
    --runs 1

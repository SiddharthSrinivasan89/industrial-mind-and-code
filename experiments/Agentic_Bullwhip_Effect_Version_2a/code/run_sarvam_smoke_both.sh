#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Sarvam-30b smoke test — both blind and context, 1 run per condition
#
# After reverting the "Think silently" system prompt optimisation (which
# increased parse errors from ~5% to ~22%), this smoke test validates that
# the original prompts work cleanly for both conditions.
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-smoke"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== Agentic Bullwhip V2a — Sarvam-30b Smoke Test (both conditions) ==="
echo "Backend: Local llama-server (sarvam-30b)"
echo "Conditions: blind + context (1 run each)"
echo "Prompts: original (no 'Think silently' instruction)"
echo ""

if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080."
    exit 1
fi

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

mkdir -p test_runs ../logs
LOG_FILE="../logs/sarvam_smoke_both_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --runs 1 \
    --env .env.sarvam \
    --results-dir test_runs \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== Smoke test complete ==="
echo "Finished at: $(date)"
echo "Log: $LOG_FILE"

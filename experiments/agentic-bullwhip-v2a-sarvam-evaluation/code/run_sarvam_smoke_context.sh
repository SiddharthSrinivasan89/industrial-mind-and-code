#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Sarvam-30b context-only smoke test — 1 run per context condition
#
# Blind conditions are not viable with sarvam-30b (0% per-run success rate
# across all configurations tested). This smoke test validates context-only
# before the full overnight run.
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

echo "=== Agentic Bullwhip V2a — Sarvam-30b Context Smoke Test ==="
echo "Backend: Local llama-server (sarvam-30b)"
echo "Conditions: context only (1 run each)"
echo ""

if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080."
    exit 1
fi

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

mkdir -p test_runs ../logs
LOG_FILE="../logs/sarvam_smoke_context_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --conditions context \
    --runs 1 \
    --env .env.sarvam \
    --results-dir test_runs \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== Context smoke test complete ==="
echo "Finished at: $(date)"
echo "Log: $LOG_FILE"

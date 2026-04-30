#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Sarvam-30b blind smoke test — 1 run per blind condition
#
# Diagnostic run to see if blind conditions can complete at all with sarvam-30b.
# The full run showed 22% per-call parse error rate for blind (vs ~5% for context),
# causing ~95% of runs to fail due to the minimal system prompt.
#
# Uses identical runtime settings as context (temp=1.0, same token limits, same
# think flags) — the only difference is the prompt content (no identity, no calendar).
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-blind-smoke"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# If not inside tmux, launch a new session and run this script inside it
if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== Agentic Bullwhip V2a — Sarvam-30b Blind Smoke Test ==="
echo "Backend: Local llama-server (sarvam-30b)"
echo "Conditions: blind only (1 run each)"
echo "Purpose: diagnose whether blind can complete with sarvam-30b"
echo ""

# Check llama-server is running with sarvam-30b
if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080."
    exit 1
fi

# Activate virtualenv if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

mkdir -p test_runs ../logs
LOG_FILE="../logs/sarvam_blind_smoke_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments E1 E2 \
    --conditions blind \
    --runs 1 \
    --env .env.sarvam \
    --results-dir test_runs \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== Blind smoke test complete ==="
echo "Finished at: $(date)"
echo "Log: $LOG_FILE"

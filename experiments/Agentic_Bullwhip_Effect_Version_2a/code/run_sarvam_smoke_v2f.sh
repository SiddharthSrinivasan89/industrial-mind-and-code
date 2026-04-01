#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# V2f smoke test — sarvam-105b at GGUF agentic settings (temp=0.5, top_p=1.0)
#
# Model: sarvam-105b, context conditions only
# Results: ../results/sarvam_105b/v2f/
# Session: sarvam-v2f-smoke
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-v2f-smoke"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== V2f Smoke Test — sarvam-105b GGUF Agentic Settings ==="
echo "Backend: Local llama-server (sarvam-105b)"
echo "Env: .env.sarvam_105b_v2f (temp=0.5, top_p=1.0)"
echo "Conditions: context only, 1 run each"
echo "Results: ../results/sarvam_105b/v2f/"
echo ""

if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080"
    exit 1
fi

if [ -d ".venv" ]; then source .venv/bin/activate; fi

mkdir -p ../results/sarvam_105b/v2f ../logs
LOG_FILE="../logs/sarvam_105b_v2f_smoke_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --conditions context \
    --runs 1 \
    --env .env.sarvam_105b_v2f \
    --results-dir ../results/sarvam_105b/v2f \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== V2f smoke test complete ==="
echo "Finished at: $(date)"
echo "  Total calls:  $(grep -c 'HTTP/1.1 200 OK' $LOG_FILE || echo 0)"
echo "  Parse errors: $(grep -c 'WARNING.*parse error' $LOG_FILE || echo 0)"

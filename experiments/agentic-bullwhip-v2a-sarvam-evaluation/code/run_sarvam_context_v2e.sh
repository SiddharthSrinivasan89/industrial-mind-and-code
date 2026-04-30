#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# V2e full run — sarvam-105b at GGUF reasoning settings (temp=1.0, top_p=1.0)
#
# Run ONLY after smoke test (run_sarvam_smoke_v2e.sh) passes (≤ 10% errors).
#
# Model: sarvam-105b, context conditions only, 10 runs each
# Results: ../results/sarvam_105b/v2e/
# Session: sarvam-v2e
#
# Timing: ~20-25 hours (105b is larger, ~40-50s/call estimated)
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-v2e"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== V2e Full Run — sarvam-105b GGUF Reasoning Settings ==="
echo "Backend: Local llama-server (sarvam-105b)"
echo "Env: .env.sarvam_105b_v2e (temp=1.0, top_p=1.0)"
echo "Conditions: context only, 10 runs each"
echo "Results: ../results/sarvam_105b/v2e/"
echo ""

if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080"
    exit 1
fi

if [ -d ".venv" ]; then source .venv/bin/activate; fi

mkdir -p ../results/sarvam_105b/v2e ../logs
LOG_FILE="../logs/sarvam_105b_v2e_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --conditions context \
    --runs 10 \
    --env .env.sarvam_105b_v2e \
    --results-dir ../results/sarvam_105b/v2e \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== V2e full run complete ==="
echo "Finished at: $(date)"
echo "Results: ../results/sarvam_105b/v2e/"

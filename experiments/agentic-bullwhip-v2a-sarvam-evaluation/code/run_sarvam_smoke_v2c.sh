#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# V2c smoke test — GGUF agentic settings (temp=0.5, top_p=1.0)
#
# Tests whether the agentic benchmark settings from the GGUF model card
# (sarvamai/sarvam-30b-gguf on HuggingFace) work for structured JSON output.
#
# GGUF model card agentic settings (Mar 2026):
#   temperature=0.5, top_p=1.0, max_new_tokens=32768
#
# This fills the gap between:
#   temp=0.4 (failed — 40-60% empty responses)
#   temp=1.0 (V2a — 94.6% SOR, our working setting)
#
# Also convergence point with cloud API think-mode recommendation (>=0.5).
#
# Decision gate:
#   Parse error rate ≤ 10% → proceed to full V2c run
#   Parse error rate > 20% → temp=0.5 insufficient for local GGUF
#
# Model: sarvam-30b, context conditions only
# Results: ../results/sarvam_v2c/
# Session: sarvam-v2c-smoke
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-v2c-smoke"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== V2c Smoke Test — GGUF Agentic Settings (temp=0.5, top_p=1.0) ==="
echo "Backend: Local llama-server (sarvam-30b)"
echo "Env: .env.sarvam_v2c (temp=0.5, top_p=1.0)"
echo "Conditions: context only, 1 run each"
echo "Results: ../results/sarvam_v2c/"
echo ""

if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080"
    exit 1
fi

if [ -d ".venv" ]; then source .venv/bin/activate; fi

mkdir -p ../results/sarvam_v2c ../logs
LOG_FILE="../logs/sarvam_v2c_smoke_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --conditions context \
    --runs 1 \
    --env .env.sarvam_v2c \
    --results-dir ../results/sarvam_v2c \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== V2c smoke test complete ==="
echo "Finished at: $(date)"
echo "  Total calls:  $(grep -c 'HTTP/1.1 200 OK' $LOG_FILE || echo 0)"
echo "  Parse errors: $(grep -c 'WARNING.*parse error' $LOG_FILE || echo 0)"

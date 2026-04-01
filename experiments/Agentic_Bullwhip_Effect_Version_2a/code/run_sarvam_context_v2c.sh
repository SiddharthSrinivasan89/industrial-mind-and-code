#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# V2c full run — GGUF agentic settings (temp=0.5, top_p=1.0)
#
# Run ONLY after smoke test (run_sarvam_smoke_v2c.sh) confirms ≤ 10% errors.
#
# GGUF model card agentic settings:
#   temperature=0.5, top_p=1.0
#
# Compare against:
#   V2a: temp=1.0, top_p=0.95 → SOR 94.6% E2, 92.2% E1
#   V2d: temp=1.0, top_p=1.0  → isolates top_p effect only
#
# Model: sarvam-30b, context conditions only, 10 runs each
# Results: ../results/sarvam_v2c/
# Session: sarvam-v2c
#
# Timing: ~15 hours
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-v2c"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== V2c Full Run — GGUF Agentic Settings (temp=0.5, top_p=1.0) ==="
echo "Backend: Local llama-server (sarvam-30b)"
echo "Env: .env.sarvam_v2c (temp=0.5, top_p=1.0)"
echo "Conditions: context only, 10 runs each"
echo "Results: ../results/sarvam_v2c/"
echo ""

if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080"
    exit 1
fi

if [ -d ".venv" ]; then source .venv/bin/activate; fi

mkdir -p ../results/sarvam_v2c ../logs
LOG_FILE="../logs/sarvam_v2c_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --conditions context \
    --runs 10 \
    --env .env.sarvam_v2c \
    --results-dir ../results/sarvam_v2c \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== V2c full run complete ==="
echo "Finished at: $(date)"
echo "Results: ../results/sarvam_v2c/"

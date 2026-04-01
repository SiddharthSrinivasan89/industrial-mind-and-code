#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# V2d full run — V2a temperature + explicit top_p=1.0
#
# Run ONLY after smoke test (run_sarvam_smoke_v2d.sh) confirms ≤ 10% errors.
#
# Isolates top_p effect: temperature=1.0 (same as V2a), top_p=1.0 (per GGUF doc).
# V2a used top_p=0.95 (llama.cpp default). This is the controlled comparison.
#
# Compare against:
#   V2a: temp=1.0, top_p=0.95 → SOR 94.6% E2, 92.2% E1
#   V2c: temp=0.5, top_p=1.0  → agentic setting
#
# Model: sarvam-30b, context conditions only, 10 runs each
# Results: ../results/sarvam_v2d/
# Session: sarvam-v2d
#
# Timing: ~15 hours
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-v2d"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== V2d Full Run — temp=1.0 + explicit top_p=1.0 ==="
echo "Backend: Local llama-server (sarvam-30b)"
echo "Env: .env.sarvam_v2d (temp=1.0, top_p=1.0)"
echo "Conditions: context only, 10 runs each"
echo "Results: ../results/sarvam_v2d/"
echo ""

if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080"
    exit 1
fi

if [ -d ".venv" ]; then source .venv/bin/activate; fi

mkdir -p ../results/sarvam_v2d ../logs
LOG_FILE="../logs/sarvam_v2d_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --conditions context \
    --runs 10 \
    --env .env.sarvam_v2d \
    --results-dir ../results/sarvam_v2d \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== V2d full run complete ==="
echo "Finished at: $(date)"
echo "Results: ../results/sarvam_v2d/"

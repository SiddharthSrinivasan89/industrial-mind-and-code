#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# V2d smoke test — V2a temperature + explicit top_p=1.0
#
# Isolates the top_p effect. Holds temperature at V2a's working value (1.0)
# and changes only top_p from 0.95 (llama.cpp default) to 1.0 (GGUF doc).
#
# GGUF model card reasoning settings (Mar 2026):
#   temperature=1.0, top_p=1.0
#
# V2a used top_p=0.95 (undocumented llama.cpp default, never explicitly set).
# If V2d SOR > 94.6% (V2a), top_p was limiting reliability.
# If V2d SOR ≈ 94.6%, top_p has negligible effect at temp=1.0.
#
# Model: sarvam-30b, context conditions only
# Results: ../results/sarvam_v2d/
# Session: sarvam-v2d-smoke
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-v2d-smoke"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== V2d Smoke Test — temp=1.0 + explicit top_p=1.0 ==="
echo "Backend: Local llama-server (sarvam-30b)"
echo "Env: .env.sarvam_v2d (temp=1.0, top_p=1.0)"
echo "Conditions: context only, 1 run each"
echo "Results: ../results/sarvam_v2d/"
echo ""

if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080"
    exit 1
fi

if [ -d ".venv" ]; then source .venv/bin/activate; fi

mkdir -p ../results/sarvam_v2d ../logs
LOG_FILE="../logs/sarvam_v2d_smoke_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --conditions context \
    --runs 1 \
    --env .env.sarvam_v2d \
    --results-dir ../results/sarvam_v2d \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== V2d smoke test complete ==="
echo "Finished at: $(date)"
echo "  Total calls:  $(grep -c 'HTTP/1.1 200 OK' $LOG_FILE || echo 0)"
echo "  Parse errors: $(grep -c 'WARNING.*parse error' $LOG_FILE || echo 0)"

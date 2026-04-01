#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# V2e smoke test — sarvam-105b at GGUF reasoning settings (temp=1.0, top_p=1.0)
#
# First experiment on sarvam-105b. Uses the "correct from day 1" settings
# from the GGUF model card — no trial and error required.
#
# Key difference from sarvam-30b:
#   Think flag: enable_thinking=False (deepseek2 architecture)
#   vs sarvam-30b: think=False (bailingmoe2 architecture)
#
# Prerequisites:
#   1. sarvam-105b GGUF at /home/sid/models/llama-cpp-models/sarvam-105b-gguf/
#   2. sarvam-30b llama-server STOPPED (105b needs ~68 GiB unified memory)
#   3. llama-server started with 105b model (run_sarvam_105b_server.sh)
#
# Model: sarvam-105b, context conditions only
# Results: ../results/sarvam_105b/v2e/
# Session: sarvam-v2e-smoke
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-v2e-smoke"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== V2e Smoke Test — sarvam-105b GGUF Reasoning Settings ==="
echo "Backend: Local llama-server (sarvam-105b)"
echo "Env: .env.sarvam_105b_v2e (temp=1.0, top_p=1.0)"
echo "Conditions: context only, 1 run each"
echo "Results: ../results/sarvam_105b/v2e/"
echo ""

if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080"
    echo "Start with: run_sarvam_105b_server.sh"
    exit 1
fi

if [ -d ".venv" ]; then source .venv/bin/activate; fi

mkdir -p ../results/sarvam_105b/v2e ../logs
LOG_FILE="../logs/sarvam_105b_v2e_smoke_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --conditions context \
    --runs 1 \
    --env .env.sarvam_105b_v2e \
    --results-dir ../results/sarvam_105b/v2e \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== V2e smoke test complete ==="
echo "Finished at: $(date)"
echo "  Total calls:  $(grep -c 'HTTP/1.1 200 OK' $LOG_FILE || echo 0)"
echo "  Parse errors: $(grep -c 'WARNING.*parse error' $LOG_FILE || echo 0)"

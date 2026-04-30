#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# V2b smoke test — cloud-recommended temperatures on local llama-server
#
# Tests whether the temperature values recommended in the official Sarvam API
# docs (docs.sarvam.ai) transfer to local GGUF inference via llama-server.
#
# Cloud recommendations (Mar 2026):
#   Non-thinking mode (E1): temp=0.2
#   Thinking mode (E2):     temp=0.5 or higher
#
# V2a used temp=1.0 for all conditions. This smoke test is the comparison
# baseline for the IHS temperature calibration finding.
#
# Decision gate after smoke:
#   Parse error rate ≤ 10%  → proceed to full 10-run V2b experiment
#   Parse error rate > 20%  → document as non-transfer finding (local ≠ cloud)
#
# Model: sarvam-30b (both tiers, context conditions only)
# Results: ../results/sarvam_cloud_temp/
# Logs:    ../logs/
# Session: sarvam-v2b-smoke
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-v2b-smoke"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== V2b Smoke Test — Cloud Temperature Calibration ==="
echo "Backend: Local llama-server (sarvam-30b)"
echo "Env: .env.sarvam_cloud_temp (temp=0.2 E1, temp=0.5 E2)"
echo "Conditions: context only, 1 run each"
echo "Results: ../results/sarvam_cloud_temp/"
echo ""

if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080. Start with run_sarvam_server.sh"
    exit 1
fi

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

mkdir -p ../results/sarvam_cloud_temp ../logs
LOG_FILE="../logs/sarvam_cloudtemp_smoke_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --conditions context \
    --runs 1 \
    --env .env.sarvam_cloud_temp \
    --results-dir ../results/sarvam_cloud_temp \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== V2b smoke test complete ==="
echo "Finished at: $(date)"
echo "Results: ../results/sarvam_cloud_temp/"
echo "Full log: $LOG_FILE"
echo ""
echo "Check parse error rate:"
echo "  Total calls:  $(grep -c 'HTTP/1.1 200 OK' $LOG_FILE || echo 0)"
echo "  Parse errors: $(grep -c 'WARNING.*parse error' $LOG_FILE || echo 0)"

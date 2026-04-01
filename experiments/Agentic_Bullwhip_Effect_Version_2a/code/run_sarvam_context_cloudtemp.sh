#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# V2b full run — cloud-recommended temperatures on local llama-server
#
# Run this ONLY after the smoke test (run_sarvam_smoke_cloudtemp.sh) confirms
# parse error rate ≤ 10% per condition. If smoke fails (>20% errors), the
# cloud temperature recommendations do not transfer to local inference — skip
# this script and document the non-transfer finding instead.
#
# Cloud recommendations (Mar 2026):
#   Non-thinking mode (E1 context_lightweight): temp=0.2
#   Thinking mode (E2 context_reasoning):       temp=0.5
#
# Compare results against V2a (temp=1.0 for all) to answer:
#   "Do official API temperature recommendations transfer to local GGUF?"
#
# Model: sarvam-30b (both tiers, context conditions only)
# Results: ../results/sarvam_cloud_temp/
# Logs:    ../logs/
# Session: sarvam-v2b
#
# Timing estimates (NVIDIA GB10, Q4_K_M ~19GB):
#   Baselines: ~1 min  (deterministic, no LLM)
#   E1 context_lightweight (10 runs): ~8 hr
#   E2 context_reasoning   (10 runs): ~7 hr
#   Total: ~15 hours
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-v2b"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== V2b Full Run — Cloud Temperature Calibration ==="
echo "Backend: Local llama-server (sarvam-30b)"
echo "Env: .env.sarvam_cloud_temp (temp=0.2 E1, temp=0.5 E2)"
echo "Conditions: context only, 10 runs each"
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
LOG_FILE="../logs/sarvam_cloudtemp_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --conditions context \
    --runs 10 \
    --env .env.sarvam_cloud_temp \
    --results-dir ../results/sarvam_cloud_temp \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== V2b full run complete ==="
echo "Finished at: $(date)"
echo "Results: ../results/sarvam_cloud_temp/"
echo "Full log: $LOG_FILE"

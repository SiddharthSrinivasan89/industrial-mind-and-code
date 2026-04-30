#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Sarvam-30b context-only run — 10 runs per context condition, baselines + E1 + E2
#
# Blind conditions are excluded because sarvam-30b's minimal blind prompt
# produces a 22% per-call parse error rate (vs ~5% for context), causing
# ~95% of blind runs to fail. Context conditions were clean in the smoke test.
#
# Model: sarvam-30b (both lightweight and reasoning tiers)
# Results: ../results/sarvam/
# Logs:    ../logs/
# Session: sarvam-v2a
#
# Timing estimates (NVIDIA GB10, Q4_K_M ~19GB, ~40s/call avg):
#   Baselines: ~1 min  (deterministic, no LLM)
#   E1 context_lightweight (10 runs): ~8 hr  (720 calls × ~40s avg)
#   E2 context_reasoning   (10 runs): ~7 hr  (720 calls × ~33s avg)
#   Total: ~15 hours
# ---------------------------------------------------------------------------

set -euo pipefail

SESSION="sarvam-v2a"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# If not inside tmux, launch a new session and run this script inside it
if [ -z "${TMUX:-}" ]; then
    tmux new-session -d -s "$SESSION" "bash $(realpath "$0")"
    echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
    exit 0
fi

cd "$SCRIPT_DIR"

echo "=== Agentic Bullwhip V2a — Sarvam-30b Context-Only Run ==="
echo "Backend: Local llama-server (sarvam-30b)"
echo "Conditions: context only (blind excluded)"
echo "Runs per condition: 10"
echo "Results: ../results/sarvam/"
echo ""

# Check llama-server is running with sarvam-30b
if ! curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "ERROR: llama-server not running on :8080. Start with run_sarvam_server.sh"
    exit 1
fi

# Activate virtualenv if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

mkdir -p ../results/sarvam ../logs
LOG_FILE="../logs/sarvam_context_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --conditions context \
    --runs 10 \
    --env .env.sarvam \
    --results-dir ../results/sarvam \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== Context-only run complete ==="
echo "Finished at: $(date)"
echo "Results: ../results/sarvam/"
echo "Full log: $LOG_FILE"

#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Sarvam-30b full experiment run — 10 runs per condition, baselines + E1 + E2
#
# Model: sarvam-30b (both lightweight and reasoning tiers)
# Results: ../results/sarvam/
# Logs:    ../logs/
# Session: sarvam-v2a
#
# Timing estimates (NVIDIA GB10, Q4_K_M ~19GB, ~45s/call avg):
#   Baselines: ~1 min  (deterministic, no LLM)
#   E1 (sarvam-30b lightweight, 10 runs): ~18 hr  (1,440 calls × ~45s avg)
#   E2 (sarvam-30b reasoning,   10 runs): ~18 hr  (1,440 calls × ~45s avg)
#   Total: ~36 hours
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

echo "=== Agentic Bullwhip V2a — Sarvam-30b Full Run ==="
echo "Backend: Local Ollama (sarvam-30b)"
echo "Runs per condition: 10"
echo "Results: ../results/sarvam/"
echo ""

# Check Ollama is reachable
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434. Run: ollama serve"
    exit 1
fi

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
LOG_FILE="../logs/sarvam_run_$(date +%Y%m%dT%H%M%S).log"
echo "Logging to $LOG_FILE"
echo "Started at: $(date)"

nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --runs 10 \
    --env .env.sarvam \
    --results-dir ../results/sarvam \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== Full run complete ==="
echo "Finished at: $(date)"
echo "Results: ../results/sarvam/"
echo "Full log: $LOG_FILE"

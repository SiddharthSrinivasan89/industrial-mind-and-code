#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Start llama-server with sarvam-105b-Q4_K_M
#
# Prerequisites:
#   1. sarvam-30b server MUST be stopped first — run: tmux kill-session -t sarvam-server
#   2. 105b GGUF must be at /home/sid/models/llama-cpp-models/sarvam-105b-gguf/
#
# Memory: ~68 GiB unified (model 64.2 GiB + KV cache)
# Port: 8080 (same as 30b server — only one can run at a time)
# Session: sarvam-105b-server
# ---------------------------------------------------------------------------

set -euo pipefail

MODEL_DIR="/home/sid/models/llama-cpp-models/sarvam-105b-gguf"
MODEL_FILE="$MODEL_DIR/sarvam-105b-Q4_K_M.gguf-00001-of-00009.gguf"
LLAMA_SERVER="/home/sid/llama.cpp/build/bin/llama-server"
SESSION="sarvam-105b-server"

if [ ! -f "$MODEL_FILE" ]; then
    echo "ERROR: Model not found at $MODEL_FILE"
    echo "Run: huggingface-cli download sarvamai/sarvam-105b-gguf --local-dir $MODEL_DIR"
    echo "Model dir: $MODEL_DIR"
    exit 1
fi

if tmux has-session -t sarvam-server 2>/dev/null; then
    echo "ERROR: sarvam-30b server (sarvam-server) is still running."
    echo "Stop it first: tmux kill-session -t sarvam-server"
    exit 1
fi

echo "Starting sarvam-105b llama-server on :8080..."
tmux new-session -d -s "$SESSION" \
    "nohup $LLAMA_SERVER \
      -m $MODEL_FILE \
      --host 0.0.0.0 \
      --port 8080 \
      --ctx-size 65536 \
      --n-gpu-layers 999 \
      2>&1 | tee /tmp/llama-server-105b.log"

echo "Started in tmux session '$SESSION'. Attach with: tmux attach -t $SESSION"
echo "Wait ~60s for model to load, then check: curl http://localhost:8080/health"

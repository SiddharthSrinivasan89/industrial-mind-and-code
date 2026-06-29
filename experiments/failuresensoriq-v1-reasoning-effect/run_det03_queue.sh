#!/usr/bin/env bash
set -o pipefail
cd "$(dirname "$0")"
LOG="det03_run_$(date +%Y%m%d_%H%M%S).log"
for m in gemma3:4b phi4-mini; do
  echo "=== SMOKE $m @ temp 0.3 $(date) ===" | tee -a "$LOG"
  if python3 ihf_preflight.py --model "$m" --num-predict 2048 --temperature 0.3 2>&1 | tee -a "$LOG"; then
    echo "=== SMOKE PASS -> FULL $m $(date) ===" | tee -a "$LOG"
    python3 run_ihf.py --model "$m" --num-predict 2048 --temperature 0.3 2>&1 | tee -a "$LOG"
    echo "=== END $m $(date) ===" | tee -a "$LOG"
  else
    echo "=== SMOKE FAIL -> SKIP $m $(date) ===" | tee -a "$LOG"
  fi
done
echo "DET03 QUEUE DONE $(date)" | tee -a "$LOG"

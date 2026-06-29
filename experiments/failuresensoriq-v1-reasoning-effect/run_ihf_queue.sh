#!/usr/bin/env bash
cd "$(dirname "$0")"
LOG="ihf_run_$(date +%Y%m%d_%H%M%S).log"
for spec in "gemma3:4b 2048" "phi4-mini 2048"; do
  set -- $spec
  echo "=== START $1 $(date) ===" | tee -a "$LOG"
  python3 run_ihf.py --model "$1" --num-predict "$2" 2>&1 | tee -a "$LOG"
  echo "=== END $1 $(date) ===" | tee -a "$LOG"
done
echo "QUEUE DONE $(date)" | tee -a "$LOG"

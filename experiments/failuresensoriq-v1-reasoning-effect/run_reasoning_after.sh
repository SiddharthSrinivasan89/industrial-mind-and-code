#!/usr/bin/env bash
cd "$(dirname "$0")"
QLOG="ihf_run_20260623_233903.log"
# wait for the gemma + phi4-mini queue to finish
until grep -q "QUEUE DONE" "$QLOG" 2>/dev/null; do sleep 60; done
echo "=== START phi4-mini-reasoning (full) $(date) ===" | tee -a "$QLOG"
python3 run_ihf.py --model phi4-mini-reasoning --num-predict 16384 2>&1 | tee -a "$QLOG"
echo "=== END phi4-mini-reasoning $(date) ===" | tee -a "$QLOG"

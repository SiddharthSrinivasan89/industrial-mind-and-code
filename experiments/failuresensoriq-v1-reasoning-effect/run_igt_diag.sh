#!/usr/bin/env bash
cd "$(dirname "$0")"
LOG="igt_diag_$(date +%Y%m%d_%H%M%S).log"
echo "=== RUN1 industrial gas turbine (all) @ temp 0.3 $(date) ===" | tee -a "$LOG"
python3 run_ihf.py --model phi4-mini-reasoning --asset "industrial gas turbine" --temperature 0.3 --num-predict 16384 --no-gate 2>&1 | tee -a "$LOG"
echo "=== RUN2 industrial gas turbine (n200) @ temp 0.5 $(date) ===" | tee -a "$LOG"
python3 run_ihf.py --model phi4-mini-reasoning --asset "industrial gas turbine" --n 200 --temperature 0.5 --num-predict 16384 --no-gate 2>&1 | tee -a "$LOG"
echo "IGT DIAG DONE $(date)" | tee -a "$LOG"

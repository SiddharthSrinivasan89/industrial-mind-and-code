#!/usr/bin/env bash
# Cold-validator queue: wait for the GPU to free, then run each 8GB-tier model
# on the full single-answer set (2,667 Q), sequentially. Resumable per model.
set -u
cd "$(dirname "$0")"

MODELS=(gemma3:4b phi4-mini phi4-mini-reasoning)
LOG="queue_$(date +%Y%m%d_%H%M%S).log"
FREE_UTIL=25      # consider GPU free when util < this %
FREE_STREAK=6     # for this many consecutive 60s polls (~6 min sustained)

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

log "queue armed — models: ${MODELS[*]}"
log "waiting for GPU: util < ${FREE_UTIL}% for ${FREE_STREAK} consecutive polls"

streak=0
while true; do
  util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -1 | tr -d ' ')
  if [[ "$util" =~ ^[0-9]+$ ]] && [ "$util" -lt "$FREE_UTIL" ]; then
    streak=$((streak + 1))
  else
    streak=0
  fi
  log "util=${util}% streak=${streak}/${FREE_STREAK}"
  [ "$streak" -ge "$FREE_STREAK" ] && break
  sleep 60
done

log "GPU free — starting runs"
for m in "${MODELS[@]}"; do
  log "=== START $m (full) ==="
  python3 run_cold.py --model "$m" --full 2>&1 | tee -a "$LOG"
  log "=== END $m ==="
done
log "ALL DONE"

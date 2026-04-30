#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Azure smoke test — 1 run per condition, all experiments
#
# Purpose: verify Azure auth, model deployments, JSON parsing, and output
#          files before committing to a full 20-run production run.
#
# Usage:
#   chmod +x run_test_azure.sh
#   ./run_test_azure.sh
#
# Prerequisites:
#   - .env.azure configured — first-time setup: cp env.azure.template .env.azure
#     The template includes all required variables with inline documentation,
#     including the temperature design rationale (blind=0.0, context=0.3)
#     and a note that Azure forces o4-mini to temperature=1.0 regardless.
#
# Output: test_runs/<experiment>/<timestamp>/
#   records.parquet, summary.json, provenance.json
#
# What to check after the run:
#   - No ERROR lines in the log output
#   - summary.json has entries for every condition (both blind and context)
#   - chain_ovar is a real number (not NaN or null)
#   - provenance.json shows the correct model names and endpoint
# ---------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Agentic Bullwhip V2 — Azure Smoke Test ==="
echo "Backend: Azure (gpt-4.1-mini + o4-mini)"
echo "Runs per condition: 1"
echo "Output: test_runs/"
echo ""

# Activate virtualenv if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Preflight dependency check to fail fast with a clear message
python - <<'PY'
import importlib
missing=[]
for mod in ("pandas","numpy","pyarrow"):
    try:
        importlib.import_module(mod)
    except ModuleNotFoundError:
        missing.append(mod)
if missing:
    raise SystemExit("Missing Python dependencies: " + ", ".join(missing) + ". Install requirements.txt before running smoke tests.")
print("Dependency preflight passed.")
PY

LOG_FILE="test_runs/smoke_azure_$(date +%Y%m%dT%H%M%S).log"
mkdir -p test_runs
echo "Logging to $LOG_FILE"

# Run all experiments with 1 run each, using .env.azure, output to test_runs/
# nohup keeps the process alive if the terminal closes mid-run (remote client safety).
# This call is intentionally blocking — the shell waits for it to finish before
# running validation. To run in the background instead, add & and track the PID.
nohup python run_experiment.py \
    --experiments baselines E1 E2 \
    --runs 1 \
    --env .env.azure \
    --results-dir test_runs \
    > "$LOG_FILE" 2>&1

echo ""
echo "=== Smoke test complete. Results in test_runs/ ==="

# Extract exact run timestamps from the log — avoids race condition if another
# run lands in test_runs/ concurrently (ls -1t would pick the wrong directory).
BASELINES_TS=$(grep "baselines complete.*results at" "$LOG_FILE" | grep -o 'baselines/[0-9T]*' | cut -d/ -f2 | tail -1 || true)
E1_TS=$(grep "E1 complete.*results at" "$LOG_FILE" | grep -o 'E1/[0-9T]*' | cut -d/ -f2 | tail -1 || true)
E2_TS=$(grep "E2 complete.*results at" "$LOG_FILE" | grep -o 'E2/[0-9T]*' | cut -d/ -f2 | tail -1 || true)

if [ -z "$BASELINES_TS" ] || [ -z "$E1_TS" ] || [ -z "$E2_TS" ]; then
    echo "ERROR: Could not extract run timestamps from log. Check $LOG_FILE for failures." >&2
    exit 1
fi

python verify_smoke_outputs.py \
    --results-dir test_runs \
    --run-dirs "baselines=${BASELINES_TS}" "E1=${E1_TS}" "E2=${E2_TS}" \
    --runs 1

#!/bin/bash
# post_run_chain.sh — waits for Azure V6 production run, commits, then runs V6b.
# Run inside tmux with nohup. Fails loud with diagnostics; never auto-proceeds past a bad gate.

REPO_ROOT="$HOME/spark-dev-workspace/industrial-mind-and-code-dev"
CODE_DIR="$REPO_ROOT/experiments/Agentic_Bullwhip_Effect_V6_StatelessSwing/code"
AZURE_LOG="/tmp/v6_o4mini.log"
V6B_LOG="/tmp/v6b_chain.log"

log()  { echo "[$(date '+%Y-%m-%dT%H:%M:%S')] $*" | tee -a "$V6B_LOG"; }
fail() {
    log "FATAL: $*"
    log "--- Last 30 lines of V6B log ---"
    tail -30 "$V6B_LOG"
    exit 1
}

# ── Gate: verify smoke run quality from parquet ─────────────────────────────
# Usage: check_smoke <results_dir> <label>
# Checks: latency_ms > 0, fallback_rate < 100%, alpha varies across periods.
check_smoke() {
    local results_dir="$1"
    local label="$2"
    log "Checking smoke quality for $label in $results_dir..."
    python3 - <<PYEOF
import sys, pathlib, pandas as pd

results = pathlib.Path("$results_dir")
parquets = list(results.rglob("records.parquet"))
if not parquets:
    print(f"FAIL: no records.parquet found under {results}")
    sys.exit(1)

df = pd.concat([pd.read_parquet(p) for p in parquets], ignore_index=True)
label_df = df[df["label"] == "$label"] if "$label" in df.columns else df

issues = []

# 1. Latency must be non-zero for at least some LLM rows
if "latency_ms" in label_df.columns:
    nonzero = (label_df["latency_ms"] > 0).sum()
    if nonzero == 0:
        issues.append("all latency_ms are 0 — likely dry-run routing or dead backend")

# 2. Fallback rate must be < 100%
if "alpha_fallback" in label_df.columns:
    fallback_rate = label_df["alpha_fallback"].mean()
    if fallback_rate >= 1.0:
        issues.append(f"100% alpha_fallback — LLM parse failed every call (rate={fallback_rate:.2f})")
    elif fallback_rate > 0.3:
        issues.append(f"WARNING: high fallback rate {fallback_rate:.2f} (>30%) — check rationales")

# 3. Alpha must vary (not identical every period)
if "alpha_chosen" in label_df.columns:
    n_unique = label_df["alpha_chosen"].nunique()
    if n_unique <= 1:
        issues.append(f"alpha_chosen has only {n_unique} unique value(s) — no variation, likely stuck")

# 4. Rationale must be non-empty for at least some rows
if "rationale" in label_df.columns:
    non_empty = (label_df["rationale"].str.strip() != "").sum()
    if non_empty == 0:
        issues.append("all rationales are empty — model not generating explanations")

if issues:
    for iss in issues:
        print(f"  - {iss}")
    # Warnings don't block; only hard FAILs above exit(1)
    if any(i.startswith("FAIL") for i in issues):
        sys.exit(1)

latency_ok = (label_df['latency_ms'] > 0).sum() if 'latency_ms' in label_df.columns else 'n/a'
fallback_r = f"{label_df['alpha_fallback'].mean():.2f}" if 'alpha_fallback' in label_df.columns else 'n/a'
alpha_uniq = label_df['alpha_chosen'].nunique() if 'alpha_chosen' in label_df.columns else 'n/a'
print(f"  OK: {len(parquets)} parquet(s), {len(label_df)} rows, "
      f"latency_ms>0={latency_ok}, fallback_rate={fallback_r}, alpha_unique={alpha_uniq}")
PYEOF
    local rc=$?
    if [[ $rc -ne 0 ]]; then
        log "Smoke check FAILED for $label. Inspect $results_dir before proceeding."
        log "Aborting — do not proceed to production with a bad smoke."
        fail "Smoke gate failed for $label (exit $rc)"
    fi
}

# ── Gate: verify context_computed prompt has no calendar month ───────────────
check_dry_run_prompts() {
    log "Verifying V6b prompt output (context_computed must have no 'Current month:')..."
    python3 - <<PYEOF
import sys
sys.path.insert(0, "$CODE_DIR")
from agent_interface import build_alpha_user_prompt

# context_debiased: must have Current month, must NOT have seasonal rules text
p_deb = build_alpha_user_prompt(
    tier="OEM", condition="context_debiased", period=5,
    calendar_month="March",
    demand_history=[100, 110, 105, 108, 112],
    prev_forecast=107.0, forecast_error=3.0,
)
issues = []
if "Current month: March" not in p_deb:
    issues.append("context_debiased missing 'Current month: March'")
if "FY-end" in p_deb or "Diwali" in p_deb:
    issues.append("context_debiased still contains seasonal guidance (FY-end/Diwali)")

# context_computed: must NOT have Current month, must have computed signal lines
p_comp = build_alpha_user_prompt(
    tier="OEM", condition="context_computed", period=5,
    calendar_month="March",
    demand_history=[100, 110, 105, 108, 112],
    prev_forecast=107.0, forecast_error=3.0,
)
if "Current month:" in p_comp:
    issues.append("context_computed still contains 'Current month:' — month not replaced")
if "Demand trend" not in p_comp:
    issues.append("context_computed missing 'Demand trend' computed signal")
if "demand CV" not in p_comp:
    issues.append("context_computed missing 'demand CV' computed signal")
if "Last forecast error:" not in p_comp:
    issues.append("context_computed missing 'Last forecast error' line")
# Forecast error must not appear twice in context_computed
if p_comp.count("forecast error") > 2:
    issues.append("context_computed has duplicate forecast error lines")

if issues:
    for iss in issues:
        print(f"  FAIL: {iss}")
    sys.exit(1)

print("  OK: context_debiased has month, no seasonal rules.")
print("  OK: context_computed has computed signals, no calendar month.")
PYEOF
    local rc=$?
    [[ $rc -ne 0 ]] && fail "Dry-run prompt check failed — fix agent_interface.py before running live API calls"
}

# ── Find the most recent results dir for a given experiment label ────────────
latest_results() {
    ls -1d "$REPO_ROOT/experiments/Agentic_Bullwhip_Effect_V6_StatelessSwing/results/$1"/[0-9]* \
        2>/dev/null | sort | tail -1
}

# ===========================================================================
# STEP 1: Wait for Azure V6 production run to finish
# ===========================================================================
log "Waiting for Azure run to complete (monitoring $AZURE_LOG)..."
until grep -q "^EXIT:" "$AZURE_LOG" 2>/dev/null; do
    sleep 30
done
EXIT_CODE=$(grep "^EXIT:" "$AZURE_LOG" | tail -1 | cut -d: -f2)
log "Azure run finished with exit code: $EXIT_CODE"
[[ "$EXIT_CODE" != "0" ]] && fail "Azure production run exited non-zero ($EXIT_CODE) — check $AZURE_LOG"

# ===========================================================================
# STEP 2: Commit V6 results
# ===========================================================================
log "Committing V6 results to git..."
cd "$REPO_ROOT"
git add experiments/Agentic_Bullwhip_Effect_V6_StatelessSwing/
if git diff --cached --quiet; then
    log "Nothing new to commit for V6 — already committed, continuing."
else
    git commit -m "$(cat <<'EOF'
feat: add V6 StatelessSwing production results (mini_adaptive, o4mini_adaptive, oss120b_adaptive)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)" || fail "git commit failed"
    git push origin main || fail "git push failed"
    log "Commit and push complete."
fi

# ===========================================================================
# STEP 3: Dry runs — verify code paths before any live API call
# ===========================================================================
log "Running Azure dry run for mini_debiased..."
cd "$CODE_DIR"
DRY_RUN=1 python run_experiment.py --experiments mini_debiased --runs 2 --env .env.azure \
    >> "$V6B_LOG" 2>&1 || fail "Azure dry run failed — check $V6B_LOG"

log "Running local dry run for oss120b_debiased..."
DRY_RUN=1 python run_experiment.py --experiments oss120b_debiased --runs 2 --env .env.local \
    >> "$V6B_LOG" 2>&1 || fail "Local dry run failed — check $V6B_LOG"

# Verify prompt content is correct (context_computed has no calendar month, etc.)
check_dry_run_prompts

# Sleep to ensure smoke runs get a different UTC timestamp than dry runs
# (run_experiment.py uses UTC timestamp as directory name; same-second = collision = skip)
sleep 2

# ===========================================================================
# STEP 4: Azure smoke — mini_debiased (2 runs)
# ===========================================================================
log "Starting V6b Azure smoke: mini_debiased (2 runs)..."
python run_experiment.py --experiments mini_debiased --runs 2 --env .env.azure \
    >> "$V6B_LOG" 2>&1 || fail "Azure smoke run failed — check $V6B_LOG"

AZURE_SMOKE_DIR=$(latest_results "mini_debiased")
[[ -z "$AZURE_SMOKE_DIR" ]] && fail "No results directory found for mini_debiased after smoke"

check_smoke "$AZURE_SMOKE_DIR" "mini_ctx_debiased"
check_smoke "$AZURE_SMOKE_DIR" "mini_ctx_computed"

# ===========================================================================
# STEP 5: Local smoke — oss120b_debiased (2 runs)
# ===========================================================================
log "Starting V6b local smoke: oss120b_debiased (2 runs)..."
python run_experiment.py --experiments oss120b_debiased --runs 2 --env .env.local \
    >> "$V6B_LOG" 2>&1 || fail "Local smoke run failed — check $V6B_LOG"

LOCAL_SMOKE_DIR=$(latest_results "oss120b_debiased")
[[ -z "$LOCAL_SMOKE_DIR" ]] && fail "No results directory found for oss120b_debiased after smoke"

check_smoke "$LOCAL_SMOKE_DIR" "oss120b_ctx_debiased"
check_smoke "$LOCAL_SMOKE_DIR" "oss120b_ctx_computed"

# ===========================================================================
# STEP 6: verify_outputs across all results so far
# ===========================================================================
log "Running verify_outputs..."
python verify_outputs.py --results-dir ../results/ >> "$V6B_LOG" 2>&1 \
    || fail "verify_outputs failed after smokes — check $V6B_LOG before production"

log "All smoke gates passed. Proceeding to production."

# ===========================================================================
# STEP 7+8: Azure and local production — run in parallel
# ===========================================================================
log "Starting V6b production: mini_debiased (Azure) and oss120b_debiased (local) in parallel..."

python run_experiment.py --experiments mini_debiased --runs 5 --env .env.azure \
    >> "$V6B_LOG" 2>&1 &
AZURE_PID=$!

python run_experiment.py --experiments oss120b_debiased --runs 5 --env .env.local \
    >> "$V6B_LOG" 2>&1 &
LOCAL_PID=$!

wait $AZURE_PID || fail "Azure production run failed — check $V6B_LOG"
log "Azure production complete."

wait $LOCAL_PID || fail "Local production run failed — check $V6B_LOG"
log "Local production complete."

# ===========================================================================
# STEP 9: Commit V6b results
# ===========================================================================
log "Committing V6b results to git..."
cd "$REPO_ROOT"
git add experiments/Agentic_Bullwhip_Effect_V6_StatelessSwing/
git commit -m "$(cat <<'EOF'
feat: add V6b context_debiased and context_computed results (mini + oss120b)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)" || fail "git commit failed for V6b"
git push origin main || fail "git push failed for V6b"
log "V6b results committed and pushed."

log "=== Chain complete ==="

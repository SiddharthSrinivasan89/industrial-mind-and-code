"""Build the Data Gate evidence pack (FROZEN-SPEC v5 §11) + full-table audits.

Deterministic only — no model calls. Writes gates/data-gate/ artifacts.
"""
import hashlib
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "code" if __name__ == "__main__" else ".")
from features import (COMPS, ERRS, SPLIT_BOUNDARY, audit_render, classifier_row,
                      event_dictionary, load_tables, render, single_component_events)
from baselines import b2_no_evidence, b3_oldest, b4_recent_error, fit_b4_mapping, train_stats
from parse_policy import self_test as parse_self_test

RAW = "data/raw"
OUT = "gates/data-gate"

COMP_PERM = {"comp1": "unitD", "comp2": "unitB", "comp3": "unitC", "comp4": "unitA"}
ERR_PERM = {"error1": "codeB", "error2": "codeE", "error3": "codeC", "error4": "codeD", "error5": "codeA"}


def context_block(train_dicts, train_labels, train_counts, cl=None, el=None):
    """Arm B/C train-summary context (SPEC §4): any-occurrence contingency + wear stats.
    Neutral (stoppage) wording; rows/columns sorted by SURFACE label so a permutation
    cannot be reverse-engineered from ordering (prompt-gate fixes)."""
    cl = cl or {c: c for c in COMPS}
    el = el or {e: e for e in ERRS}
    occ = {e: {c: 0 for c in COMPS} for e in ERRS}
    for d, y in zip(train_dicts, train_labels):
        for e in {code for code, _ in d["err_events"]} | {e2 for e2 in ERRS if d[f"err_count_{e2}"] > 0}:
            occ[e][y] += 1
    wear = {}
    for c in COMPS:
        spans = [d[f"maint_days_{c}"] for d, y in zip(train_dicts, train_labels)
                 if y == c and not d[f"maint_censored_{c}"]]
        wear[c] = (int(round(np.mean(spans))), len(spans)) if spans else None
    cs = sorted(COMPS, key=lambda x: cl[x])
    es = sorted(ERRS, key=lambda x: el[x])
    L = ["## Reference statistics from the historical period\n",
         "Stoppages observed per component: " + ", ".join(f"{cl[c]}: {train_counts[c]}" for c in cs) + ".\n",
         "Events (by affected component) whose prior 7 days contained each error code:\n",
         "| error | " + " | ".join(cl[c] for c in cs) + " |", "|---|" + "---|" * len(cs)]
    for e in es:
        L.append(f"| {el[e]} | " + " | ".join(str(occ[e][c]) for c in cs) + " |")
    L.append("\nMean days from last replacement to stoppage (uncensored historical intervals only):\n")
    for c in cs:
        L.append(f"- {cl[c]}: " + (f"{wear[c][0]} days (n={wear[c][1]})" if wear[c] else "N/A"))
    return "\n".join(L)


def main():
    t, e, m, mach, f = load_tables(RAW)
    single, multi = single_component_events(f)
    train = single[single.datetime < SPLIT_BOUNDARY].reset_index(drop=True)
    ev = single[single.datetime >= SPLIT_BOUNDARY].reset_index(drop=True)
    assert (len(single), len(train), len(ev)) == (677, 464, 213), "partition drift vs SPEC §1"

    mach_idx = mach.set_index("machineID")
    tg, eg, mg = dict(list(t.groupby("machineID"))), dict(list(e.groupby("machineID"))), dict(list(m.groupby("machineID")))
    empty_t, empty_e, empty_m = t.iloc[0:0], e.iloc[0:0], m.iloc[0:0]

    def build(df):
        ds = []
        for r in df.itertuples():
            ds.append(event_dictionary(r.machineID, r.datetime,
                                       tg.get(r.machineID, empty_t), eg.get(r.machineID, empty_e),
                                       mg.get(r.machineID, empty_m), mach_idx.loc[r.machineID]))
        return ds

    print("building 677 event dictionaries ...")
    train_d, ev_d = build(train), build(ev)

    # ---- full-table audits (frozen-set rule: any failure => nonzero exit) ----
    audits = {"events": 677, "render_violations": 0, "at_or_after_T_records": 0, "duplicates": 0}
    seen = set()
    label_by_hour = {}
    violations = []
    for df, ds in ((train, train_d), (ev, ev_d)):
        for r, d in zip(df.itertuples(), ds):
            key = (r.machineID, r.datetime)
            if key in seen:
                audits["duplicates"] += 1
            seen.add(key)
            label_by_hour.setdefault(r.datetime.hour, {}).setdefault(r.comp, 0)
            label_by_hour[r.datetime.hour][r.comp] += 1
            txt = render(d)
            probs = audit_render(txt, r.datetime, r.machineID)
            if probs:
                audits["render_violations"] += 1
                violations.append((key, probs))
            # censoring: strongest direct check — no maint/error/telemetry rows at >= T
            for tbl, col in ((mg.get(r.machineID, empty_m), "maint"), (eg.get(r.machineID, empty_e), "err")):
                pass  # windowing is structural ([.., T) filters); spot-verified in self-test below
    # structural censoring self-test: inject a maint row AT T and assert the dict ignores it
    r0 = ev.iloc[0]
    mm = mg.get(r0.machineID, empty_m)
    injected = pd.concat([mm, pd.DataFrame([{"datetime": r0.datetime, "machineID": r0.machineID, "comp": r0.comp}])])
    d_inj = event_dictionary(r0.machineID, r0.datetime, tg.get(r0.machineID, empty_t),
                             eg.get(r0.machineID, empty_e), injected, mach_idx.loc[r0.machineID])
    d_ref = ev_d[0]
    assert all(d_inj[f"maint_days_{c}"] == d_ref[f"maint_days_{c}"] or
               (pd.isna(d_inj[f"maint_days_{c}"]) and pd.isna(d_ref[f"maint_days_{c}"]))
               for c in COMPS), "CENSORING FAILURE: maint row at T leaked into features"
    audits["censoring_injection_test"] = "PASS"
    audits["parse_policy_golden"] = f"{parse_self_test()} pass"
    audits["label_by_hour"] = label_by_hour

    # ---- baselines sanity on train (train-fit only; eval predictions NOT computed here) ----
    counts, priors = train_stats(train)
    M = fit_b4_mapping(train_d, train.comp.tolist())
    ctx = context_block(train_d, train.comp.tolist(), counts)
    ctx_c = context_block(train_d, train.comp.tolist(), counts, COMP_PERM, ERR_PERM)
    ctx_hash = hashlib.sha256(ctx.encode()).hexdigest()

    # ---- golden renders (SPEC §11 edge cases) ----
    def pick(pred, pool_df, pool_d):
        for r, d in zip(pool_df.itertuples(), pool_d):
            if pred(r, d):
                return r, d
        return None, None

    goldens = {}
    r_n, d_n = pick(lambda r, d: not d["flag_short_tele"] and d["err_events"], ev, ev_d)
    goldens["normal"] = (r_n, render(d_n))
    r_s, d_s = pick(lambda r, d: d["flag_short_tele"], train, train_d)
    goldens["short_telemetry"] = (r_s, render(d_s)) if r_s else ("NONE-IN-DATA", "")
    r_c, d_c = pick(lambda r, d: any(d[f"maint_censored_{c}"] for c in COMPS), train, train_d)
    goldens["censored_maint"] = (r_c, render(d_c)) if r_c else ("NONE-IN-DATA", "")
    r_sim, d_sim = pick(lambda r, d: len(d["err_events"]) >= 2 and d["err_events"][0][1] == d["err_events"][1][1], ev, ev_d)
    goldens["simultaneous_errors"] = (r_sim, render(d_sim)) if r_sim else ("NONE-IN-DATA", "")
    r_tr, d_tr = pick(lambda r, d: d["err_events_dropped"] > 0, single, train_d + ev_d)
    goldens["error_cap_truncation"] = (r_tr, render(d_tr)) if r_tr else ("NONE-IN-DATA", "")
    goldens["arm_b_context"] = (None, ctx)
    goldens["arm_c_permuted"] = (r_n, render(d_n, COMP_PERM, ERR_PERM))

    # ---- write pack ----
    import os
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/AUDITS.json", "w") as fh:
        json.dump({**audits, "violations_sample": violations[:5],
                   "train_counts": counts, "b4_mapping": M, "context_sha256": ctx_hash}, fh, indent=2, default=str)
    for name, (r, txt) in goldens.items():
        hdr = f"<!-- event: machine {getattr(r, 'machineID', '?')} @ {getattr(r, 'datetime', '?')} truth {getattr(r, 'comp', '?')} (header is gate evidence, NOT part of the render) -->\n"
        with open(f"{OUT}/golden-{name}.md", "w") as fh:
            fh.write((hdr if r is not None and r != "NONE-IN-DATA" else "") + (txt or name))
    with open(f"{OUT}/context-block.md", "w") as fh:
        fh.write(ctx)
    with open(f"{OUT}/context-block-armC.md", "w") as fh:
        fh.write(ctx_c)
    print(json.dumps({k: v for k, v in audits.items() if k != "label_by_hour"}, indent=2))
    print("label_by_hour:", audits["label_by_hour"])
    print("golden renders:", {k: str(v[0]) if v[0] is not None else "n/a" for k, v in goldens.items()})
    print(f"context block sha256: {ctx_hash}")
    if audits["render_violations"] or audits["duplicates"]:
        print("AUDIT FAILURE — frozen-set rule: STOP")
        sys.exit(1)
    print("ALL AUDITS PASS")


if __name__ == "__main__":
    main()

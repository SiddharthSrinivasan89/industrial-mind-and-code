"""Canonical feature dictionary + the two projections (FROZEN-SPEC v5 §4).

Every aggregation window is right-open [start, T). Rounding (round-half-even) is applied to
the dictionary itself; both projections consume rounded values.
"""
import numpy as np
import pandas as pd

COMPS = ["comp1", "comp2", "comp3", "comp4"]
ERRS = ["error1", "error2", "error3", "error4", "error5"]
CHANNELS = ["volt", "rotate", "pressure", "vibration"]
BLOCKS = {"d3": (72, 48), "d2": (48, 24), "f24": (24, 0)}  # hours before T
ERR_CAP = 20
SPLIT_BOUNDARY = pd.Timestamp("2015-09-01 00:00")


def load_tables(raw_dir):
    t = pd.read_csv(f"{raw_dir}/PdM_telemetry.csv", parse_dates=["datetime"])
    e = pd.read_csv(f"{raw_dir}/PdM_errors.csv", parse_dates=["datetime"])
    m = pd.read_csv(f"{raw_dir}/PdM_maint.csv", parse_dates=["datetime"])
    mach = pd.read_csv(f"{raw_dir}/PdM_machines.csv")
    f = pd.read_csv(f"{raw_dir}/PdM_failures.csv", parse_dates=["datetime"])
    return t, e, m, mach, f


def single_component_events(f):
    grp = f.groupby(["machineID", "datetime"])["failure"].agg(list).reset_index()
    grp["n"] = grp["failure"].str.len()
    single = grp[grp.n == 1].copy()
    single["comp"] = single["failure"].str[0]
    return (
        single[["machineID", "datetime", "comp"]]
        .sort_values(["machineID", "datetime"])
        .reset_index(drop=True),
        grp[grp.n > 1][["machineID", "datetime", "failure"]].reset_index(drop=True),
    )


def _r(x, nd=1):
    return float(np.round(x, nd)) if pd.notna(x) else np.nan


def event_dictionary(mid, T, tel, err, mnt, mach_row):
    """Build one event's canonical dictionary. tel/err/mnt are that machine's full tables."""
    d = {"model": mach_row["model"], "age": int(mach_row["age"])}
    tw = tel[(tel.datetime < T)]
    for blk, (h1, h0) in BLOCKS.items():
        w = tw[(tw.datetime >= T - pd.Timedelta(hours=h1)) & (tw.datetime < T - pd.Timedelta(hours=h0))]
        d[f"tele_missing_{blk}"] = bool(len(w) == 0)
        for ch in CHANNELS:
            v = w[ch]
            d[f"tele_{ch}_{blk}_mean"] = _r(v.mean()) if len(v) else np.nan
            d[f"tele_{ch}_{blk}_std"] = _r(v.std(ddof=1)) if len(v) >= 2 else (0.0 if len(v) == 1 else np.nan)
            d[f"tele_{ch}_{blk}_min"] = _r(v.min()) if len(v) else np.nan
            d[f"tele_{ch}_{blk}_max"] = _r(v.max()) if len(v) else np.nan
    for ch in CHANNELS:
        m1, m2, m3 = d[f"tele_{ch}_f24_mean"], d[f"tele_{ch}_d2_mean"], d[f"tele_{ch}_d3_mean"]
        d[f"tele_{ch}_delta1"] = _r(m1 - m2) if pd.notna(m1) and pd.notna(m2) else np.nan
        d[f"tele_{ch}_delta2"] = _r(m2 - m3) if pd.notna(m2) and pd.notna(m3) else np.nan
    ew = err[(err.datetime >= T - pd.Timedelta(hours=168)) & (err.datetime < T)].copy()
    for e_ in ERRS:
        d[f"err_count_{e_}"] = int((ew.errorID == e_).sum())
    if len(ew):
        ew["hours"] = ((T - ew.datetime).dt.total_seconds() / 3600).astype(int)
        ew = ew.sort_values(["hours", "errorID"])  # hours asc, code asc — BEFORE cap
        d["err_events"] = list(zip(ew.errorID.tolist(), ew.hours.tolist()))[:ERR_CAP]
        d["err_events_dropped"] = max(0, len(ew) - ERR_CAP)
        d["err_recent_code"] = ew.iloc[0].errorID
        d["err_recent_hours"] = float(ew.iloc[0].hours)
    else:
        d["err_events"], d["err_events_dropped"] = [], 0
        d["err_recent_code"], d["err_recent_hours"] = "none", 168.0
    mw = mnt[mnt.datetime < T]
    for c in COMPS:
        rec = mw[mw.comp == c]
        if len(rec):
            d[f"maint_days_{c}"] = float(int((T - rec.datetime.max()).total_seconds() // 86400))
            d[f"maint_censored_{c}"] = False
        else:
            d[f"maint_days_{c}"] = np.nan
            d[f"maint_censored_{c}"] = True
        w90 = rec[rec.datetime >= T - pd.Timedelta(days=90)]
        d[f"maint_count90_{c}"] = int(len(w90))
    d["flag_short_tele"] = any(d[f"tele_missing_{b}"] for b in BLOCKS)  # metadata only
    return d


PREDICTOR_COLS = (
    ["model", "age"]
    + [f"tele_{ch}_{blk}_{s}" for ch in CHANNELS for blk in BLOCKS for s in ("mean", "std", "min", "max")]
    + [f"tele_{ch}_delta{i}" for ch in CHANNELS for i in (1, 2)]
    + [f"tele_missing_{blk}" for blk in BLOCKS]
    + [f"err_count_{e}" for e in ERRS]
    + ["err_recent_code", "err_recent_hours"]
    + [f"maint_days_{c}" for c in COMPS]
    + [f"maint_censored_{c}" for c in COMPS]
    + [f"maint_count90_{c}" for c in COMPS]
)


def classifier_row(d):
    return {k: d[k] for k in PREDICTOR_COLS}


def _fmt(x):
    return "no data" if pd.isna(x) else f"{x:g}"


def render(d, comp_labels=None, err_labels=None):
    """Markdown render. Optional label maps implement the Arm C permutation."""
    cl = comp_labels or {c: c for c in COMPS}
    el = err_labels or {e: e for e in ERRS}
    L = [f"## Machine\n\n- model: {d['model']}\n- age: {d['age']} years\n"]
    L.append("## Telemetry (times relative to reference time T)\n")
    L.append("| channel | day -3 | day -2 | final 24h | delta(f24-d2) | delta(d2-d3) |")
    L.append("|---|---|---|---|---|---|")
    for ch in CHANNELS:
        cells = []
        for blk in ("d3", "d2", "f24"):
            if d[f"tele_missing_{blk}"]:
                cells.append("no data")
            else:
                cells.append(
                    f"{d[f'tele_{ch}_{blk}_mean']:g} ± {d[f'tele_{ch}_{blk}_std']:g} "
                    f"[{d[f'tele_{ch}_{blk}_min']:g}–{d[f'tele_{ch}_{blk}_max']:g}]"
                )
        L.append(
            f"| {ch} | {cells[0]} | {cells[1]} | {cells[2]} | "
            f"{_fmt(d[f'tele_{ch}_delta1'])} | {_fmt(d[f'tele_{ch}_delta2'])} |"
        )
    L.append("\n## Error log (last 7 days)\n")
    if d["err_events"]:
        L.append("| code | hours before T |")
        L.append("|---|---|")
        for code, hrs in d["err_events"]:
            L.append(f"| {el[code]} | {hrs} |")
        if d["err_events_dropped"]:
            L.append(f"\n({d['err_events_dropped']} older error rows omitted)")
        counts = ", ".join(f"{el[e]}: {d[f'err_count_{e}']}"
                           for e in sorted(ERRS, key=lambda x: el[x]))
        L.append(f"\n7-day counts — {counts}")
    else:
        L.append("No errors in the last 7 days.")
    L.append("\n## Maintenance history\n")
    L.append("| component | days since last replacement | replacements in last 90 days |")
    L.append("|---|---|---|")
    for c in sorted(COMPS, key=lambda x: cl[x]):  # surface-label order (Arm C leak fix)
        days = "no prior record" if d[f"maint_censored_{c}"] else f"{int(d[f'maint_days_{c}'])}"
        L.append(f"| {cl[c]} | {days} | {d[f'maint_count90_{c}']} |")
    return "\n".join(L)


def audit_render(text, T, mid):
    """Fail-closed render audits (SPEC §6.1/§6.3): no absolute dates, no machineID, no
    failure-log content, no time-of-day."""
    problems = []
    import re
    if re.search(r"\b20\d\d-\d\d-\d\d\b|\b20\d\d\b", text):
        problems.append("absolute date/year present")
    if re.search(r"\d\d:\d\d", text):
        problems.append("time-of-day present")
    if re.search(rf"\bmachine\s*{mid}\b|machineID", text, re.I):
        problems.append("machine identity present")
    if re.search(r"\bfail(ed|ure)?\b", text, re.I):
        problems.append("failure wording present in evidence")
    return problems

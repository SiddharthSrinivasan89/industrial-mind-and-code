"""Confirmatory analysis (FROZEN-SPEC v5 §§5-6): macro-F1 + accuracy with machine-cluster
bootstrap CIs; H1 (IUT), H2 (IUT), H2b (descriptive gap + cap). Primaries confirmatory; local
ladder exploratory. Fast numpy-native cluster bootstrap. No model calls.
"""
import json
import glob
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
COMPS = ["comp1", "comp2", "comp3", "comp4"]
UNITS = ["unitA", "unitB", "unitC", "unitD"]
PRIMARIES = ["gpt-5.4", "gpt-oss_120b", "nemotron-3-super_120b"]  # nemotron promoted post-hoc (Sid 2026-07-19); see SPEC amendment
B = 10000


def load(subj, arm):
    p = RES / f"{subj}_arm{arm}" / "records.jsonl"
    if not p.exists():
        return None
    df = pd.DataFrame(json.loads(l) for l in p.read_text().splitlines())
    df["pred"] = df["pred"].where(df["pred"].notna(), "__invalid__")  # SPEC §9/§13: invalid=wrong
    df["machine"] = df.event_id.str.split("@").str[0].astype(int)
    return df[["event_id", "machine", "truth", "pred"]]


def idx(labels):
    return {l: i for i, l in enumerate(labels)}


def per_machine_conf(df, labels):
    """Return machines list, per-machine 4x4 confusion (true x pred, valid preds only),
    and per-machine true-class totals (incl. invalid preds -> FN)."""
    li = idx(labels)
    machs = sorted(df.machine.unique())
    K = len(labels)
    conf = np.zeros((len(machs), K, K))
    truetot = np.zeros((len(machs), K))
    for mi, m in enumerate(machs):
        s = df[df.machine == m]
        for t, p in zip(s.truth, s.pred):
            ti = li[t]
            truetot[mi, ti] += 1
            if p in li:
                conf[mi, ti, li[p]] += 1
    return np.array(machs), conf, truetot


def macro_f1_from(conf_sum, truetot_sum):
    tp = np.diagonal(conf_sum, axis1=-2, axis2=-1)          # (...,K)
    pred_tot = conf_sum.sum(axis=-2)                         # (...,K)
    with np.errstate(divide="ignore", invalid="ignore"):
        prec = np.where(pred_tot > 0, tp / pred_tot, 0.0)
        rec = np.where(truetot_sum > 0, tp / truetot_sum, 0.0)
        f1 = np.where(prec + rec > 0, 2 * prec * rec / (prec + rec), 0.0)
    return f1.mean(axis=-1)


def boot_f1(df, labels, seed):
    machs, conf, truetot = per_machine_conf(df, labels)
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(machs), (B, len(machs)))
    cs = conf[pick].sum(axis=1)           # (B,K,K)
    ts = truetot[pick].sum(axis=1)        # (B,K)
    point = macro_f1_from(conf.sum(0), truetot.sum(0))
    return point, macro_f1_from(cs, ts)


def paired_boot_f1_diff(dfa, dfb, labels, seed):
    """dfa vs dfb aligned on event_id; same machine resample; returns (point_diff, dist)."""
    m = dfa.merge(dfb[["event_id", "pred"]], on="event_id", suffixes=("_a", "_b"))
    machs = sorted(m.machine.unique())
    K = len(labels); li = idx(labels)
    ca = np.zeros((len(machs), K, K)); cb = np.zeros((len(machs), K, K)); tt = np.zeros((len(machs), K))
    for mi, mm in enumerate(machs):
        s = m[m.machine == mm]
        for t, pa, pb in zip(s.truth, s.pred_a, s.pred_b):
            ti = li[t]; tt[mi, ti] += 1
            if pa in li: ca[mi, ti, li[pa]] += 1
            if pb in li: cb[mi, ti, li[pb]] += 1
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(machs), (B, len(machs)))
    da = macro_f1_from(ca[pick].sum(1), tt[pick].sum(1)) - macro_f1_from(cb[pick].sum(1), tt[pick].sum(1))
    point = macro_f1_from(ca.sum(0), tt.sum(0)) - macro_f1_from(cb.sum(0), tt.sum(0))
    return point, da


def one_sided_p(dist):
    return float((1 + np.sum(dist <= 0)) / (B + 1))


def main():
    rep = {"metrics": {}, "H1": {}, "H2": {}, "H2b": {}, "notes": {}}
    cls = pd.read_csv(RES / "classical" / "predictions.csv")
    champ = json.loads((RES / "classical" / "summary.json").read_text())["champion"]
    base = {b: cls[["event_id", "truth", b]].rename(columns={b: "pred"}).assign(
                machine=cls.event_id.str.split("@").str[0].astype(int))
            for b in ["b2_no_evidence", "b3_oldest", "b4_recent_error", "champion"]}

    # point metrics for all arms + baselines
    for f in sorted(glob.glob(str(RES / "*_arm*" / "records.jsonl"))):
        name = Path(f).parent.name; subj, arm = name.rsplit("_arm", 1)
        df = load(subj, arm); labels = UNITS if arm == "C" else COMPS
        pt, dist = boot_f1(df, labels, 20260720)
        rep["metrics"][name] = {"n": len(df), "machines": int(df.machine.nunique()),
                                "accuracy": float((df.truth == df.pred).mean()),
                                "macro_f1": float(pt),
                                "macro_f1_ci95": [float(np.percentile(dist, 2.5)), float(np.percentile(dist, 97.5))]}
    for b, d in base.items():
        pt, dist = boot_f1(d, COMPS, 20260720)
        rep["metrics"][f"baseline_{b}"] = {"n": len(d), "accuracy": float((d.truth == d.pred).mean()),
                                           "macro_f1": float(pt),
                                           "macro_f1_ci95": [float(np.percentile(dist, 2.5)), float(np.percentile(dist, 97.5))]}

    # H1: each primary Arm A vs B2/B3/B4 (IUT max-p, then Holm over 2 subjects)
    seeds = {"gpt-5.4": 20260721, "gpt-oss_120b": 20260724, "nemotron-3-super_120b": 20260731}
    subj_p = {}
    for subj in PRIMARIES:
        a = load(subj, "A")
        if a is None:
            continue
        ps = {}
        for i, b in enumerate(["b2_no_evidence", "b3_oldest", "b4_recent_error"]):
            _, dist = paired_boot_f1_diff(a, base[b], COMPS, seeds[subj] + i)
            ps[b] = one_sided_p(dist)
        subj_p[subj] = max(ps.values()); rep["H1"][subj] = {"per_baseline_p": ps, "subject_IUT_p": subj_p[subj]}
    ordered = sorted(subj_p.items(), key=lambda kv: kv[1])
    nsub = len(ordered)
    holm = {s: min(p * (nsub - r), 1.0) for r, (s, p) in enumerate(ordered)}
    rep["H1"]["holm_adjusted"] = holm
    rep["H1"]["supported_subjects"] = [s for s, v in holm.items() if v < 0.05]
    rep["H1"]["verdict"] = "supported" if rep["H1"]["supported_subjects"] else "not supported"

    # H2: champion vs each primary Arm B (both raw p<0.05)
    h2p = {}
    for subj in PRIMARIES:
        _, dist = paired_boot_f1_diff(base["champion"], load(subj, "B"), COMPS, 20260720)
        h2p[subj] = one_sided_p(dist)
    rep["H2"] = {"raw_p": h2p, "verdict": "supported" if all(p < 0.05 for p in h2p.values()) else "not supported"}

    # H2b: Arm B vs C on probe, descriptive accuracy gap + 90% CI + cap
    for subj in PRIMARIES:
        c = load(subj, "C")
        if c is None: continue
        bB = load(subj, "B")
        m = c.merge(bB[["event_id", "truth"]], on="event_id", suffixes=("", "_b"))
        m["c_ok"] = (c.set_index("event_id").loc[m.event_id, "truth"].values == m.pred.values)
        # correct flags aligned
        cc = c.assign(ok=(c.truth == c.pred))[["event_id", "machine", "ok"]]
        bb = bB.assign(ok=(bB.truth == bB.pred))[["event_id", "ok"]]
        mm = cc.merge(bb, on="event_id", suffixes=("_c", "_b"))
        machs = sorted(mm.machine.unique())
        per = {x: mm[mm.machine == x] for x in machs}
        rng = np.random.default_rng(20260720); gaps = []
        for _ in range(B):
            s = pd.concat([per[x] for x in rng.choice(machs, len(machs), replace=True)])
            gaps.append(s.ok_b.mean() - s.ok_c.mean())
        gap = mm.ok_b.mean() - mm.ok_c.mean(); lo, hi = np.percentile(gaps, [5, 95])
        rep["H2b"][subj] = {"n_probe": len(mm), "armB_acc": float(mm.ok_b.mean()),
                            "armC_acc": float(mm.ok_c.mean()), "gap": float(gap),
                            "ci90": [float(lo), float(hi)], "cap_triggered": bool(gap > 0.10 and lo > 0)}

    (RES / "ANALYSIS.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()

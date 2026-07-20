"""Classical arm: champion selection, granularity gate, label-shuffle gate, baselines
(FROZEN-SPEC v5 §§7–8). Deterministic + local sklearn only — no model calls.

    python3 code/run_classical.py            # selection + gates + eval predictions
    python3 code/run_classical.py --skip-shuffle-gate   # (debug only, not canonical)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from features import COMPS, SPLIT_BOUNDARY, PREDICTOR_COLS, classifier_row, event_dictionary, load_tables, single_component_events
from baselines import b1_prior_random, b2_no_evidence, b3_oldest, b4_recent_error, fit_b4_mapping, train_stats

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import sklearn

RAW = str(HERE.parent / "data" / "raw")
OUT = HERE.parent / "results" / "classical"
TUNE_BOUNDARY = pd.Timestamp("2015-07-01")
CAT = ["model", "err_recent_code"]
NUM = [c for c in PREDICTOR_COLS if c not in CAT]


def macro_f1(y, p):
    return f1_score(y, p, labels=COMPS, average="macro", zero_division=0)


def build_all():
    t, e, m, mach, f = load_tables(RAW)
    single, _ = single_component_events(f)
    tg, eg, mg = dict(list(t.groupby("machineID"))), dict(list(e.groupby("machineID"))), dict(list(m.groupby("machineID")))
    mach_idx = mach.set_index("machineID")
    et, ee, em = t.iloc[0:0], e.iloc[0:0], m.iloc[0:0]
    dicts = [event_dictionary(r.machineID, r.datetime, tg.get(r.machineID, et),
                              eg.get(r.machineID, ee), mg.get(r.machineID, em), mach_idx.loc[r.machineID])
             for r in single.itertuples()]
    X = pd.DataFrame([classifier_row(d) for d in dicts])
    X[[c for c in NUM if X[c].dtype == bool]] = X[[c for c in NUM if X[c].dtype == bool]].astype(float)
    y = single.comp
    return single, dicts, X, y


def candidates():
    for C in (0.01, 0.1, 1, 10):
        pre = ColumnTransformer([
            ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), NUM),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CAT)])
        yield f"logreg_C{C}", Pipeline([("pre", pre),
            ("clf", LogisticRegression(C=C, class_weight="balanced", solver="lbfgs", max_iter=2000))])
    for lr in (0.05, 0.1):
        for depth in (2, 3):
            for it in (100, 300):
                pre = ColumnTransformer([("num", "passthrough", NUM),
                                         ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT)])
                yield f"hgb_lr{lr}_d{depth}_i{it}", Pipeline([("pre", pre),
                    ("clf", HistGradientBoostingClassifier(learning_rate=lr, max_depth=depth,
                                                           max_iter=it, random_state=0))])


def fit_weighted(pipe, X, y):
    name = type(pipe.named_steps["clf"]).__name__
    if name == "HistGradientBoostingClassifier":
        w = y.map(1.0 / y.value_counts(normalize=True))
        pipe.fit(X, y, clf__sample_weight=w.values)
    else:
        pipe.fit(X, y)
    return pipe


def select(Xf, yf, Xt, yt):
    scores = {}
    for name, pipe in candidates():
        fit_weighted(pipe, Xf, yf)
        scores[name] = macro_f1(yt, pipe.predict(Xt))
    best = max(scores.values())
    winners = [k for k, v in scores.items() if v == best]
    champ = sorted(winners, key=lambda k: (not k.startswith("logreg"), k))[0]  # tie -> logreg
    return champ, scores


def make(name):
    for n, p in candidates():
        if n == name:
            return p
    raise KeyError(name)


def main(skip_shuffle):
    OUT.mkdir(parents=True, exist_ok=True)
    single, dicts, X, y = build_all()
    is_train = single.datetime < SPLIT_BOUNDARY
    is_fit = single.datetime < TUNE_BOUNDARY
    is_tune = is_train & ~is_fit
    Xf, yf = X[is_fit], y[is_fit]
    Xt, yt = X[is_tune], y[is_tune]
    Xtr, ytr = X[is_train], y[is_train]
    Xe, ye = X[~is_train], y[~is_train]
    ev = single[~is_train].reset_index(drop=True)
    print(f"fit {len(Xf)}, tune {len(Xt)}, train {len(Xtr)}, eval {len(Xe)}; sklearn {sklearn.__version__}")

    counts, priors = train_stats(single[is_train])
    b2 = b2_no_evidence(counts)

    champ_name, scores = select(Xf, yf, Xt, yt)
    tune_champ = scores[champ_name]
    tune_b2 = macro_f1(yt, [b2] * len(yt))
    gate_granularity = tune_champ - tune_b2 >= 0.05
    print(f"champion {champ_name} tune macro-F1 {tune_champ:.4f} vs no-evidence {tune_b2:.4f} "
          f"-> granularity gate {'PASS' if gate_granularity else 'FAIL'}")
    if not gate_granularity:
        print("ATTEMPT-1 GRANULARITY FAIL — STOP (ladder attempt 2 requires design amendment path)")
        sys.exit(1)

    shuffle = {"run": False}
    if not skip_shuffle:
        nulls = []
        for i in range(200):
            rng = np.random.default_rng(20260722 + i)
            ys = pd.Series(rng.permutation(yf.values), index=yf.index)
            _, s = select(Xf, ys, Xt, yt)
            nulls.append(max(s.values()))
            if (i + 1) % 25 == 0:
                print(f"  shuffle {i + 1}/200 (null max so far {max(nulls):.4f})", flush=True)
        shuffle = {"run": True, "null_max": float(max(nulls)), "null_mean": float(np.mean(nulls)),
                   "pass": bool(tune_champ > max(nulls))}
        print(f"label-shuffle gate: champion {tune_champ:.4f} vs null max {max(nulls):.4f} -> "
              f"{'PASS' if shuffle['pass'] else 'FAIL'}")
        if not shuffle["pass"]:
            sys.exit(1)

    # frozen refit on all 464; eval predictions for both candidates (champion confirmatory)
    preds = {}
    for name in {champ_name, "logreg_C1" if champ_name.startswith("hgb") else "hgb_lr0.1_d3_i300"}:
        pipe = fit_weighted(make(name), Xtr, ytr)
        preds[name] = list(pipe.predict(Xe))
    M = fit_b4_mapping([d for d, tr in zip(dicts, is_train) if tr], list(ytr))
    ev_dicts = [d for d, tr in zip(dicts, is_train) if not tr]
    out = pd.DataFrame({
        "event_id": [f"{r.machineID}@{r.datetime:%Y-%m-%dT%H}" for r in ev.itertuples()],
        "truth": list(ye),
        "b1_prior_random": b1_prior_random(len(ev), priors),
        "b2_no_evidence": [b2] * len(ev),
        "b3_oldest": [b3_oldest(d, counts) for d in ev_dicts],
        "b4_recent_error": [b4_recent_error(d, M, counts) for d in ev_dicts],
        "champion": preds[champ_name],
    })
    other = [k for k in preds if k != champ_name][0]
    out[f"alt_{other}"] = preds[other]
    out.to_csv(OUT / "predictions.csv", index=False)
    summary = {"champion": champ_name, "tune_scores": scores, "tune_b2": tune_b2,
               "granularity_gate": "PASS", "shuffle_gate": shuffle,
               "sklearn": sklearn.__version__,
               "eval_macro_f1": {c: macro_f1(out.truth, out[c]) for c in
                                 ["b1_prior_random", "b2_no_evidence", "b3_oldest", "b4_recent_error", "champion", f"alt_{other}"]},
               "eval_accuracy": {c: float((out.truth == out[c]).mean()) for c in
                                 ["b1_prior_random", "b2_no_evidence", "b3_oldest", "b4_recent_error", "champion", f"alt_{other}"]}}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary["eval_macro_f1"], indent=2))
    print(json.dumps(summary["eval_accuracy"], indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-shuffle-gate", action="store_true")
    a = ap.parse_args()
    main(a.skip_shuffle_gate)

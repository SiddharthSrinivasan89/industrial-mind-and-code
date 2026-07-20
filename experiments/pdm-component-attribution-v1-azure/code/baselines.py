"""Baselines B1–B4 (FROZEN-SPEC v5 §7). All fit on the train partition only."""
import numpy as np

from features import COMPS, ERRS

TIE_ORDER = {c: i for i, c in enumerate(COMPS)}  # comp1 < comp2 < comp3 < comp4


def train_stats(train_events):
    counts = train_events.comp.value_counts().reindex(COMPS).fillna(0).astype(int)
    priors = (counts / counts.sum()).to_dict()
    return counts.to_dict(), priors


def _tiebreak(cands, fail_counts):
    best = max(fail_counts[c] for c in cands)
    cands = [c for c in cands if fail_counts[c] == best]
    return min(cands, key=lambda c: TIE_ORDER[c])


def b1_prior_random(n, priors, seed=20260721):
    rng = np.random.default_rng(seed)
    return list(rng.choice(COMPS, size=n, p=[priors[c] for c in COMPS]))


def b2_no_evidence(fail_counts):
    return _tiebreak(COMPS, fail_counts)  # train majority (comp2 on this data)


def b3_oldest(d, fail_counts):
    censored = [c for c in COMPS if d[f"maint_censored_{c}"]]
    if len(censored) == 1:
        return censored[0]
    if censored:
        return _tiebreak(censored, fail_counts)
    ages = {c: d[f"maint_days_{c}"] for c in COMPS}
    best = max(ages.values())
    return _tiebreak([c for c, a in ages.items() if a == best], fail_counts)


def fit_b4_mapping(train_dicts, train_labels):
    """M[e, c] = count of train events with err_recent_code = e AND label = c."""
    M = {e: {c: 0 for c in COMPS} for e in ERRS + ["none"]}
    for d, y in zip(train_dicts, train_labels):
        M[d["err_recent_code"]][y] += 1
    return M


def b4_recent_error(d, M, fail_counts):
    e = d["err_recent_code"]
    if e == "none":
        return b2_no_evidence(fail_counts)
    col = M[e]
    best = max(col.values())
    if best == 0:
        return b2_no_evidence(fail_counts)
    return _tiebreak([c for c, v in col.items() if v == best], fail_counts)

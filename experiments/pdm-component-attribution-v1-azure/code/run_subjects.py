"""Subject runner — Arms A/B/C over the frozen eval set (FROZEN-SPEC v5).

Serial local execution (Ollama on kratos); Azure arm gated separately. Checkpointed JSONL
per (subject, arm); resume = skip completed event_ids. Hash-chained event ledger reused from
pipeline-v2 (pinned commit 9a44c726) per the adapter contract.

    python3 code/run_subjects.py --subject gpt-oss:120b --arm A [--events smoke1|probe|all|repeat]
"""
import argparse
import hashlib
import os
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PV2 = HERE.parent.parent / "tpm-cross-pillar-v1-grounded" / "pipeline-v2"
sys.path.insert(0, str(PV2))
import ledger as pv2_ledger  # pinned-core reuse (hash-chained event log)

import numpy as np
import pandas as pd

from features import COMPS, ERRS, SPLIT_BOUNDARY, audit_render, event_dictionary, load_tables, render, single_component_events
from parse_policy import parse_component

RAW = str(HERE.parent / "data" / "raw")
RESULTS = HERE.parent / "results"
CTX_PATH = HERE.parent / "gates" / "data-gate" / "context-block.md"

COMP_PERM = {"comp1": "unitD", "comp2": "unitB", "comp3": "unitC", "comp4": "unitA"}
ERR_PERM = {"error1": "codeB", "error2": "codeE", "error3": "codeC", "error4": "codeD", "error5": "codeA"}
PROBE_MACHINES = {4, 11, 22, 23, 30, 39, 40, 42, 47, 56, 58, 61, 63, 64, 68, 73, 74, 75, 80, 81, 88, 98}
REPEAT_EVENTS = {(1, "2015-09-02"), (17, "2015-11-27"), (21, "2015-12-04"), (24, "2015-11-13"),
                 (25, "2015-10-31"), (30, "2015-12-05"), (37, "2015-09-16"), (37, "2015-10-01"),
                 (37, "2015-11-15"), (43, "2015-11-17"), (45, "2015-10-19"), (49, "2015-11-11"),
                 (50, "2015-09-12"), (57, "2015-11-04"), (63, "2015-11-09"), (64, "2015-09-17"),
                 (71, "2015-09-23"), (74, "2015-10-20"), (78, "2015-09-03"), (78, "2015-11-02"),
                 (84, "2015-10-02"), (87, "2015-12-23"), (88, "2015-12-30"), (90, "2015-10-02"),
                 (90, "2015-11-01"), (94, "2015-10-20"), (95, "2015-09-17"), (95, "2015-10-17"),
                 (97, "2015-09-06"), (99, "2015-11-29")}

OLLAMA = "http://127.0.0.1:11434/api/chat"
DECODING = {  # FROZEN-SPEC §9 — transmitted values
    "gpt-oss:120b":        {"options": {"temperature": 1.0, "top_p": 1.0, "num_ctx": 8192, "num_predict": 8192}, "think": False},
    "qwen3.5:122b":        {"options": {"temperature": 0.6, "top_p": 0.95, "num_ctx": 32768, "num_predict": 16384}, "think": True},
    "nemotron-3-super:120b": {"options": {"temperature": 0.7, "top_p": 0.95, "num_ctx": 8192, "num_predict": 4096}, "think": False},
    "qwen3:4b":            {"options": {"temperature": 0.6, "top_p": 0.95, "num_ctx": 8192, "num_predict": 4096}, "think": True},
    "nemotron-3-nano:4b":  {"options": {"temperature": 0.7, "top_p": 0.95, "num_ctx": 8192, "num_predict": 4096}, "think": False},
    "gpt-5.4":             {"surface": "azure", "max_completion_tokens": 4096},
    "sonnet-4.6-agy":      {"surface": "agy", "agy_model": "Claude Sonnet 4.6 (Thinking)"},
}

SYSTEM = ("You are a maintenance analyst for a fleet of industrial machines. Each machine has "
          "four replaceable components and provides summaries of hourly telemetry (voltage, "
          "rotation speed, pressure, vibration), coded error events, and component replacement "
          "records.")

OUT_FMT = ('Respond with ONLY a raw JSON object (do not wrap it in markdown code blocks), in '
           'exactly this form:\n{{"component": "COMPONENT_NAME"}}\nReplace COMPONENT_NAME with '
           'exactly one of: {opts}.\n\nBefore answering, verify that the value of "component" '
           'exactly matches one candidate name and that the response is valid JSON.')
TASK_A = ("One of this machine's four components stopped functioning at reference time T. Using "
          "only the evidence above, decide which one. The candidate components are, in no "
          "particular order: {opts}.\n\n" + OUT_FMT)
TASK_B = ("One of this machine's four components stopped functioning at reference time T. Using "
          "the evidence above together with the reference statistics from the historical period, "
          "decide which one. The candidate components are, in no particular order: {opts}.\n\n"
          + OUT_FMT)


def eval_events():
    t, e, m, mach, f = load_tables(RAW)
    single, _ = single_component_events(f)
    ev = single[single.datetime >= SPLIT_BOUNDARY].reset_index(drop=True)
    assert len(ev) == 213
    tg, eg, mg = dict(list(t.groupby("machineID"))), dict(list(e.groupby("machineID"))), dict(list(m.groupby("machineID")))
    mach_idx = mach.set_index("machineID")
    return ev, tg, eg, mg, mach_idx, (t.iloc[0:0], e.iloc[0:0], m.iloc[0:0])


def answer_orders(n):
    """Per-event rank permutations (SPEC §2, amended twice at the prompt gate). Arm A/B uses
    ranks_ab on sorted comps. Arm C draws its OWN permutation (independent stream) and
    rejects any draw with ANY per-position correspondence to the mapped A/B order — an
    elementwise derangement w.r.t. A/B, deterministic given the seeds."""
    rng_ab = np.random.default_rng(20260728)
    rng_c = np.random.default_rng(20260731)
    comps_sorted, units_sorted = sorted(COMPS), sorted(COMP_PERM.values())
    out = []
    for _ in range(n):
        ab = list(rng_ab.permutation(4))
        mapped = [COMP_PERM[comps_sorted[i]] for i in ab]  # A/B order translated to units
        while True:
            c = list(rng_c.permutation(4))
            c_labels = [units_sorted[i] for i in c]
            if all(x != y for x, y in zip(c_labels, mapped)):
                break
        out.append((ab, c))
    return out


def apply_order(ranks, labels_sorted):
    return [labels_sorted[i] for i in ranks]


def build_user_prompt(arm, d, ranks_pair, ctx, ctx_c):
    ranks_ab, ranks_c = ranks_pair
    if arm == "C":
        rnd = render(d, COMP_PERM, ERR_PERM)
        labels = apply_order(ranks_c, sorted(COMP_PERM.values()))
        opts = ", ".join(labels)
        user = (f"<reference_statistics>\n{ctx_c}\n</reference_statistics>\n\n"
                f"<evidence>\n{rnd}\n</evidence>\n\n" + TASK_B.format(opts=opts))
    else:
        rnd = render(d)
        labels = apply_order(ranks_ab, sorted(COMPS))
        opts = ", ".join(labels)
        if arm == "A":
            user = f"<evidence>\n{rnd}\n</evidence>\n\n" + TASK_A.format(opts=opts)
        else:
            user = (f"<reference_statistics>\n{ctx}\n</reference_statistics>\n\n"
                    f"<evidence>\n{rnd}\n</evidence>\n\n" + TASK_B.format(opts=opts))
    assert user.startswith("<evidence>") or user.startswith("<reference_statistics>")
    return user, labels


def _load_env(path):
    env = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"')
    return env


_AZ = None


def call_azure(user, cfg, timeout=600):
    # Supply your own Azure OpenAI config. Either export the variables below, or point
    # PDM_AZURE_ENV at a local env file (KEY=VALUE lines):
    #   AZURE_ENDPOINT, AZURE_API_KEY, AZURE_API_VERSION, MODEL_GPT54
    global _AZ
    if _AZ is None:
        env_path = os.getenv("PDM_AZURE_ENV")
        _AZ = _load_env(env_path) if env_path else {
            k: os.environ[k] for k in ("AZURE_ENDPOINT", "AZURE_API_KEY", "AZURE_API_VERSION", "MODEL_GPT54")}
    url = (f"{_AZ['AZURE_ENDPOINT'].rstrip('/')}/openai/deployments/{_AZ['MODEL_GPT54']}"
           f"/chat/completions?api-version={_AZ['AZURE_API_VERSION']}")
    body = {"messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": user}],
            "max_completion_tokens": cfg["max_completion_tokens"]}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "api-key": _AZ["AZURE_API_KEY"]})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    ch = d.get("choices", [{}])[0]
    txt = (ch.get("message", {}).get("content") or "")
    usage = d.get("usage", {})
    meta = {"prompt_eval_count": usage.get("prompt_tokens"), "eval_count": usage.get("completion_tokens"),
            "done_reason": ch.get("finish_reason"), "model": d.get("model")}
    return txt, meta


def call_agy(user, cfg, timeout=600):
    import subprocess
    prompt = SYSTEM + "\n\n" + user
    r = subprocess.run(["agy", "--model", cfg["agy_model"], "--print", prompt, "--print-timeout", "8m"],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"agy rc={r.returncode}: {r.stderr[-200:]}")
    return r.stdout, {"prompt_eval_count": None, "eval_count": None, "done_reason": "cli", "model": cfg["agy_model"]}


def call_ollama(model, user, cfg, timeout=900):
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM},
                                         {"role": "user", "content": user}],
            "stream": False, "options": cfg["options"]}
    if cfg["think"]:
        body["think"] = True
    req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    msg = d.get("message", {})
    return (msg.get("content", "") or ""), d


def run(subject, arm, which):
    ev, tg, eg, mg, mach_idx, (et, ee, em) = eval_events()
    orders = answer_orders(len(ev))
    ctx = CTX_PATH.read_text()
    ctx_c = (CTX_PATH.parent / "context-block-armC.md").read_text()
    cfg = DECODING[subject]
    outdir = RESULTS / f"{subject.replace(':', '_')}_arm{arm}"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / ("records.jsonl" if which != "repeat" else "repeats.jsonl")
    led = outdir / "ledger.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            rec = json.loads(line)
            done.add((rec["event_id"], rec.get("rep", 0)))
    preflight_idx = set()
    if which == "preflight":
        lens = []
        for i, r in enumerate(ev.itertuples()):
            d = event_dictionary(r.machineID, r.datetime, tg.get(r.machineID, et),
                                 eg.get(r.machineID, ee), mg.get(r.machineID, em), mach_idx.loc[r.machineID])
            u, _ = build_user_prompt(arm, d, orders[i], ctx, ctx_c)
            lens.append((len(u), i))
        longest = {i for _, i in sorted(lens, reverse=True)[:3]}
        preflight_idx = longest | set(range(213))
        preflight_idx = set(list(longest) + [i for i in range(213) if i not in longest][:17])
        out = outdir / "preflight.jsonl"
        done = set()
    rows = []
    for i, r in enumerate(ev.itertuples()):
        eid = f"{r.machineID}@{r.datetime:%Y-%m-%dT%H}"
        key = (r.machineID, f"{r.datetime:%Y-%m-%d}")
        if which == "smoke1" and i > 0:
            break
        if which == "preflight" and i not in preflight_idx:
            continue
        if which == "probe" and r.machineID not in PROBE_MACHINES:
            continue
        if which == "repeat" and key not in REPEAT_EVENTS:
            continue
        reps = range(1, 4) if which == "repeat" else [0]
        for rep in reps:
            if (eid, rep) in done:
                continue
            rows.append((i, r, eid, rep))
    print(f"{subject} arm {arm} [{which}]: {len(rows)} calls to make ({len(done)} done)")
    for i, r, eid, rep in rows:
        d = event_dictionary(r.machineID, r.datetime, tg.get(r.machineID, et),
                             eg.get(r.machineID, ee), mg.get(r.machineID, em), mach_idx.loc[r.machineID])
        user, labels = build_user_prompt(arm, d, orders[i], ctx, ctx_c)
        probs = audit_render(user.split("<evidence>")[1].split("</evidence>")[0], r.datetime, r.machineID)
        assert not probs, f"render audit failure at {eid}: {probs}"
        attempts, txt, raw, err = 0, "", {}, None
        t0 = time.time()
        while attempts < 10:
            attempts += 1
            try:
                if cfg.get("surface") == "azure":
                    txt, raw = call_azure(user, cfg)
                elif cfg.get("surface") == "agy":
                    txt, raw = call_agy(user, cfg)
                else:
                    txt, raw = call_ollama(subject, user, cfg)
                break
            except Exception as ex:  # transport only
                err = f"{type(ex).__name__}: {ex}"
                time.sleep(min(60, 2 ** attempts))
        ms = int((time.time() - t0) * 1000)
        pred, status = parse_component(txt, labels)
        truth_label = COMP_PERM[r.comp] if arm == "C" else r.comp
        rec = {"event_id": eid, "rep": rep, "subject": subject, "arm": arm,
               "truth": truth_label, "pred": pred, "correct": bool(pred == truth_label),
               "parse_status": status, "attempts": attempts, "latency_ms": ms,
               "prompt_tokens": raw.get("prompt_eval_count"), "completion_tokens": raw.get("eval_count"),
               "finish_reason": raw.get("done_reason"), "empty": not txt.strip(),
               "transport_error": err if attempts >= 10 else None,
               "options": cfg.get("options"), "think": cfg.get("think"), "labels": labels,
               "surface": cfg.get("surface", "ollama"),
               "raw_chars": len(txt)}
        with open(out, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        pv2_ledger.append(led, {"kind": "subject_call",
                                **{k: rec[k] for k in ("event_id", "rep", "pred", "correct", "parse_status")}})
        print(f"  {eid} rep{rep}: pred={pred} truth={truth_label} {'OK' if rec['correct'] else 'x'} "
              f"({status}, {ms}ms, {rec['completion_tokens']} tok)", flush=True)
    if which == "preflight":
        recs = [json.loads(l) for l in out.read_text().splitlines()]
        ok = sum(r["parse_status"] == "ok" for r in recs)
        trunc = sum(r["finish_reason"] == "length" for r in recs)
        empty = sum(r["empty"] for r in recs)
        verdict = "PASS" if (ok >= len(recs) - 2 and trunc == 0 and empty == 0) else "FAIL"
        report = {"subject": subject, "arm": arm, "n": len(recs), "parse_ok": ok,
                  "truncated": trunc, "empty": empty, "verdict": verdict}
        (outdir / "preflight-report.json").write_text(json.dumps(report, indent=2))
        print("PREFLIGHT", json.dumps(report))
        if verdict == "FAIL":
            sys.exit(1)
    print("done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--arm", required=True, choices=["A", "B", "C"])
    ap.add_argument("--events", default="all", choices=["smoke1", "preflight", "probe", "all", "repeat"])
    a = ap.parse_args()
    run(a.subject, a.arm, a.events)

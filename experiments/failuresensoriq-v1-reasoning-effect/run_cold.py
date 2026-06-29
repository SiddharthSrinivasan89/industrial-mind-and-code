#!/usr/bin/env python3
"""Phase 1, cold rung: ask a model each question with no help, score against the key.

Usage:
  python3 run_cold.py --smoke            # 5 questions, print raw replies
  python3 run_cold.py --n 200            # balanced sample, score it

Saves the frozen sample to sample_manifest.json (built once, reused after).
"""
import argparse
import json
import os
import random
import re
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ALL = os.path.join(HERE, "data/raw/failuresensoriq_standard/all.jsonl")
MANIFEST = os.path.join(HERE, "sample_manifest.json")
OLLAMA = "http://localhost:11434/api/chat"


def load():
    return [json.loads(l) for l in open(ALL) if l.strip()]


def build_prompt(r):
    lines = [r["question"], ""]
    for lab, opt in zip(r["option_ids"], r["options"]):
        lines.append(f"{lab}) {opt}")
    lines += ["", "Answer with the letter of the single best option only."]
    return "\n".join(lines)


def correct_label(r):
    idx = r["correct"].index(True)
    return r["option_ids"][idx]


def ask(model, prompt, retries=5):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "stream": False,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 7168}}
    delay = 2
    for attempt in range(retries):
        try:
            t = time.time()
            resp = requests.post(OLLAMA, json=payload, timeout=180)
            resp.raise_for_status()
            return resp.json()["message"]["content"], round((time.time() - t) * 1000)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(min(delay, 60))
            delay *= 2


def parse(reply, r):
    """Pull the chosen option label out of a messy reply. None if unreadable.

    Non-reasoning models lead with the letter ("B" then explain). Reasoning models
    (phi4-mini-reasoning) emit a think block first and conclude at the end, so we
    strip the think block and, in the fallback, take the LAST answer statement.
    """
    labels = [l.rstrip(")").upper() for l in r["option_ids"]]
    # strip a reasoning/think block if present (closed, or leading up to </think>)
    clean = re.sub(r"<think>.*?</think>", "", reply, flags=re.S | re.I)
    clean = re.sub(r"^.*?</think>", "", clean, flags=re.S | re.I)
    s = clean.strip().lstrip("*# ").strip()
    # the letter the reply leads with: "B", "B)", "(B)", "B\n\nExplanation"
    m = re.match(r"[*\s(]*([A-Z])(?![A-Za-z])", s)
    if m and m.group(1) in labels:
        return r["option_ids"][labels.index(m.group(1))]
    # a letter committed with a closing paren, e.g. "D)" ("The answer would be D) Current").
    # prefer one that follows a commit word; else the first such letter in the reply.
    mc = re.search(r"answer|correct|best|choose|select|pick|option", clean, re.I)
    if mc:
        pm = re.search(r"\b([A-Z])\)", clean[mc.start():])
        if pm and pm.group(1) in labels:
            return r["option_ids"][labels.index(pm.group(1))]
    pm = re.search(r"\b([A-Z])\)", clean)
    if pm and pm.group(1) in labels:
        return r["option_ids"][labels.index(pm.group(1))]
    # explicit "answer/option/correct is X" — take the LAST mention (reasoning concludes at end)
    matches = re.findall(r"(?:answer|option|correct)[^A-Za-z]{0,15}([A-Z])\b", clean, re.I)
    for g in reversed(matches):
        if g.upper() in labels:
            return r["option_ids"][labels.index(g.upper())]
    # last non-empty line is a lone letter
    lines = [ln.strip().strip("*.):(") for ln in s.splitlines() if ln.strip()]
    if lines and len(lines[-1]) == 1 and lines[-1].upper() in labels:
        return r["option_ids"][labels.index(lines[-1].upper())]
    # fall back to a unique option-text match
    low = clean.lower()
    hits = [lab for lab, opt in zip(r["option_ids"], r["options"]) if opt.lower() in low]
    return hits[0] if len(hits) == 1 else None


def balanced_sample(rows, n, seed=0):
    by_asset = {}
    for r in rows:
        by_asset.setdefault(r["asset_name"], []).append(r["id"])
    per = max(1, n // len(by_asset))
    rng = random.Random(seed)
    ids = []
    for a, lst in sorted(by_asset.items()):
        ids += rng.sample(lst, min(per, len(lst)))
    return sorted(ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma3:4b")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--full", action="store_true", help="run all single-answer questions")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    rows = load()
    by_id = {r["id"]: r for r in rows}

    if args.smoke:
        ids = balanced_sample(rows, 5, seed=1)
        print(f"SMOKE — {args.model}, {len(ids)} questions\n")
        for _id in ids:
            r = by_id[_id]
            reply, ms = ask(args.model, build_prompt(r))
            got = parse(reply, r)
            key = correct_label(r)
            print(f"id {_id} [{r['asset_name']}]  key={key}  parsed={got}  {ms}ms")
            print(f"  raw reply: {reply!r}\n")
        return

    if args.full:
        ids = sorted(by_id)
        out = os.path.join(HERE, f"results_cold_full_{args.model.replace(':','-')}.jsonl")
    else:
        if os.path.exists(MANIFEST):
            ids = json.load(open(MANIFEST))["ids"]
        else:
            ids = balanced_sample(rows, args.n)
            json.dump({"n": len(ids), "seed": 0, "ids": ids}, open(MANIFEST, "w"))
        out = os.path.join(HERE, f"results_cold_{args.model.replace(':','-')}.jsonl")

    # resume: skip ids already written to the output file
    done = {}
    if os.path.exists(out):
        for line in open(out):
            if line.strip():
                rec = json.loads(line)
                done[rec["id"]] = rec
    todo = [i for i in ids if i not in done]
    print(f"COLD{' (full)' if args.full else ''} — {args.model}: {len(ids)} questions, "
          f"{len(done)} already done, {len(todo)} to run", flush=True)

    f = open(out, "a")
    for i, _id in enumerate(todo):
        r = by_id[_id]
        reply, ms = ask(args.model, build_prompt(r))
        got = parse(reply, r)
        key = correct_label(r)
        rec = {"id": _id, "asset": r["asset_name"], "qtype": r["question_type"],
               "key": key, "parsed": got, "correct": got == key, "ms": ms, "raw": reply}
        f.write(json.dumps(rec) + "\n")
        f.flush()
        done[_id] = rec
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(todo)} done", flush=True)
    f.close()

    results = [done[i] for i in ids if i in done]
    n = len(results)
    acc = sum(x["correct"] for x in results) / n
    fails = sum(1 for x in results if x["parsed"] is None)
    print(f"\naccuracy: {acc:.1%}  ({sum(x['correct'] for x in results)}/{n})")
    print(f"unreadable replies: {fails}")
    print("by machine:")
    for a in sorted({x["asset"] for x in results}):
        sub = [x for x in results if x["asset"] == a]
        print(f"  {a:<42} {sum(x['correct'] for x in sub)/len(sub):.1%}  (n={len(sub)})")
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Re-score a saved cold-run file from its saved raw replies, using the current parser.

No model calls — re-parses the stored `raw` text only, then rewrites parsed/correct.
Keeps a .bak. Safe to run on a finished file; do NOT run on a file still being written.

Usage: python3 rescore.py results_cold_full_gemma3-4b.jsonl [more files...]
"""
import json
import os
import shutil
import sys

import run_cold


def rescore(path):
    rows = run_cold.load()
    by_id = {r["id"]: r for r in rows}
    recs = [json.loads(l) for l in open(path) if l.strip()]
    n = len(recs)
    before_c = sum(x["correct"] for x in recs)
    before_f = sum(1 for x in recs if x["parsed"] is None)
    flipped = 0
    for x in recs:
        got = run_cold.parse(x["raw"], by_id[x["id"]])
        if got != x["parsed"]:
            flipped += 1
        x["parsed"] = got
        x["correct"] = got == x["key"]
    after_c = sum(x["correct"] for x in recs)
    after_f = sum(1 for x in recs if x["parsed"] is None)
    shutil.copy(path, path + ".bak")
    with open(path, "w") as f:
        for x in recs:
            f.write(json.dumps(x) + "\n")
    print(f"{os.path.basename(path)}: n={n}, records changed={flipped}")
    print(f"  before: {before_c/n:.1%} ({before_c}/{n}), unreadable={before_f}")
    print(f"  after:  {after_c/n:.1%} ({after_c}/{n}), unreadable={after_f}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        rescore(p)

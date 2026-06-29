#!/usr/bin/env python3
"""Data-gate inspection: show how FailureSensorIQ encodes questions, options, and
answers, plus key field distributions. Read-only. Run: python3 inspect_data.py"""
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")


def load(rel):
    with open(os.path.join(RAW, rel)) as f:
        return [json.loads(l) for l in f if l.strip()]


def show_record(rec, keys=None):
    for k, v in rec.items():
        if keys and k not in keys:
            continue
        s = json.dumps(v, ensure_ascii=False)
        if len(s) > 600:
            s = s[:600] + " …"
        print(f"    {k}: {s}")


def dist(rows, field):
    c = Counter(r.get(field) for r in rows)
    return dict(sorted(c.items(), key=lambda x: -x[1]))


print("=" * 78)
print("SINGLE-ANSWER  failuresensoriq_standard/all.jsonl")
print("=" * 78)
single = load("failuresensoriq_standard/all.jsonl")
print(f"rows: {len(single)}")
print(f"asset_name unique ({len(dist(single,'asset_name'))}): {list(dist(single,'asset_name'))}")
print(f"question_type: {dist(single,'question_type')}")
print(f"text_type: {dist(single,'text_type')}")
print(f"relevancy: {dist(single,'relevancy')}")
print(f"option count per Q (min/max): "
      f"{min(len(r['options']) for r in single)}/{max(len(r['options']) for r in single)}")
print("--- sample record [0] ---")
show_record(single[0])
print("--- sample record [1] (different question_type if any) ---")
other = next((r for r in single if r.get("question_type") != single[0].get("question_type")), single[1])
show_record(other)

print()
print("=" * 78)
print("MULTI-ANSWER  failuresensoriq_standard/all_multi_answers.jsonl")
print("=" * 78)
multi = load("failuresensoriq_standard/all_multi_answers.jsonl")
print(f"rows: {len(multi)}")
print(f"subject unique ({len(dist(multi,'subject'))}): {list(dist(multi,'subject'))[:12]}")
ncorrect = Counter(len(r["correct"]) if isinstance(r["correct"], list) else 1 for r in multi)
print(f"#correct-per-question distribution: {dict(sorted(ncorrect.items()))}")
print(f"option count per Q (min/max): "
      f"{min(len(r['options']) for r in multi)}/{max(len(r['options']) for r in multi)}")
print("--- sample record [0] ---")
show_record(multi[0])

print()
print("=" * 78)
print("OPTIONS-PERT  failuresensoriq_standard/all_10_options.jsonl")
print("=" * 78)
opt10 = load("failuresensoriq_standard/all_10_options.jsonl")
print(f"rows: {len(opt10)}  | option count per Q (min/max): "
      f"{min(len(r['options']) for r in opt10)}/{max(len(r['options']) for r in opt10)}")
show_record(opt10[0], keys=["id", "question", "options", "option_ids", "correct"])

print()
print("=" * 78)
print("SIMPLE-PERT  failuresensoriq_perturbed/perturbed_simple.jsonl")
print("=" * 78)
sp = load("failuresensoriq_perturbed/perturbed_simple.jsonl")
print(f"rows: {len(sp)}")
show_record(sp[0], keys=["id", "question", "options", "option_ids", "correct"])

print()
print("=" * 78)
print("ID alignment across variants (do perturbed sets share base ids?)")
print("=" * 78)
base_ids = {r["id"] for r in single}
for rel in ["failuresensoriq_perturbed/perturbed_simple.jsonl",
            "failuresensoriq_perturbed/perturbed_complex.jsonl",
            "failuresensoriq_standard/all_10_options.jsonl"]:
    ids = {r["id"] for r in load(rel)}
    print(f"  {rel.split('/')[-1]:42s} ids={len(ids)}  shared_with_base={len(ids & base_ids)}")

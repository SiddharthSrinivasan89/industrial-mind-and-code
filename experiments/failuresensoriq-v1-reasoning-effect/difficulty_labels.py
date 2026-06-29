#!/usr/bin/env python3
"""Freeze a per-question difficulty + polarity label for the single-answer set.

Difficulty rule (signed off 2026-06-23): difficulty = fault-breadth of the question's
focal sensor on its asset = how many distinct faults that sensor is marked relevant to.
  clear     : breadth <= 2
  confusing : breadth >= 5
  moderate  : in between
Focal sensor: for sensor-subject questions (failure_modes_for_sensor) it is the sensor
named in the question; for fault-subject questions (sensors_for_failure_mode) it is the
correct-answer sensor. Polarity is read straight from question_type.

Output: difficulty_labels.jsonl, one record per question id. Frozen artifact for RQ4/RQ5.
"""
import json
from collections import Counter, defaultdict

import run_cold

rows = run_cold.load()

sensor_vocab = set()
fault_vocab = set()
for r in rows:
    if "sensors_for_failure_mode" in r["relevancy"]:
        sensor_vocab.update(o.lower() for o in r["options"])
    else:
        fault_vocab.update(o.lower() for o in r["options"])


def longest_in(text, vocab):
    t = text.lower()
    c = [v for v in vocab if v in t]
    return max(c, key=len) if c else None


# relevant (asset, sensor) -> set of faults, from positive questions both directions
rel = defaultdict(set)
for r in rows:
    if not r["relevancy"].startswith("relevant"):
        continue
    asset = r["asset_name"]
    correct = r["options"][r["correct"].index(True)].lower()
    if "sensors_for_failure_mode" in r["relevancy"]:
        fault, sensor = longest_in(r["question"], fault_vocab), correct
    else:
        fault, sensor = correct, longest_in(r["question"], sensor_vocab)
    if fault and sensor:
        rel[(asset, sensor)].add(fault)


def label(breadth):
    if breadth is None:
        return "unknown"
    if breadth <= 2:
        return "clear"
    if breadth >= 5:
        return "confusing"
    return "moderate"


out = []
for r in rows:
    asset = r["asset_name"]
    correct = r["options"][r["correct"].index(True)].lower()
    if "sensors_for_failure_mode" in r["relevancy"]:
        focal = correct
    else:
        focal = longest_in(r["question"], sensor_vocab)
    breadth = len(rel[(asset, focal)]) if focal in (s for a, s in rel if a == asset) else (
        len(rel.get((asset, focal), set())) if focal else None)
    polarity = "positive" if r["question_type"] == "mcp1_positive" else "negative"
    out.append({"id": r["id"], "asset": asset, "polarity": polarity,
                "focal_sensor": focal, "fault_breadth": breadth,
                "difficulty": label(breadth)})

with open("difficulty_labels.jsonl", "w") as f:
    for rec in sorted(out, key=lambda x: x["id"]):
        f.write(json.dumps(rec) + "\n")

print(f"frozen {len(out)} labels -> difficulty_labels.jsonl")
print("difficulty:", dict(Counter(x["difficulty"] for x in out)))
print("polarity:", dict(Counter(x["polarity"] for x in out)))
print("missing focal sensor:", sum(1 for x in out if x["focal_sensor"] is None))

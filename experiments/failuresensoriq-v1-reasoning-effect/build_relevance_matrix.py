#!/usr/bin/env python3
"""Reconstruct the failure-mode <-> sensor relevance map per asset from the
single-answer 'relevant' (positive) questions, then measure the easy vs hard
diagnostic direction. No model calls. Run: python3 build_relevance_matrix.py

- Easy direction  (failure -> sensors): how many gauges show a given fault.
- Hard direction  (sensor  -> failures): how many faults a given gauge could mean.
A sensor relevant to many failure modes is an ambiguous ('confusing') symptom.

Edges are the 'most relevant' links the benchmark encodes in its positive
single-answer items (923 questions). Same fault appears across many questions with
different option sets, so multiple relevant sensors per fault accumulate. This is
the strong-link map, not necessarily the complete FMEA matrix.
"""
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
S = [json.loads(l) for l in open(os.path.join(HERE, "data/raw/failuresensoriq_standard/all.jsonl")) if l.strip()]


def find_entity(text, vocab):
    cands = [v for v in vocab if v and v in text]
    return max(cands, key=len) if cands else None


# Per-asset vocabularies from option lists.
sensor_vocab = defaultdict(set)   # options of *_sensors_for_failure_mode questions
fm_vocab = defaultdict(set)       # options of *_failure_modes_for_sensor questions
for r in S:
    a = r["asset_name"]
    if "sensors_for_failure_mode" in r["relevancy"]:
        sensor_vocab[a].update(r["options"])
    else:
        fm_vocab[a].update(r["options"])

# Build relevant (fault -> sensors) and (sensor -> faults) per asset from positives.
fault_to_sensors = defaultdict(lambda: defaultdict(set))
sensor_to_faults = defaultdict(lambda: defaultdict(set))
parsed = miss = 0
for r in S:
    if r["question_type"] != "mcp1_positive":
        continue
    a = r["asset_name"]
    text = r["question"].lower().replace(a, " ")
    correct = next(o for o, c in zip(r["options"], r["correct"]) if c)
    if r["relevancy"] == "relevant_sensors_for_failure_mode":
        fault = find_entity(text, fm_vocab[a]); sensor = correct
    else:  # relevant_failure_modes_for_sensor
        sensor = find_entity(text, sensor_vocab[a]); fault = correct
    if not fault or not sensor:
        miss += 1
        continue
    parsed += 1
    fault_to_sensors[a][fault].add(sensor)
    sensor_to_faults[a][sensor].add(fault)

print(f"positive questions parsed: {parsed}  (extraction misses: {miss})\n")

# Per-asset easy/hard summary.
hdr = f"{'asset':<42}{'#faults':>8}{'#sensors':>9}{'sens/fault':>11}{'faults/sens':>12}{'max f/s':>8}"
print(hdr); print("-" * len(hdr))
tot_sf = tot_fs = 0.0
n_assets = 0
overloaded = defaultdict(int)   # sensor -> times it is an asset's most-overloaded symptom
for a in sorted(fault_to_sensors, key=lambda x: -len(sensor_to_faults[x])):
    faults = fault_to_sensors[a]; sensors = sensor_to_faults[a]
    sens_per_fault = sum(len(v) for v in faults.values()) / len(faults)
    faults_per_sens = sum(len(v) for v in sensors.values()) / len(sensors)
    worst = max(sensors.items(), key=lambda kv: len(kv[1]))
    overloaded[worst[0]] += 1
    tot_sf += sens_per_fault; tot_fs += faults_per_sens; n_assets += 1
    print(f"{a:<42}{len(faults):>8}{len(sensors):>9}{sens_per_fault:>11.2f}{faults_per_sens:>12.2f}{len(worst[1]):>8}")

print("-" * len(hdr))
print(f"{'MEAN across assets':<42}{'':>8}{'':>9}{tot_sf/n_assets:>11.2f}{tot_fs/n_assets:>12.2f}\n")

# Most confusing symptoms: sensors flagging the most faults, pooled view.
print("Most 'confusing' symptoms (one example asset each) — gauge : #faults it could mean")
flat = []
for a in sensor_to_faults:
    for s, fs in sensor_to_faults[a].items():
        flat.append((len(fs), s, a, sorted(fs)))
for n, s, a, fs in sorted(flat, reverse=True)[:10]:
    ex = ", ".join(fs[:4]) + (" …" if len(fs) > 4 else "")
    print(f"  {s:<22} could mean {n:>2} faults  [{a}]  e.g. {ex}")

# Single-point faults: detectable by only one sensor in the strong-link map.
singles = sum(1 for a in fault_to_sensors for f, ss in fault_to_sensors[a].items() if len(ss) == 1)
total_faults = sum(len(v) for v in fault_to_sensors.values())
print(f"\nSingle-sensor faults (only one gauge flags them here): {singles}/{total_faults}")

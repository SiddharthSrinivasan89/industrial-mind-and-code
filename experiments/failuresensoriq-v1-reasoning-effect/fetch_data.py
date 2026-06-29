#!/usr/bin/env python3
"""Acquire the FailureSensorIQ dataset into data/raw/, pin the revision, and record
per-file SHA-256 + provenance. Read-only with respect to HuggingFace; idempotent.

Run: python3 fetch_data.py
"""
import hashlib
import json
import os
from datetime import datetime, timezone

import requests

REPO_ID = "ibm-research/FailureSensorIQ"
# Pinned to the revision listed by the HF API at acquisition time (provenance).
REVISION = "5f9a736201916597345285bb6e712e3b8f4f0cfe"

# Direct HTTP download per file. snapshot_download() hung on its transfer backend
# (stalled socket, zero bytes after 5 min), so we pull each file from the pinned
# resolve URL with explicit connect/read timeouts and retries instead.
FILES = [
    "README.md",
    "failuresensoriq_standard/all.jsonl",
    "failuresensoriq_standard/all_10_options.jsonl",
    "failuresensoriq_standard/all_multi_answers.jsonl",
    "failuresensoriq_perturbed/perturbed_simple.jsonl",
    "failuresensoriq_perturbed/perturbed_complex.jsonl",
    "failuresensoriq_perturbed/all_10_options_all_perturbed_simple.jsonl",
    "failuresensoriq_perturbed/all_10_options_perturbed_complex.jsonl",
]
BASE = f"https://huggingface.co/datasets/{REPO_ID}/resolve/{REVISION}"

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "data", "raw")


def download(rel, dest):
    url = f"{BASE}/{rel}"
    last = None
    for attempt in range(5):
        try:
            with requests.get(url, stream=True, timeout=(10, 60)) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            return
        except Exception as e:  # noqa: BLE001 - retry transport errors
            last = e
    raise RuntimeError(f"failed to download {rel}: {last}")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    for rel in FILES:
        dest = os.path.join(RAW_DIR, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            print(f"  skip (present) {rel}")
            continue
        download(rel, dest)
        print(f"  fetched {rel}")

    # Per-file checksums + jsonl row counts and first-record keys.
    files = []
    for rel in FILES:
        p = os.path.join(RAW_DIR, rel)
        entry = {"file": rel, "bytes": os.path.getsize(p), "sha256": sha256(p)}
        if rel.endswith(".jsonl"):
            with open(p) as f:
                first = f.readline()
                rows = 1 + sum(1 for _ in f) if first.strip() else 0
            entry["rows"] = rows
            entry["keys"] = sorted(json.loads(first).keys()) if first.strip() else []
        files.append(entry)

    prov = {
        "repo_id": REPO_ID,
        "repo_type": "dataset",
        "revision": REVISION,
        "source_url": f"https://huggingface.co/datasets/{REPO_ID}",
        "code_repo": "https://github.com/IBM/FailureSensorIQ",
        "paper": "FailureSensorIQ (IBM Research, NeurIPS 2025), arXiv:2506.03278",
        "license_hf_cardData": "apache-2.0",
        "license_github_readme": "CC-BY-4.0",
        "license_note": "HF card and GitHub README disagree; resolve before redistribution.",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    out = os.path.join(HERE, "data", "PROVENANCE.json")
    with open(out, "w") as f:
        json.dump(prov, f, indent=2)
    print(json.dumps(prov, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()

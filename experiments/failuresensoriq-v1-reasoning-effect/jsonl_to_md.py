#!/usr/bin/env python3
"""Export a FailureSensorIQ JSONL file to a reviewable Markdown table.

Derived review artifact only — does not modify or replace the source data.

Usage: python jsonl_to_md.py <input.jsonl> [output.md]
"""
import json
import os
import sys
from collections import Counter


def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def main():
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(inp)[0] + "_review.md"
    rows = [json.loads(line) for line in open(inp, encoding="utf-8") if line.strip()]

    by_asset = Counter(r.get("asset_name", "—") for r in rows)
    by_type = Counter(r.get("question_type", "—") for r in rows)
    by_rel = Counter(r.get("relevancy", "—") for r in rows)

    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# FailureSensorIQ — `{os.path.basename(inp)}` (review export)\n\n")
        f.write(f"Auto-generated from `{inp}` — derived review artifact, not source data. "
                f"{len(rows)} records. Regenerate with `jsonl_to_md.py`.\n\n")
        f.write("> Source: IBM Research FailureSensorIQ (NeurIPS 2025, arXiv:2506.03278). "
                "See `data/DATA.md` and `data/PROVENANCE.json`.\n\n")
        f.write("## Summary\n\n")
        f.write("**By asset:** " + " · ".join(f"{k} ({v})" for k, v in by_asset.most_common()) + "\n\n")
        f.write("**By question type:** " + " · ".join(f"{k} ({v})" for k, v in by_type.most_common()) + "\n\n")
        f.write("**By relevancy:** " + " · ".join(f"{k} ({v})" for k, v in by_rel.most_common()) + "\n\n")
        f.write("## Records\n\n")
        f.write("| # | Asset | Type | Question | Options (✓ = correct) |\n")
        f.write("|---|---|---|---|---|\n")
        for r in rows:
            opts = r.get("options", [])
            ids = r.get("option_ids") or [chr(65 + i) for i in range(len(opts))]
            corr = r.get("correct") or [False] * len(opts)
            cells = [
                (f"**{esc(oid)}) {esc(opt)} ✓**" if c else f"{esc(oid)}) {esc(opt)}")
                for oid, opt, c in zip(ids, opts, corr)
            ]
            f.write(f"| {r.get('id', '')} | {esc(r.get('asset_name', '—'))} "
                    f"| {esc(r.get('question_type', '—'))} | {esc(r.get('question', ''))} "
                    f"| {' · '.join(cells)} |\n")
    print(f"wrote {out}  ({len(rows)} records)")


if __name__ == "__main__":
    main()

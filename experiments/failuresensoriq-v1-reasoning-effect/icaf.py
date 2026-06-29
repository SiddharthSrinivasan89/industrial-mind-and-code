#!/usr/bin/env python3
"""ICAF — Industrial Commissioning Agentic Framework (v0, deterministic loop).

Commissions a local model into an industrial workflow, on-prem, no cloud. The loop:
  classify task (catalog) -> set temperature regime -> IHF probe at that temperature
  -> resolve reasoning/temperature conflict -> emit a commissioning record.

With several candidate models it closes the loop: iterate and converge on the model that
commissions cleanly for the task (the model-selection payoff in ICAF.md §8). The driver is a
deterministic script (a state machine); the only model in the picture is the local one under
commission.

    python3 icaf.py --workflow fault-diagnosis --model gemma3:4b
    python3 icaf.py --workflow fault-diagnosis --candidates gemma3:4b,phi4-mini,phi4-mini-reasoning
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import ihf
from icaf_catalog import CATALOG, DETERMINISTIC_TEMP

HERE = Path(__file__).resolve().parent
NON_REASONING_HINT = "gemma3:4b, phi4-mini"


def commission_one(workflow, model, num_predict=None, n=20, dry_run=False):
    """Run the commissioning loop for one (workflow, model). Returns a record dict."""
    wf = CATALOG[workflow]
    task_class = wf["class"]
    prov = ihf.resolve_defaults(model)
    if not prov["found"]:
        return {"workflow": workflow, "model": model, "verdict": "NOT COMMISSIONED",
                "error": "no provider-default card", "conflicts": [], "ihf_gate": False}
    reasoning = prov.get("reasoning", False)

    conflicts, relaxations, recommendation = [], [], None
    if task_class == "deterministic":
        if reasoning:
            mandated_temp = prov["temperature"]
            conflicts.append("deterministic task wants temperature 0-0.3, but a reasoning model "
                             "loops / never terminates at low temperature")
            relaxations.append(f"temperature relaxed to provider default {mandated_temp} "
                               "(reasoning model cannot run the deterministic-low regime)")
            recommendation = (f"prefer a non-reasoning local model ({NON_REASONING_HINT}) "
                              f"at temperature {DETERMINISTIC_TEMP}")
        else:
            mandated_temp = DETERMINISTIC_TEMP
    else:
        mandated_temp = prov["temperature"]

    budget = num_predict or (16384 if reasoning else 2048)

    ihf_result, ihf_pass = None, None
    if not dry_run:
        cmd = ["python3", str(HERE / "ihf_preflight.py"), "--model", model,
               "--num-predict", str(budget), "--temperature", str(mandated_temp), "--n", str(n)]
        proc = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
        ihf_pass = proc.returncode == 0
        reports = sorted((HERE / "results" / "_preflight").glob(
            f"{model.replace(':', '-')}_*/ihf_preflight.json"))
        if reports:
            ihf_result = json.loads(reports[-1].read_text())

    if dry_run:
        verdict = "DRY-RUN"
    elif ihf_pass and not conflicts:
        verdict = "COMMISSIONED"
    elif ihf_pass and conflicts:
        verdict = "COMMISSIONED WITH CAVEATS"
    else:
        verdict = "NOT COMMISSIONED"

    return {"workflow": workflow, "task_class": task_class, "task_desc": wf["desc"],
            "model": model, "model_version": ihf.model_version(model), "is_reasoning": reasoning,
            "mandated_temperature": mandated_temp, "num_predict": budget, "conflicts": conflicts,
            "relaxations": relaxations, "recommendation": recommendation,
            "ihf_gate": ihf_pass, "ihf_checks": (ihf_result.get("checks") if ihf_result else None),
            "verdict": verdict}


def is_clean(rec, dry_run):
    """Selectable: task-appropriate (no conflict) and the probe passed (or dry-run)."""
    return not rec["conflicts"] and (dry_run or rec["ihf_gate"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--model", help="commission a single model")
    g.add_argument("--candidates", help="comma-separated models; converge on the one that commissions")
    ap.add_argument("--num-predict", type=int, default=None)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true", help="run the loop logic without the IHF probe")
    args = ap.parse_args()

    if args.workflow not in CATALOG:
        sys.exit(f"unknown workflow {args.workflow!r}; choices: {', '.join(sorted(CATALOG))}")

    models = [args.model] if args.model else [m.strip() for m in args.candidates.split(",") if m.strip()]
    trail = [commission_one(args.workflow, m, args.num_predict, args.n, args.dry_run) for m in models]

    # converge: first clean model wins; else first commissioned-with-caveats; else none
    selected = next((r for r in trail if is_clean(r, args.dry_run)), None)
    if not selected and not args.dry_run:
        selected = next((r for r in trail if r["ihf_gate"]), None)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    record = {"workflow": args.workflow, "task_class": CATALOG[args.workflow]["class"],
              "candidates": models, "dry_run": args.dry_run,
              "selected_model": (selected["model"] if selected else None),
              "trail": trail, "timestamp_utc": stamp}
    outdir = HERE / "results" / "_commission"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{args.workflow}_{stamp}.json").write_text(json.dumps(record, indent=2))

    wf = CATALOG[args.workflow]
    print("=" * 70)
    print(f"ICAF COMMISSION — {args.workflow}  [{wf['class']}: {wf['desc']}]")
    print("=" * 70)
    for r in trail:
        if "error" in r:
            print(f"  {r['model']:24} {r['verdict']:24} ({r['error']})")
            continue
        tag = "<- selected" if selected and r["model"] == selected["model"] else ""
        gate = "" if args.dry_run else f" IHF={'PASS' if r['ihf_gate'] else 'FAIL'}"
        print(f"  {r['model']:24} temp={r['mandated_temperature']:<4} {r['verdict']:24}{gate}  {tag}")
        if r["conflicts"]:
            print(f"      conflict: {r['conflicts'][0]}")
    print("-" * 70)
    if selected:
        print(f"  SELECTED: {selected['model']} at temperature {selected['mandated_temperature']}")
    else:
        print(f"  NO MODEL COMMISSIONED for this workflow among: {', '.join(models)}")
    print("=" * 70)
    sys.exit(0 if selected else 1)


if __name__ == "__main__":
    main()

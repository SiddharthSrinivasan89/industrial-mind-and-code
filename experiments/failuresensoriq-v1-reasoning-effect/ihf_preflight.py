#!/usr/bin/env python3
"""IHF v1 preflight for the FailureSensorIQ MCQ task — experiment-as-deployment gate.

Probes one model at its provider settings (default 20 calls), scores the five frozen
dimensions (SOR/AFC/TCA/TBC/FP), writes ihf_preflight.{md,json}, and exits non-zero if
the gate fails. Protocol: frameworks/model-integration-hygiene/IHF-PREFLIGHT.md

Structured output here is a single committed option letter (not JSON): strict = parsed
on the first attempt, fallback = unreadable.

    python3 ihf_preflight.py --model gemma3:4b --num-predict 2048
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import ihf
import run_cold

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--num-predict", type=int, required=True, help="output budget the full run will use")
    ap.add_argument("--temperature", type=float, default=None,
                    help="task-mandated temperature (ICAF); default = provider card temperature")
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--min-sor", type=float, default=0.95)
    ap.add_argument("--max-fallback", type=float, default=0.05)
    args = ap.parse_args()

    prov = ihf.resolve_defaults(args.model)
    version = ihf.model_version(args.model)
    rows = run_cold.load()
    by_id = {r["id"]: r for r in rows}
    ids = json.load(open(HERE / "sample_manifest.json"))["ids"][:args.n]

    mandated_temp = args.temperature if args.temperature is not None else prov.get("temperature")
    settings = {"temperature": mandated_temp, "top_p": prov.get("top_p"),
                "top_k": prov.get("top_k"), "seed": args.seed,
                "num_ctx": args.num_ctx, "num_predict": args.num_predict}

    recs = []
    for _id in ids:
        r = by_id[_id]
        content, tele = ihf.call(args.model, run_cold.build_prompt(r), settings)
        parsed = ihf.parse_answer(content, r["option_ids"])
        recs.append({"id": _id, "parse_status": "strict" if parsed is not None else "fallback",
                     "truncated": tele["finish_reason"] == "length", **tele})

    n = len(recs)
    strict = sum(1 for r in recs if r["parse_status"] == "strict")
    fb = n - strict
    truncated = sum(1 for r in recs if r["truncated"])
    empty = sum(1 for r in recs if r["empty"])
    sor = round(strict / n, 3)
    fallback_rate = round(fb / n, 3)

    # ---- the five dimensions ----
    card_temp = prov.get("temperature")
    rec, mx = prov.get("rec_output_tokens"), prov.get("max_output_tokens")
    ctx = prov.get("context_window")

    sor_ok = sor >= args.min_sor
    fp_ok = fallback_rate <= args.max_fallback
    afc_ok = fp_ok and empty == 0
    mandate = args.temperature if args.temperature is not None else card_temp
    tca_ok = mandate is not None and abs(settings["temperature"] - mandate) < 1e-9
    tbc_flags = []
    if not prov["found"]:
        tbc_flags.append("no provider-default card")
    else:
        if rec and args.num_predict < rec:
            tbc_flags.append(f"budget {args.num_predict} < rec {rec}")
        if mx and args.num_predict > mx:
            tbc_flags.append(f"budget {args.num_predict} > max {mx}")
        if ctx and args.num_ctx > ctx:
            tbc_flags.append(f"num_ctx {args.num_ctx} > window {ctx}")
        if truncated:
            tbc_flags.append(f"{truncated} truncated (finish_reason=length)")
    tbc_ok = not tbc_flags

    checks = {
        "SOR": {"pass": sor_ok, "value": f"{sor} ({strict}/{n} first-pass)", "threshold": f">= {args.min_sor}"},
        "AFC": {"pass": afc_ok, "value": f"temp={settings['temperature']} top_p={settings['top_p']} "
                f"top_k={settings['top_k']} empty={empty}", "threshold": "flags behaved, no empties"},
        "TCA": {"pass": tca_ok, "value": f"operating={settings['temperature']} vs mandated={mandate}"
                + (" (task-mandated)" if args.temperature is not None else " (provider default)"),
                "threshold": "== task-mandated temperature"},
        "TBC": {"pass": tbc_ok, "value": f"budget={args.num_predict} rec={rec} max={mx} trunc={truncated}"
                + ("" if tbc_ok else " — " + "; ".join(tbc_flags)), "threshold": "rec <= budget <= max, no truncation"},
        "FP": {"pass": fp_ok, "value": f"fallback={fallback_rate} ({fb}/{n})", "threshold": f"<= {args.max_fallback}"},
    }
    gate_pass = all(c["pass"] for c in checks.values())
    names = {"SOR": "Structured Output Reliability", "AFC": "API Flag Compliance",
             "TCA": "Temperature Compliance", "TBC": "Token Budget Compliance",
             "FP": "Failure Predictability"}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    outdir = HERE / "results" / "_preflight" / f"{args.model.replace(':', '-')}_{stamp}"
    outdir.mkdir(parents=True, exist_ok=True)
    report = {"model": args.model, "model_version": version, "provider_default": prov,
              "settings": settings, "n_calls": n,
              "metrics": {"strict": strict, "fallback": fb, "sor": sor, "fallback_rate": fallback_rate,
                          "truncated": truncated, "empty": empty},
              "checks": checks, "gate_pass": gate_pass, "timestamp_utc": stamp}
    (outdir / "ihf_preflight.json").write_text(json.dumps(report, indent=2))

    gate_line = "PASS — cleared for full run" if gate_pass else "FAIL — fix wiring, do not launch"
    md = [f"# IHF Preflight — {args.model}", "",
          f"**Gate:** {'✅ ' if gate_pass else '❌ '}{gate_line}", "",
          f"- Model version (pinned): `{version}`",
          f"- Settings: temp `{settings['temperature']}` · top_p `{settings['top_p']}` · "
          f"top_k `{settings['top_k']}` · seed `{settings['seed']}` · num_ctx `{settings['num_ctx']}` · "
          f"num_predict `{settings['num_predict']}`",
          f"- Card: `{prov.get('card')}` · calls: `{n}` · {stamp}", "",
          "| Dimension | Result | Value | Threshold |", "|---|---|---|---|"]
    for dim in ("SOR", "AFC", "TCA", "TBC", "FP"):
        c = checks[dim]
        md.append(f"| {names[dim]} | {'PASS' if c['pass'] else '**FAIL**'} | {c['value']} | {c['threshold']} |")
    (outdir / "ihf_preflight.md").write_text("\n".join(md) + "\n")

    print("=" * 64)
    print(f"IHF PREFLIGHT — {args.model}  version={version}")
    for dim in ("SOR", "AFC", "TCA", "TBC", "FP"):
        c = checks[dim]
        print(f"  {dim}  {'PASS' if c['pass'] else 'FAIL'}  {c['value']}")
    print(f"  GATE: {gate_line}")
    print(f"  report: {outdir / 'ihf_preflight.md'}")
    print("=" * 64)
    sys.exit(0 if gate_pass else 1)


if __name__ == "__main__":
    main()

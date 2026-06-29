#!/usr/bin/env python3
"""IHF-compliant full runner for the FailureSensorIQ cold rung.

Runs a model at its provider settings (from the model card) over the full single-answer
set, captures IHF telemetry on every call, writes a run manifest (provenance), and is
resumable with a compatibility check that refuses to blend incompatible records.
Correctness is recorded but is task quality, not integration hygiene.

    python3 run_ihf.py --model gemma3:4b --num-predict 2048
"""
import argparse
import hashlib
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import ihf
import run_cold

HERE = Path(__file__).resolve().parent


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE).decode().strip()[:12]
    except Exception:
        return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--num-predict", type=int, required=True)
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--temperature", type=float, default=None,
                    help="task-mandated temperature (ICAF); default = provider card temperature")
    ap.add_argument("--min-sor", type=float, default=0.95)
    ap.add_argument("--max-fallback", type=float, default=0.05)
    ap.add_argument("--asset", default=None, help="run only questions for this asset")
    ap.add_argument("--n", type=int, default=None, help="cap to first N (shuffled) questions")
    ap.add_argument("--think", action="store_true", help="enable native thinking (reasoning on)")
    ap.add_argument("--no-gate", action="store_true", help="diagnostic: do not abort on the rolling gate")
    args = ap.parse_args()

    prov = ihf.resolve_defaults(args.model)
    if not prov["found"]:
        sys.exit(f"no provider-default card for {args.model} — record one first")
    version = ihf.model_version(args.model)
    mandated_temp = args.temperature if args.temperature is not None else prov.get("temperature")
    settings = {"temperature": mandated_temp, "top_p": prov.get("top_p"),
                "top_k": prov.get("top_k"), "seed": args.seed,
                "num_ctx": args.num_ctx, "num_predict": args.num_predict,
                "think": True if args.think else None}

    rows = run_cold.load()
    by_id = {r["id"]: r for r in rows}
    ids = sorted(by_id)
    if args.asset:
        ids = [i for i in ids if by_id[i]["asset_name"] == args.asset]
        if not ids:
            sys.exit(f"no questions for asset {args.asset!r}")
    # seeded shuffle so the rolling gate's first 10% is representative across assets
    order = ids[:]
    random.Random(args.seed).shuffle(order)
    if args.n:
        order = order[:args.n]
        ids = sorted(order)
    prompt_fp = hashlib.sha256(run_cold.build_prompt(by_id[ids[0]]).encode()).hexdigest()[:16]

    tag = args.model.replace(":", "-").replace("/", "-")
    asset_tag = "_" + args.asset.replace(" ", "-") if args.asset else ""
    n_tag = f"_n{args.n}" if args.n else ""
    temp_tag = f"_t{args.temperature}" if args.temperature is not None else ""
    out = HERE / f"results_ihf_{tag}{asset_tag}{n_tag}{temp_tag}.jsonl"
    manifest_path = HERE / f"results_ihf_{tag}{asset_tag}{n_tag}{temp_tag}.manifest.json"
    manifest = {"model": args.model, "model_version": version, "settings": settings,
                "prompt_fingerprint": prompt_fp, "git_commit": git_commit(),
                "sample": f"{args.asset or 'full_single_answer'}{n_tag}", "n_total": len(ids),
                "started_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")}

    # resume with compatibility check
    done = {}
    if out.exists() and manifest_path.exists():
        prev = json.loads(manifest_path.read_text())
        bad = [k for k in ("model", "model_version", "prompt_fingerprint") if prev.get(k) != manifest[k]]
        bad += ["settings." + k for k in settings if prev.get("settings", {}).get(k) != settings[k]]
        if bad:
            sys.exit(f"resume refused — manifest mismatch on {bad}; move the old result aside")
        for line in out.open():
            if line.strip():
                r = json.loads(line)
                done[r["id"]] = r
        manifest = prev
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2))

    todo = [i for i in order if i not in done]
    fresh = len(done) == 0
    n_gate = min(max(round(0.10 * len(ids)), 50), 250)  # rolling gate sample: 10%, floor 50, cap 250
    print(f"IHF run — {args.model} v{version} @ temp={settings['temperature']}: "
          f"{len(ids)} Q, {len(done)} done, {len(todo)} to run"
          + (f"; rolling gate at first {n_gate}" if fresh else ""), flush=True)

    f = out.open("a")
    for i, _id in enumerate(todo):
        r = by_id[_id]
        content, tele = ihf.call(args.model, run_cold.build_prompt(r), settings)
        parsed = ihf.parse_answer(content, r["option_ids"])
        key = run_cold.correct_label(r)
        rec = {"id": _id, "asset": r["asset_name"], "qtype": r["question_type"], "key": key,
               "parsed": parsed, "correct": parsed == key,
               "parse_status": "strict" if parsed is not None else "fallback",
               "finish_reason": tele["finish_reason"], "prompt_tokens": tele["prompt_tokens"],
               "completion_tokens": tele["completion_tokens"], "empty": tele["empty"],
               "thinking_present": tele.get("thinking_present"),
               "attempts": tele["attempts"], "ms": tele["ms"],
               "thinking": tele.get("thinking", ""), "raw": content}
        f.write(json.dumps(rec) + "\n")
        f.flush()
        done[_id] = rec
        # rolling gate: on a fresh run, evaluate hygiene over the first n_gate (representative) calls
        if fresh and not args.no_gate and (i + 1) == n_gate:
            seg = [done[j] for j in todo[:n_gate]]
            fbr = sum(1 for x in seg if x["parse_status"] == "fallback") / n_gate
            trunc = sum(1 for x in seg if x["finish_reason"] == "length")
            gate = {"n": n_gate, "sor": round(1 - fbr, 3), "fallback_rate": round(fbr, 3),
                    "truncated": trunc, "pass": (1 - fbr) >= args.min_sor and fbr <= args.max_fallback and trunc == 0}
            manifest["rolling_gate"] = gate
            manifest_path.write_text(json.dumps(manifest, indent=2))
            if not gate["pass"]:
                f.close()
                print(f"\nROLLING GATE FAIL at {n_gate} calls: SOR={gate['sor']} "
                      f"fallback={gate['fallback_rate']} truncated={trunc} — aborting (wiring off-spec)", flush=True)
                sys.exit(2)
            print(f"\nrolling gate PASS at {n_gate}: SOR={gate['sor']} "
                  f"fallback={gate['fallback_rate']} truncated={trunc}", flush=True)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(todo)} done", flush=True)
    f.close()

    res = [done[i] for i in ids if i in done]
    n = len(res)
    c = sum(x["correct"] for x in res)
    fb = sum(1 for x in res if x["parse_status"] == "fallback")
    trunc = sum(1 for x in res if x["finish_reason"] == "length")
    print(f"\naccuracy: {c/n:.1%} ({c}/{n})  [task quality]")
    print(f"IHF telemetry: SOR(strict)={1 - fb/n:.3f}  fallback={fb/n:.3f}  truncated={trunc}")
    manifest["completed_utc"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    manifest["n_done"] = n
    manifest["accuracy"] = round(c / n, 4)
    manifest["ihf"] = {"sor": round(1 - fb / n, 3), "fallback_rate": round(fb / n, 3), "truncated": trunc}
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"saved {out} + {manifest_path.name}")


if __name__ == "__main__":
    main()

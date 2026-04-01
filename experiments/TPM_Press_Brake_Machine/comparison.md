# Model Comparison — TPM Cross-Pillar Reasoning
**Dataset:** experiments_v2.md (V2 — chaotic, incomplete, multi-source)
**Task:** Surface hidden cross-pillar connections in TPM data for PB-07 press brake
**Models:** Qwen3.5 (local, Ollama) vs o3-mini (Azure OpenAI)

---

> **Run history:** Three runs recorded below.
> - **Run 1** — Prompts diverged (red herring instruction only in o3-mini). Results not comparable.
> - **Run 2** — Qwen3.5 re-run with aligned prompts. Clean on Qwen3.5 side; o3-mini still on Run 1 prompt.
> - **Run 3** — o3-mini re-run with aligned prompt + 32k token budget. Both models now on identical prompts. **Definitive comparison.**

---

---

# Run 1 — Mismatched Prompts (Invalid Comparison)
> Qwen3.5 prompt did not include the red herring instruction. o3-mini prompt did. Results below reflect prompt differences, not model differences.

## Scorecard — Hidden Connections Found

| Connection ID | Description | Qwen3.5 | o3-mini |
|---|---|---|---|
| V2-A | Jordan induction gap → AM log gaps → QM-005 (name never appears in QM) | FOUND (HIGH) | FOUND (MEDIUM) |
| V2-B | FI-003 stalled + ADM-005 pending → wrong reference block → QM-006 | FOUND (HIGH) | FOUND (HIGH) |
| V2-C | WO-0432 PB-04 breakdown → Ray diverted → PM deferral cascade on PB-07 | FOUND (MEDIUM) | FOUND (HIGH) |
| V2-E | FI-001 quick-change, no safety review → unlogged near-misses → SHE-004 | FOUND (MEDIUM) | FOUND (HIGH) |
| V2-F | ADM-002 HSLA without ECN → accelerated die wear → ADM-004 as "routine" | FOUND (HIGH) | FOUND (HIGH) |
| V2-H | FI-002 stroke speed above EEM rating → hydraulic pressure spikes → WO-0433 unresolved | FOUND (MEDIUM) | FOUND (MEDIUM) |
| **Score** | | **6 / 6** | **6 / 6** |

---

## Scorecard — Red Herrings

| Red Herring | Description | Qwen3.5 | o3-mini |
|---|---|---|---|
| V2-D | MS-447 batch change — looks causal, is only an amplifier | NOT flagged | FLAGGED explicitly |
| V2-G | PB-04 operator reassignment — looks like staffing cause, is unrelated to quality | NOT flagged | FLAGGED (partial — stream cut off) |

---

## Qualitative Differences

### Confidence Calibration
- **Qwen3.5** rated most connections HIGH, including ones with weak evidence (e.g., V2-A — Jordan's name doesn't appear in QM records at all). Overconfident.
- **o3-mini** rated V2-A as MEDIUM and the latent structural risk (V2-H) as MEDIUM. More calibrated where evidence is indirect or inferred.

### Red Herring Reasoning
- **Qwen3.5** did not produce a "Red Herrings" section at all. Its bias is toward finding connections, not disconfirming them. It folded MS-447 into other chains without flagging the distinction.
- **o3-mini** explicitly named both red herrings, explained the mechanism for why they *look* connected, and stated why the evidence doesn't support them as root causes. This is the more useful output for an investigator who needs to know what *not* to chase.

### Reasoning Trace
- **Qwen3.5** exposed 6,588 chars of visible thinking — you can see it checking each pillar, verifying IDs, deciding between interpretations. The thinking was explicit, step-by-step, and traceable.
- **o3-mini** returned 0 reasoning token chars — Azure does not surface o3 reasoning tokens in the stream. The output appears "from nowhere". You see conclusions without the audit trail.

### Structural Quality
- Both produced well-formed reports with issue ID chains and mechanism explanations.
- **o3-mini** stream terminated slightly early (V2-G explanation cut off) — likely hit `max_completion_tokens: 8000`. Increase to resolve.
- **Qwen3.5** ran to full completion without truncation.

### Causal Chain Depth
- **o3-mini** Connection 3 (PB-04 resource chain) explicitly named the *compounding* effect — deferral of both WO-0431 and WO-0433 simultaneously, which Qwen3.5 also found but described less precisely.
- **Qwen3.5** Connection 6 (hydraulic degradation) added an extra cross-link to FI-002 that o3-mini treated separately — arguably more integrated thinking, but risks over-connecting.

---

## Summary Verdict

| Dimension | Winner |
|---|---|
| Connections found | Tie (6/6 both) |
| Red herring identification | o3-mini |
| Confidence calibration | o3-mini |
| Reasoning transparency | Qwen3.5 |
| Full completion (no truncation) | Qwen3.5 |
| Speed (approx.) | Qwen3.5 (local, no API latency) |
| Cost | Qwen3.5 (free / local) |

**The meaningful gap is red herring identification.** An agent that can't say "this looks connected but isn't" will send maintenance teams down dead ends. That's where o3-mini is ahead in this task. The connection-finding quality is equivalent.

**The meaningful gap in Qwen3.5's favour is reasoning transparency.** In an industrial context, an investigator needs to explain *how* they got there — not just what they found. The visible thinking chain makes Qwen3.5's output auditable in a way o3-mini's isn't (at least via Azure).

---

# Run 2 — Identical Prompts (Clean Comparison)
> Both agents received the same system prompt and investigation prompt, including the red herring instruction.
> Qwen3.5: `report_v2.md` | o3-mini: `report_o3.md` (Run 1 o3-mini, needs re-run with aligned prompt)

## Scorecard — Hidden Connections Found

| Connection ID | Description | Qwen3.5 (Run 2) | o3-mini (Run 1 — prompt gap) |
|---|---|---|---|
| V2-A | Jordan induction gap → AM log gaps → QM-005 | FOUND (HIGH) | FOUND (MEDIUM) |
| V2-B | FI-003 stalled + ADM-005 → wrong reference block → QM-006 | FOUND (HIGH) | FOUND (HIGH) |
| V2-C | WO-0432 PB-04 breakdown → Ray diverted → PM deferral cascade | FOUND (HIGH) | FOUND (HIGH) |
| V2-E | FI-001 quick-change → unlogged near-misses → SHE-004 | FOUND (HIGH) | FOUND (HIGH) |
| V2-F | ADM-002 HSLA without ECN → accelerated die wear → ADM-004 as "routine" | FOUND (MEDIUM) | FOUND (HIGH) |
| V2-H | FI-002 stroke speed above EEM rating → hydraulic pressure spikes | FOUND (HIGH) | FOUND (MEDIUM) |
| **Score** | | **6 / 6** | **6 / 6** *(Run 1)* |

## Scorecard — Red Herrings

| Red Herring | Description | Qwen3.5 (Run 2) | o3-mini (Run 1) |
|---|---|---|---|
| V2-D | MS-447 batch change — amplifier, not root cause | FLAGGED — explained as partial red herring, causal distinction made | FLAGGED explicitly |
| V2-G | PB-04 staffing reassignment — explains AM gap, not quality | FLAGGED — correctly linked AM gap to staffing but separated from quality cause chain | FLAGGED (partial — truncated) |
| V2-F | Die wear signal — real but needs cross-pillar analysis to be actionable | FLAGGED as additional red herring | NOT flagged separately |

## What Changed Between Run 1 and Run 2 (Qwen3.5)

| Dimension | Run 1 (wrong prompt) | Run 2 (correct prompt) |
|---|---|---|
| Red herrings flagged | 0 | 3 (V2-D, V2-G, V2-F) |
| Confidence calibration | Mostly HIGH, overconfident | More nuanced — V2-F rated MEDIUM |
| Report length | 8,843 chars | 9,306 chars |
| Thinking length | 6,588 chars | 5,249 chars |

## Updated Qualitative Differences (Run 2 basis)

### Red Herring Reasoning
With identical prompts, **both models flag red herrings**. The gap from Run 1 was entirely prompt design. Qwen3.5 in Run 2 actually flagged a third red herring (V2-F — die wear signal) that o3-mini did not surface separately.

### Confidence Calibration
Still a difference. Qwen3.5 Run 2 rated V2-C (PB-04 resource chain) as HIGH where o3-mini rated it HIGH too — confidence scores now broadly aligned. Qwen3.5 still shows slight tendency to rate connections confidently even when evidence is indirect.

### Reasoning Transparency
Unchanged. Qwen3.5 exposes full thinking trace (~5,000 chars). o3-mini returns zero reasoning tokens via Azure. In an auditable industrial context, Qwen3.5's trace is operationally more valuable.

### Additional Finding (Qwen3.5 Run 2 only)
Qwen3.5 explicitly noted that V2-F (die wear signal) is real but only actionable via cross-pillar analysis — a nuanced distinction that wasn't in o3-mini's output. This suggests the thinking model may generate additional signal when given room to reason.

## Updated Summary Verdict (Run 2)

| Dimension | Qwen3.5 (Run 2) | o3-mini (Run 1, needs re-run) |
|---|---|---|
| Connections found | 6 / 6 | 6 / 6 |
| Red herrings flagged | 3 (V2-D, V2-G, V2-F) | 2 (V2-D, V2-G partial) |
| Confidence calibration | Mostly accurate | Mostly accurate |
| Reasoning transparency | Full trace visible | Zero — opaque |
| Completion (no truncation) | Full | Truncated at 8k tokens (fixed to 32k) |
| Speed | Local, no latency | API latency |
| Cost | Free / local | Azure consumption |

**Primary finding:** The Run 1 "gap" in red herring reasoning was a prompt engineering failure, not a model capability difference. With identical prompts, Qwen3.5 matches or exceeds o3-mini on this task — and surfaces more red herrings.

**Open item:** o3-mini needs a clean re-run with the aligned prompt and 32k token limit to produce a fully valid comparison.

---

# Run 3 — Identical Prompts, Full Token Budget (Definitive Comparison)
> Both agents: same system prompt + investigation prompt. Qwen3.5: `num_ctx 8192`. o3-mini: `max_completion_tokens 32000`, `reasoning_effort high`.

## Scorecard — Hidden Connections Found

| Connection ID | Description | Qwen3.5 (Run 2) | o3-mini (Run 3) |
|---|---|---|---|
| V2-A | Jordan induction gap → AM log gaps → QM-005 | FOUND (HIGH) | FOUND (MEDIUM) |
| V2-B | FI-003 stalled + ADM-005 → wrong reference block → QM-006 | FOUND (HIGH) | FOUND (HIGH) |
| V2-C | WO-0432 PB-04 breakdown → Ray diverted → PM deferral cascade | FOUND (HIGH) | FOUND (MEDIUM) |
| V2-E | FI-001 quick-change → unlogged near-misses → SHE-004 | FOUND (HIGH) | FOUND (MEDIUM) |
| V2-F | ADM-002 HSLA without ECN → accelerated die wear → ADM-004 as "routine" | FOUND (MEDIUM) | FOUND (MEDIUM) |
| V2-H | FI-002 stroke speed above EEM rating → hydraulic pressure spikes | FOUND (HIGH) | FOUND (MEDIUM) |
| **Score** | | **6 / 6** | **6 / 6** |

## Scorecard — Red Herrings

| Red Herring | Description | Qwen3.5 (Run 2) | o3-mini (Run 3) |
|---|---|---|---|
| V2-D | MS-447 batch change — amplifier, not root cause | FLAGGED | FLAGGED |
| V2-G | PB-04 staffing reassignment — explains AM gap, not quality | FLAGGED | FLAGGED |
| V2-F | Die wear signal — real but needs cross-pillar analysis | FLAGGED as 3rd red herring | NOT flagged separately (treated as Connection 5) |

## Qualitative Differences — Definitive

### Connections Found
Tie. Both 6/6. No difference on recall.

### Confidence Calibration
**o3-mini rated everything MEDIUM** in Run 3 — 5 out of 6 connections received MEDIUM confidence, only V2-B (reference block mismatch) got HIGH. This is either better calibration on uncertain data, or conservative bias. Qwen3.5 spread ratings across HIGH and MEDIUM, which maps more intuitively to the actual evidence strength in the dataset.

### Red Herring Handling
Tie with a nuance. Both flagged V2-D and V2-G. Qwen3.5 additionally flagged V2-F. o3-mini folded V2-F into Connection 5 as a finding rather than a red herring — a defensible choice, but different framing.

### Reasoning Transparency
Unchanged across all runs. Qwen3.5 exposes full thinking trace. o3-mini returns zero reasoning tokens via Azure — outputs appear without audit trail.

### Report Completeness
o3-mini Run 3: 10,365 chars (longest output). Qwen3.5 Run 2: 9,306 chars. Both fully complete with no truncation.

### Priority Actions Quality
- **Qwen3.5** priority actions are more specific and operationally actionable — names exact part numbers, timelines, and escalation framing ("quality risk not routine procurement").
- **o3-mini** priority actions are higher-level and more strategic — "launch a comprehensive audit", "reassess all operational changes through an engineering review". Useful for a manager, less useful for a maintenance technician.

## Definitive Summary Verdict

| Dimension | Qwen3.5 | o3-mini |
|---|---|---|
| Connections found | 6 / 6 | 6 / 6 |
| Red herrings flagged | 3 | 2 (+ 1 folded into findings) |
| Confidence calibration | Spread (HIGH/MEDIUM) | Conservative (mostly MEDIUM) |
| Reasoning transparency | Full trace visible | Zero — opaque |
| Actionability of recommendations | Specific, operational | Strategic, high-level |
| Report completeness | Full | Full |
| Speed | Local, no latency | API latency |
| Cost | Free / local | Azure consumption |

**Final finding:** With identical prompts and full token budgets, both models perform equivalently on connection recall. The real differences are:
1. **Reasoning transparency** — Qwen3.5 wins. The visible thinking trace is auditable and explainable to a maintenance team.
2. **Recommendation specificity** — Qwen3.5 wins on operational detail. o3-mini outputs are more suitable for a management briefing.
3. **Confidence calibration** — o3-mini's MEDIUM-heavy ratings may reflect better uncertainty handling on incomplete data, or may be overcautious. Requires more runs to determine.
4. **Cost and sovereignty** — Qwen3.5 runs entirely local. For an industrial setting with data sensitivity concerns, this is a significant operational factor.

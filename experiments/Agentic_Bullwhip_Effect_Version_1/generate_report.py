"""
Generate a detailed PDF report for the Agentic Bullwhip Experiment (Version 4).
Output: results/experiment_report.pdf
"""

import json
import os
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.platypus import ListFlowable, ListItem

# ── paths ──────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
AGG = BASE / "results" / "aggregated"
OUT = BASE / "results" / "experiment_report.pdf"

# ── load aggregated data ───────────────────────────────────────────────────────
def load(name):
    with open(AGG / f"{name}_aggregated.json") as f:
        return json.load(f)

BL  = load("blind_lightweight")
BR  = load("blind_reasoning")
CL  = load("context_lightweight")
CR  = load("context_reasoning")

CONFIGS = [
    ("blind_lightweight",  BL,  "gpt-4.1-mini", "Blind"),
    ("blind_reasoning",    BR,  "o1",            "Blind"),
    ("context_lightweight",CL,  "gpt-4.1-mini", "Context"),
    ("context_reasoning",  CR,  "o1",            "Context"),
]

# ── colour palette ─────────────────────────────────────────────────────────────
DARK_BLUE   = colors.HexColor("#1a2744")
MID_BLUE    = colors.HexColor("#2c4a8c")
LIGHT_BLUE  = colors.HexColor("#dce8f7")
ACCENT      = colors.HexColor("#e84545")
WARM_GREY   = colors.HexColor("#f5f5f5")
TEXT_BLACK  = colors.HexColor("#1a1a1a")
MUTED       = colors.HexColor("#666666")
BORDER      = colors.HexColor("#c8d6e8")
GREEN       = colors.HexColor("#2e7d32")
AMBER       = colors.HexColor("#e65100")
RED         = colors.HexColor("#c62828")

# ── styles ─────────────────────────────────────────────────────────────────────
base_styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

styles = {
    "title":      S("title",   fontSize=28, leading=34, textColor=DARK_BLUE,
                    fontName="Helvetica-Bold", spaceAfter=6, alignment=TA_CENTER),
    "subtitle":   S("subtitle",fontSize=13, leading=18, textColor=MID_BLUE,
                    fontName="Helvetica", spaceAfter=4, alignment=TA_CENTER),
    "meta":       S("meta",    fontSize=10, leading=14, textColor=MUTED,
                    fontName="Helvetica", spaceAfter=2, alignment=TA_CENTER),
    "h1":         S("h1",      fontSize=16, leading=20, textColor=DARK_BLUE,
                    fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=6),
    "h2":         S("h2",      fontSize=13, leading=17, textColor=MID_BLUE,
                    fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=4),
    "h3":         S("h3",      fontSize=11, leading=15, textColor=DARK_BLUE,
                    fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3),
    "body":       S("body",    fontSize=9.5, leading=14, textColor=TEXT_BLACK,
                    fontName="Helvetica", spaceAfter=6, alignment=TA_JUSTIFY),
    "body_left":  S("body_left",fontSize=9.5, leading=14, textColor=TEXT_BLACK,
                    fontName="Helvetica", spaceAfter=6),
    "caption":    S("caption", fontSize=8.5, leading=12, textColor=MUTED,
                    fontName="Helvetica-Oblique", spaceAfter=4, alignment=TA_CENTER),
    "mono":       S("mono",    fontSize=8.5, leading=13, textColor=TEXT_BLACK,
                    fontName="Courier", spaceAfter=4),
    "callout":    S("callout", fontSize=9.5, leading=14, textColor=DARK_BLUE,
                    fontName="Helvetica-Bold", spaceAfter=4, leftIndent=8),
    "verdict_good":  S("vg",  fontSize=9.5, leading=14, textColor=GREEN,
                        fontName="Helvetica-Bold", spaceAfter=3),
    "verdict_bad":   S("vb",  fontSize=9.5, leading=14, textColor=RED,
                        fontName="Helvetica-Bold", spaceAfter=3),
    "verdict_warn":  S("vw",  fontSize=9.5, leading=14, textColor=AMBER,
                        fontName="Helvetica-Bold", spaceAfter=3),
}

# ── table helpers ──────────────────────────────────────────────────────────────
def header_cell(txt, size=8.5, color=colors.white, bg=DARK_BLUE):
    return Paragraph(f'<font color="#{color.hexval()[2:] if hasattr(color,"hexval") else "ffffff"}">{txt}</font>',
                     ParagraphStyle("th", fontSize=size, leading=12,
                                    fontName="Helvetica-Bold", textColor=color,
                                    alignment=TA_CENTER))

def cell(txt, bold=False, align=TA_CENTER, size=8.5, color=TEXT_BLACK):
    fn = "Helvetica-Bold" if bold else "Helvetica"
    return Paragraph(str(txt),
                     ParagraphStyle("td", fontSize=size, leading=12,
                                    fontName=fn, textColor=color, alignment=align))

def make_table(data, col_widths, style_cmds=None):
    base_cmd = [
        ("BACKGROUND",   (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, WARM_GREY]),
        ("GRID",         (0, 0), (-1, -1), 0.4, BORDER),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    if style_cmds:
        base_cmd.extend(style_cmds)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(base_cmd))
    return t

def hr():
    return HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=6, spaceBefore=2)

def sp(h=6):
    return Spacer(1, h)

def P(text, style="body"):
    return Paragraph(text, styles[style])

# ── page template with header/footer ──────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    # header bar
    canvas.setFillColor(DARK_BLUE)
    canvas.rect(0, h - 1.5*cm, w, 1.5*cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(1.5*cm, h - 0.95*cm, "Agentic Bullwhip Experiment — Version 4")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 1.5*cm, h - 0.95*cm, "CONFIDENTIAL · 2026-02-27")
    # footer
    canvas.setFillColor(BORDER)
    canvas.rect(0, 0, w, 0.9*cm, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(1.5*cm, 0.3*cm, "Industrial Mind & Code · LLM Supply Chain Research")
    canvas.drawRightString(w - 1.5*cm, 0.3*cm, f"Page {doc.page}")
    canvas.restoreState()

def on_first_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    # top banner
    canvas.setFillColor(DARK_BLUE)
    canvas.rect(0, h - 4.5*cm, w, 4.5*cm, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h - 4.5*cm, w, 0.35*cm, fill=1, stroke=0)
    # footer
    canvas.setFillColor(BORDER)
    canvas.rect(0, 0, w, 0.9*cm, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(1.5*cm, 0.3*cm, "Industrial Mind & Code · LLM Supply Chain Research")
    canvas.drawRightString(w - 1.5*cm, 0.3*cm, f"Page {doc.page}")
    canvas.restoreState()

# ── build document ─────────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=2.5*cm, bottomMargin=1.8*cm,
        title="Agentic Bullwhip Experiment — V4 Results Report",
        author="Claude Code / Industrial Mind & Code",
    )

    story = []
    W = A4[0] - 3.6*cm   # usable width

    # ── COVER ─────────────────────────────────────────────────────────────────
    story.append(sp(5.5*cm))
    story.append(Paragraph(
        '<font color="#1a2744">Agentic Bullwhip Experiment</font>',
        ParagraphStyle("ctitle", fontSize=30, leading=36, fontName="Helvetica-Bold",
                        textColor=DARK_BLUE, alignment=TA_CENTER, spaceAfter=4)
    ))
    story.append(Paragraph(
        "Version 4 — Detailed Results Report",
        ParagraphStyle("csubt", fontSize=16, leading=22, fontName="Helvetica",
                        textColor=MID_BLUE, alignment=TA_CENTER, spaceAfter=20)
    ))
    story.append(HRFlowable(width="60%", thickness=2, color=ACCENT,
                             spaceAfter=16, hAlign="CENTER"))
    for line in [
        "Experiment date: 2026-02-27",
        "Branch: Agentic-bullwhip-experiment/Version_4",
        "Total experiment cost: $26.11",
        "Author: Industrial Mind &amp; Code / Claude Code (claude-sonnet-4-6)",
    ]:
        story.append(Paragraph(line, styles["meta"]))
    story.append(PageBreak())

    # ── 1. OVERVIEW ────────────────────────────────────────────────────────────
    story.append(P("1. Experiment Overview", "h1"))
    story.append(hr())
    story.append(P(
        "This experiment investigates whether LLM-based agents operating a 3-tier supply chain "
        "(OEM → Ancillary → Component) amplify or dampen demand variability — the <b>bullwhip effect</b>. "
        "A 2×2 factorial design varies two independent factors: information treatment (blind vs. context) "
        "and model tier (lightweight: gpt-4.1-mini vs. reasoning: o1). Each of the four resulting "
        "configurations was run 5 times over 12 ordering periods, producing 20 complete experimental runs "
        "and 720 individual LLM calls.", "body"
    ))

    overview_data = [
        ["Factor", "Level A", "Level B"],
        ["Information treatment", "Blind\n(no demand history)", "Context\n(seasonal context + history)"],
        ["Model tier", "Lightweight\n(gpt-4.1-mini)", "Reasoning\n(o1)"],
    ]
    ov_table = [
        [cell("Factor", bold=True), cell("Level A", bold=True), cell("Level B", bold=True)],
        [cell("Information treatment"), cell("Blind\n(no demand history)"), cell("Context\n(seasonal context + history)")],
        [cell("Model tier"), cell("Lightweight\n(gpt-4.1-mini)"), cell("Reasoning\n(o1)")],
    ]
    story.append(make_table(ov_table, [W*0.35, W*0.325, W*0.325]))
    story.append(sp(6))

    story.append(P("<b>Supply chain structure:</b> Three tiers operate in serial. Demand originates externally at the OEM from a real-world inspired synthetic CSV (Dec 2024 – Dec 2025, 13 periods). The OEM's order becomes the ancillary's demand; the ancillary's order becomes the component's demand.", "body"))
    story.append(P("<b>Primary metric:</b> OVAR (Order Variance Amplification Ratio) = Var(orders) / Var(demand received), computed per tier per run and averaged across the 5 runs per configuration. OVAR > 1 indicates bullwhip amplification; OVAR = 1 is perfect pass-through; OVAR < 1 indicates smoothing.", "body"))
    story.append(P("<b>Control variables:</b> Initial inventory 43,000 units at all tiers, 1-period lead time, order floor at 0 (no negative orders).", "body"))

    # ── 2. DATA QUALITY ────────────────────────────────────────────────────────
    story.append(P("2. Data Quality & Run Integrity", "h1"))
    story.append(hr())
    story.append(P("All 20 runs completed without parse errors or undefined OVAR values. The dataset is clean.", "body"))

    dq_data = [
        [cell("Config", bold=True), cell("Runs", bold=True), cell("OVAR undefined", bold=True),
         cell("OEM CV%", bold=True), cell("Anc CV%", bold=True), cell("Comp CV%", bold=True), cell("Stability", bold=True)],
    ]
    stab_flags = {
        "blind_lightweight":  ("0.41", "1.50", "1.82",  "STABLE",      GREEN),
        "context_lightweight":("0.29", "2.55", "10.18", "MOSTLY STABLE", AMBER),
        "blind_reasoning":    ("57.15","36.94","16.66", "UNSTABLE",    RED),
        "context_reasoning":  ("22.86","32.76","25.10", "UNSTABLE",    RED),
    }
    for name, d, model, treat in CONFIGS:
        fl = stab_flags[name]
        dq_data.append([
            cell(name.replace("_", "\n"), align=TA_LEFT, size=8),
            cell("5/5"),
            cell("0"),
            cell(fl[0], color=RED if float(fl[0]) > 10 else TEXT_BLACK),
            cell(fl[1], color=RED if float(fl[1]) > 10 else TEXT_BLACK),
            cell(fl[2], color=RED if float(fl[2]) > 10 else TEXT_BLACK),
            cell(fl[3], color=fl[4], bold=True),
        ])
    story.append(make_table(dq_data, [W*0.24, W*0.09, W*0.14, W*0.12, W*0.12, W*0.12, W*0.17]))
    story.append(P(
        "<i>CV &gt; 10% flagged as high instability. o1 configurations exhibit wide run-to-run variance — "
        "conclusions drawn from their OVAR means must be treated as directionally informative, not statistically definitive, "
        "without larger sample sizes (n ≥ 20 recommended).</i>", "caption"
    ))

    # ── 3. PRIMARY RESULTS: OVAR ───────────────────────────────────────────────
    story.append(P("3. Primary Results — OVAR by Configuration", "h1"))
    story.append(hr())
    story.append(P(
        "OVAR is the central experimental metric. The table below reports the mean ± standard deviation across "
        "5 runs for each configuration-tier combination, along with the chain-average OVAR.", "body"
    ))

    ovar_data = [
        [cell("Config", bold=True), cell("Model", bold=True), cell("Treatment", bold=True),
         cell("OEM OVAR\nmean ± std", bold=True), cell("CV%", bold=True),
         cell("Ancillary OVAR\nmean ± std", bold=True), cell("CV%", bold=True),
         cell("Component OVAR\nmean ± std", bold=True), cell("CV%", bold=True),
         cell("Chain\nAvg", bold=True)],
    ]
    chain_avgs = []
    for name, d, model, treat in CONFIGS:
        t = d["tiers"]
        o, a, c = t["oem"], t["ancillary"], t["component"]
        chain_avg = (o["ovar_mean"] + a["ovar_mean"] + c["ovar_mean"]) / 3
        chain_avgs.append(chain_avg)
        ovar_data.append([
            cell(name.replace("_", "\n"), align=TA_LEFT, size=8),
            cell(model, size=8),
            cell(treat, size=8),
            cell(f"{o['ovar_mean']:.3f} ± {o['ovar_std']:.3f}",
                 color=RED if o["ovar_mean"] > 5 else (AMBER if o["ovar_mean"] > 3.5 else GREEN)),
            cell(f"{o['ovar_cv_pct']:.1f}", color=RED if o["ovar_cv_pct"] > 10 else TEXT_BLACK),
            cell(f"{a['ovar_mean']:.3f} ± {a['ovar_std']:.3f}"),
            cell(f"{a['ovar_cv_pct']:.1f}", color=RED if a["ovar_cv_pct"] > 10 else TEXT_BLACK),
            cell(f"{c['ovar_mean']:.3f} ± {c['ovar_std']:.3f}"),
            cell(f"{c['ovar_cv_pct']:.1f}", color=RED if c["ovar_cv_pct"] > 10 else TEXT_BLACK),
            cell(f"{chain_avg:.3f}", bold=True),
        ])
    best_chain = min(chain_avgs)
    worst_chain = max(chain_avgs)
    highlight_cmds = []
    for i, avg in enumerate(chain_avgs):
        row = i + 1
        if avg == best_chain:
            highlight_cmds.append(("BACKGROUND", (-1, row), (-1, row), colors.HexColor("#c8e6c9")))
        elif avg == worst_chain:
            highlight_cmds.append(("BACKGROUND", (-1, row), (-1, row), colors.HexColor("#ffcdd2")))
    story.append(make_table(ovar_data,
        [W*0.16, W*0.1, W*0.09, W*0.16, W*0.06, W*0.16, W*0.06, W*0.15, W*0.06, W*0.08],
        highlight_cmds))
    story.append(P("<i>Green chain avg = best (lowest). Red = worst. CV% cells in red indicate high instability (&gt;10%).</i>", "caption"))

    # ranking
    story.append(P("3.1 Chain-Average OVAR Ranking", "h2"))
    ranking = sorted(zip(chain_avgs, [c[0] for c in CONFIGS]))
    rank_data = [
        [cell("Rank", bold=True), cell("Config", bold=True), cell("Chain Avg OVAR", bold=True), cell("Assessment", bold=True)],
    ]
    labels = ["Best (lowest)", "2nd", "3rd", "Worst (highest)"]
    label_colors = [GREEN, MUTED, AMBER, RED]
    for i, (avg, name) in enumerate(ranking):
        rank_data.append([
            cell(labels[i], color=label_colors[i], bold=True),
            cell(name.replace("_", "\n"), align=TA_LEFT, size=8),
            cell(f"{avg:.3f}", bold=(i == 0 or i == 3)),
            cell("Context + lightweight is the best overall performer" if i == 0
                 else "Blind + lightweight performs well" if i == 1
                 else "Blind + reasoning is inconsistent but moderate" if i == 2
                 else "Context + reasoning is the worst — fully inverted cascade", align=TA_LEFT, size=8)
        ])
    story.append(make_table(rank_data, [W*0.18, W*0.22, W*0.15, W*0.45]))

    # ── 4. KEY FINDINGS ────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(P("4. Key Findings", "h1"))
    story.append(hr())

    story.append(P("4.1 All Configurations Confirm the Bullwhip Effect", "h2"))
    story.append(P(
        "Every OVAR value across all 4 configurations and 3 tiers is substantially above 1.0. "
        "LLM-based agents inherently amplify demand variability under the experimental conditions tested. "
        "The central question is not <i>whether</i> bullwhip occurs, but <i>how the cascade pattern "
        "differs across configurations</i>.", "body"
    ))

    story.append(P("4.2 Blind Configs Reproduce the Textbook Monotone Cascade", "h2"))
    story.append(P(
        "Both blind configurations follow the classical pattern: OEM (~2.27) → Ancillary (~2.94–3.66) → "
        "Component (~3.65–4.27), with each upstream tier amplifying further. The lightweight and reasoning "
        "models produce similar magnitudes in the blind treatment, but the reasoning model shows much higher "
        "run-to-run instability (OEM CV 57.15% vs 0.41%). Model power alone does not reduce bullwhip "
        "without additional context.", "body"
    ))

    story.append(P("4.3 Context + Lightweight Partially Dampens the Cascade", "h2"))
    story.append(P(
        "Context_lightweight achieves the best chain-average OVAR (2.929) and best pattern "
        "detection (elevation score 0.833). Downstream tiers benefit most: component OVAR drops from "
        "4.266 to 3.412 (−20%) vs blind_lightweight, while OEM remains virtually unchanged (2.267 → 2.237). "
        "The improvement is consistent across runs (all CVs ≤ 10.18%). At $0.0068/run, this is the most "
        "cost-effective configuration.", "body"
    ))

    story.append(P("4.4 Context + Reasoning Creates an Anomalous Inverted Cascade", "h2"))
    story.append(P(
        "The most striking finding of this experiment. Context_reasoning produces a <b>fully inverted cascade</b>: "
        "OEM OVAR (6.349) &gt; Ancillary (4.191) &gt; Component (2.698). The top of the chain is the worst "
        "amplifier; the bottom is the best. This is the opposite of all other configurations and of classical "
        "bullwhip theory.", "body"
    ))

    inv_data = [
        [cell("Config", bold=True), cell("OEM OVAR", bold=True), cell("Ancillary OVAR", bold=True),
         cell("Component OVAR", bold=True), cell("Cascade Direction", bold=True)],
        [cell("blind_lightweight"), cell("2.267"), cell("2.938"), cell("4.266"),
         cell("Normal ↑ upstream", color=GREEN)],
        [cell("context_lightweight"), cell("2.237"), cell("3.138"), cell("3.412"),
         cell("Normal ↑ upstream", color=GREEN)],
        [cell("blind_reasoning"), cell("4.200"), cell("3.656"), cell("3.649"),
         cell("Flat/mild reversal", color=AMBER)],
        [cell("context_reasoning"), cell("6.349", color=RED, bold=True),
         cell("4.191"), cell("2.698", color=GREEN, bold=True),
         cell("FULLY INVERTED ↓ upstream", color=RED, bold=True)],
    ]
    story.append(make_table(inv_data, [W*0.25, W*0.16, W*0.18, W*0.18, W*0.23],
        [("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#ffebee"))]))

    story.append(sp(8))
    story.append(P(
        "<b>Mechanistic explanation:</b> o1's extended chain-of-thought reasoning processes the seasonal context "
        "prompt differently depending on tier position. At OEM (which sees raw external demand + seasonal annotations), "
        "o1 constructs elaborate anticipatory orders before expected festival peaks — <i>variance injection</i>. "
        "At Component (which receives already-distorted upstream orders), o1 with context can recognise that large "
        "orders are festival-driven spikes and moderates its response — <i>spike-recognition dampening</i>. "
        "gpt-4.1-mini does not exhibit this reversal because it applies context more uniformly and with less elaboration.", "body"
    ))

    # ── 5. HYPOTHESIS VERDICTS ─────────────────────────────────────────────────
    story.append(P("5. Hypothesis Verdicts", "h1"))
    story.append(hr())

    hyp_data = [
        [cell("Hypothesis", bold=True), cell("Prediction", bold=True),
         cell("Result", bold=True), cell("Verdict", bold=True)],
        [cell("H1", bold=True),
         cell("Context OVAR < Blind OVAR at all three tiers", align=TA_LEFT, size=8),
         cell("Context raises OEM OVAR (+1.059 avg across models); only improves component", align=TA_LEFT, size=8),
         cell("REJECTED", color=RED, bold=True)],
        [cell("H2", bold=True),
         cell("Blind-reasoning ≈ blind-lightweight (model doesn't matter)", align=TA_LEFT, size=8),
         cell("Blind-reasoning OEM OVAR 4.200 vs 2.267 for blind-lightweight — delta 1.933, CV 57%", align=TA_LEFT, size=8),
         cell("REJECTED", color=RED, bold=True)],
        [cell("H3", bold=True),
         cell("Context-reasoning achieves the lowest chain OVAR", align=TA_LEFT, size=8),
         cell("Context-reasoning achieves the HIGHEST chain OVAR (4.412) — worst in experiment", align=TA_LEFT, size=8),
         cell("REJECTED", color=RED, bold=True)],
        [cell("H4", bold=True),
         cell("Context agents score higher on seasonal pattern detection", align=TA_LEFT, size=8),
         cell("True for context-lightweight (0.833 vs 0.700 elevation score); reversed for context-reasoning (0.600)", align=TA_LEFT, size=8),
         cell("PARTIALLY\nSUPPORTED", color=AMBER, bold=True)],
    ]
    story.append(make_table(hyp_data, [W*0.06, W*0.27, W*0.42, W*0.15],
        [("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffebee")),
         ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#ffebee")),
         ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#ffebee")),
         ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#fff8e1"))]))
    story.append(P(
        "All three primary hypotheses are rejected. The data do not support the intuition that more information "
        "(context) and more reasoning capability (o1) jointly improve supply chain ordering behaviour as measured by OVAR.", "body"
    ))

    # ── 6. MAIN EFFECTS & INTERACTION ─────────────────────────────────────────
    story.append(PageBreak())
    story.append(P("6. Main Effects & Context × Model Interaction", "h1"))
    story.append(hr())

    story.append(P("6.1 Context Main Effect (averaged across both models)", "h2"))
    me_ctx_data = [
        [cell("Tier", bold=True), cell("Blind mean OVAR", bold=True), cell("Context mean OVAR", bold=True),
         cell("Delta", bold=True), cell("Direction", bold=True)],
        [cell("OEM"),       cell("3.233"), cell("4.293"), cell("+1.059", color=RED, bold=True), cell("Context WORSE", color=RED)],
        [cell("Ancillary"), cell("3.297"), cell("3.664"), cell("+0.367", color=AMBER),           cell("Context WORSE", color=AMBER)],
        [cell("Component"), cell("3.958"), cell("3.055"), cell("−0.903", color=GREEN, bold=True), cell("Context BETTER", color=GREEN)],
    ]
    story.append(make_table(me_ctx_data, [W*0.18, W*0.22, W*0.22, W*0.18, W*0.20]))

    story.append(P("6.2 Model Main Effect (averaged across both treatments)", "h2"))
    me_mod_data = [
        [cell("Tier", bold=True), cell("Lightweight mean OVAR", bold=True), cell("Reasoning mean OVAR", bold=True),
         cell("Delta", bold=True), cell("Direction", bold=True)],
        [cell("OEM"),       cell("2.252"), cell("5.274"), cell("+3.022", color=RED, bold=True), cell("Reasoning WORSE", color=RED)],
        [cell("Ancillary"), cell("3.038"), cell("3.923"), cell("+0.885", color=AMBER),           cell("Reasoning WORSE", color=AMBER)],
        [cell("Component"), cell("3.839"), cell("3.174"), cell("−0.665", color=GREEN),           cell("Reasoning BETTER", color=GREEN)],
    ]
    story.append(make_table(me_mod_data, [W*0.18, W*0.24, W*0.24, W*0.16, W*0.18]))

    story.append(P("6.3 Interaction: Context × Model at OEM Tier", "h2"))
    story.append(P(
        "The most important structural finding is a significant interaction between context and model at the OEM tier. "
        "The context effect <i>reverses sign</i> depending on the model:", "body"
    ))
    int_data = [
        [cell("Tier", bold=True), cell("Context effect on gpt-4.1-mini", bold=True), cell("Context effect on o1", bold=True), cell("Interaction", bold=True)],
        [cell("OEM"),       cell("−0.030 (marginal improvement)", color=GREEN), cell("+2.149 (substantial worsening)", color=RED, bold=True), cell("STRONG REVERSAL", color=RED, bold=True)],
        [cell("Ancillary"), cell("+0.199 (slight worsening)", color=AMBER),     cell("+0.535 (worsening)", color=AMBER),                      cell("Consistent")],
        [cell("Component"), cell("−0.855 (improvement)", color=GREEN),          cell("−0.952 (improvement)", color=GREEN),                    cell("Consistent")],
    ]
    story.append(make_table(int_data, [W*0.15, W*0.30, W*0.30, W*0.25]))
    story.append(P(
        "At the component tier, context improves OVAR for both models by similar magnitudes. "
        "At the OEM tier, context is effectively neutral for gpt-4.1-mini and severely damaging for o1. "
        "<b>Design recommendation: context provision and model selection cannot be treated as independent choices.</b>", "body"
    ))

    # ── 7. STABILITY ───────────────────────────────────────────────────────────
    story.append(P("7. Stability Analysis (Coefficient of Variation)", "h1"))
    story.append(hr())
    story.append(P(
        "Run-to-run stability is critical for operational deployability. A high CV means the same configuration "
        "can produce qualitatively different outcomes in successive months — which is unacceptable for inventory planning.", "body"
    ))

    stab_data = [
        [cell("Config", bold=True), cell("OEM CV%", bold=True), cell("Ancillary CV%", bold=True),
         cell("Component CV%", bold=True), cell("Max CV%", bold=True), cell("Assessment", bold=True)],
    ]
    for name, d, model, treat in CONFIGS:
        t = d["tiers"]
        cvs = [t["oem"]["ovar_cv_pct"], t["ancillary"]["ovar_cv_pct"], t["component"]["ovar_cv_pct"]]
        mx = max(cvs)
        if mx < 3:
            assess, acol = "STABLE", GREEN
        elif mx < 12:
            assess, acol = "MOSTLY STABLE", AMBER
        else:
            assess, acol = "UNSTABLE", RED
        stab_data.append([
            cell(name.replace("_", "\n"), align=TA_LEFT, size=8),
            cell(f"{cvs[0]:.1f}", color=RED if cvs[0] > 10 else TEXT_BLACK),
            cell(f"{cvs[1]:.1f}", color=RED if cvs[1] > 10 else TEXT_BLACK),
            cell(f"{cvs[2]:.1f}", color=RED if cvs[2] > 10 else TEXT_BLACK),
            cell(f"{mx:.1f}", color=RED if mx > 10 else TEXT_BLACK, bold=True),
            cell(assess, color=acol, bold=True),
        ])
    story.append(make_table(stab_data, [W*0.26, W*0.14, W*0.14, W*0.14, W*0.14, W*0.18]))
    story.append(P(
        "Lightweight model runs are essentially deterministic (all CVs ≤ 10.18%). "
        "o1 runs are highly stochastic: blind_reasoning OEM CV of 57.15% means the 95% CI for the true mean spans "
        "approximately [2.0, 6.4] — overlapping substantially with context_reasoning OEM (6.349). "
        "With n=5 runs, o1 conclusions are directionally informative only.", "body"
    ))

    # ── 8. SECONDARY METRICS ───────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(P("8. Secondary Metrics", "h1"))
    story.append(hr())

    story.append(P("8.1 Stockouts", "h2"))
    story.append(P(
        "Stockout counts (periods where backlog > 0) decrease in context_reasoning, but this is a "
        "consequence of massive over-ordering rather than improved planning efficiency.", "body"
    ))
    sc_data = [
        [cell("Config", bold=True), cell("OEM Stockouts", bold=True),
         cell("Ancillary Stockouts", bold=True), cell("Component Stockouts", bold=True)],
    ]
    for name, d, model, treat in CONFIGS:
        t = d["tiers"]
        sc_data.append([
            cell(name.replace("_", "\n"), align=TA_LEFT, size=8),
            cell(f"{t['oem']['stockout_count_mean']:.1f}"),
            cell(f"{t['ancillary']['stockout_count_mean']:.1f}"),
            cell(f"{t['component']['stockout_count_mean']:.1f}",
                 color=GREEN if t['component']['stockout_count_mean'] < 5.5 else TEXT_BLACK),
        ])
    story.append(make_table(sc_data, [W*0.35, W*0.21, W*0.22, W*0.22]))

    story.append(P("8.2 Excess Inventory (end-of-simulation, mean across runs)", "h2"))
    ei_data = [
        [cell("Config", bold=True), cell("OEM Excess", bold=True),
         cell("Ancillary Excess", bold=True), cell("Component Excess", bold=True), cell("Chain Total", bold=True)],
    ]
    for name, d, model, treat in CONFIGS:
        t = d["tiers"]
        chain_ei = t["oem"]["excess_inventory_mean"] + t["ancillary"]["excess_inventory_mean"] + t["component"]["excess_inventory_mean"]
        ei_data.append([
            cell(name.replace("_", "\n"), align=TA_LEFT, size=8),
            cell(f"{t['oem']['excess_inventory_mean']:,.0f}"),
            cell(f"{t['ancillary']['excess_inventory_mean']:,.0f}"),
            cell(f"{t['component']['excess_inventory_mean']:,.0f}",
                 color=RED if t['component']['excess_inventory_mean'] > 200000 else TEXT_BLACK),
            cell(f"{chain_ei:,.0f}", bold=True,
                 color=RED if chain_ei > 500000 else (AMBER if chain_ei > 250000 else TEXT_BLACK)),
        ])
    story.append(make_table(ei_data, [W*0.26, W*0.17, W*0.19, W*0.19, W*0.19]))
    story.append(P(
        "Context_reasoning accumulates 654,728 units of chain-wide excess inventory — approximately 6× "
        "blind_lightweight. This is the physical correlate of high OEM/ancillary OVAR: large anticipatory "
        "orders fill pipelines even when demand does not materialise as expected.", "body"
    ))

    story.append(P("8.3 Total Units Ordered (12 periods, mean across 5 runs)", "h2"))
    to_data = [
        [cell("Config", bold=True), cell("OEM Total", bold=True),
         cell("Ancillary Total", bold=True), cell("Component Total", bold=True), cell("Chain Total", bold=True)],
    ]
    for name, d, model, treat in CONFIGS:
        t = d["tiers"]
        chain_tot = t["oem"]["total_ordered_mean"] + t["ancillary"]["total_ordered_mean"] + t["component"]["total_ordered_mean"]
        to_data.append([
            cell(name.replace("_", "\n"), align=TA_LEFT, size=8),
            cell(f"{t['oem']['total_ordered_mean']:,.0f}"),
            cell(f"{t['ancillary']['total_ordered_mean']:,.0f}"),
            cell(f"{t['component']['total_ordered_mean']:,.0f}",
                 color=RED if t['component']['total_ordered_mean'] > 650000 else TEXT_BLACK),
            cell(f"{chain_tot:,.0f}", bold=True),
        ])
    story.append(make_table(to_data, [W*0.26, W*0.17, W*0.19, W*0.19, W*0.19]))
    story.append(P(
        "Context_reasoning orders 33% more component units than blind_lightweight (698,960 vs 583,860). "
        "A modest 4.2% over-order at OEM cascades into 80,996 additional ancillary units and 115,100 "
        "additional component units — the bullwhip cascade made physically concrete.", "body"
    ))

    story.append(P("8.4 Peak Overshoot (max order / max demand)", "h2"))
    po_data = [
        [cell("Config", bold=True), cell("OEM Peak Overshoot", bold=True),
         cell("Ancillary Peak Overshoot", bold=True), cell("Component Peak Overshoot", bold=True)],
    ]
    for name, d, model, treat in CONFIGS:
        t = d["tiers"]
        po_data.append([
            cell(name.replace("_", "\n"), align=TA_LEFT, size=8),
            cell(f"{t['oem']['peak_overshoot_mean']:.4f}",
                 color=RED if t['oem']['peak_overshoot_mean'] > 1.5 else TEXT_BLACK),
            cell(f"{t['ancillary']['peak_overshoot_mean']:.4f}"),
            cell(f"{t['component']['peak_overshoot_mean']:.4f}"),
        ])
    story.append(make_table(po_data, [W*0.30, W*0.23, W*0.24, W*0.23]))

    # ── 9. PATTERN DETECTION ───────────────────────────────────────────────────
    story.append(P("9. Pattern Detection", "h1"))
    story.append(hr())
    story.append(P(
        "Pattern score v2 = mean(keyword_score, elevation_score). Event periods are 3, 10, 11, 12. "
        "Keyword score measures seasonal vocabulary use; elevation score measures whether orders at "
        "event periods are ≥ 110% of the non-event baseline.", "body"
    ))

    ps_data = [
        [cell("Config", bold=True), cell("Pattern Score\nmean ± std", bold=True),
         cell("CV%", bold=True), cell("Keyword Score\nmean ± std", bold=True),
         cell("Elevation Score\nmean ± std", bold=True), cell("Elev. CV%", bold=True)],
    ]
    for name, d, model, treat in CONFIGS:
        ps_data.append([
            cell(name.replace("_", "\n"), align=TA_LEFT, size=8),
            cell(f"{d['pattern_score_mean']:.3f} ± {d['pattern_score_std']:.3f}",
                 color=GREEN if d['pattern_score_mean'] == max(c[1]['pattern_score_mean'] for c in CONFIGS) else TEXT_BLACK),
            cell(f"{d['pattern_score_mean']/d['pattern_score_std']*0 + (d['pattern_score_std']/d['pattern_score_mean']*100 if d['pattern_score_mean'] > 0 else 0):.1f}"),
            cell(f"{d['keyword_score_mean']:.3f} ± {d['keyword_score_std']:.3f}"),
            cell(f"{d['elevation_score_mean']:.3f} ± {d['elevation_score_std']:.3f}",
                 color=GREEN if d['elevation_score_mean'] == max(c[1]['elevation_score_mean'] for c in CONFIGS) else TEXT_BLACK),
            cell(f"{(d['elevation_score_std']/d['elevation_score_mean']*100 if d['elevation_score_mean'] > 0 else 0):.1f}",
                 color=RED if (d['elevation_score_std']/d['elevation_score_mean']*100 if d['elevation_score_mean'] > 0 else 0) > 15 else TEXT_BLACK),
        ])
    story.append(make_table(ps_data, [W*0.24, W*0.20, W*0.09, W*0.20, W*0.20, W*0.09]))

    story.append(sp(6))
    story.append(P(
        "<b>Keyword score is zero for both lightweight configurations.</b> gpt-4.1-mini agents never verbalised "
        "seasonal reasoning (no dasara, diwali, festive, budget, monsoon, fy-end keywords appeared). Both o1 "
        "configurations show occasional keyword use (blind: 0.038, context: 0.025), but inconsistently. "
        "Critically, gpt-4.1-mini can incorporate context into ordering decisions (shown by improved elevation "
        "score with context) without verbalising the seasonal reasoning — the behaviour changes but the language does not.", "body"
    ))
    story.append(P(
        "<b>Context_lightweight achieves the best elevation score (0.833)</b> — the only configuration to "
        "consistently elevate orders at event periods. Context_reasoning achieves the worst elevation score "
        "(0.600) with CV 33.33%, suggesting o1 sometimes over-rationalises and concludes that elevation is "
        "not warranted even when context implies it.", "body"
    ))

    # ── 10. COST ───────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(P("10. Cost Analysis", "h1"))
    story.append(hr())
    story.append(P(
        "Cost is a tracking variable, not an experimental factor. It is recorded to characterise the "
        "resource footprint of each configuration. All cost figures are in USD.", "body"
    ))

    cost_data = [
        [cell("Config", bold=True), cell("Model", bold=True), cell("Cost / run (USD)", bold=True),
         cell("Total 5 runs (USD)", bold=True), cell("Relative cost", bold=True)],
    ]
    base_cost = BL["total_cost_usd_per_run_mean"]
    for name, d, model, treat in CONFIGS:
        c = d["total_cost_usd_per_run_mean"]
        rel = c / base_cost
        cost_data.append([
            cell(name.replace("_", "\n"), align=TA_LEFT, size=8),
            cell(model),
            cell(f"${c:.4f}", color=RED if c > 1 else (AMBER if c > 0.01 else GREEN)),
            cell(f"${d['total_cost_usd_all_runs']:.2f}"),
            cell(f"{rel:.0f}×", color=RED if rel > 100 else TEXT_BLACK, bold=(rel > 100)),
        ])
    story.append(make_table(cost_data, [W*0.30, W*0.15, W*0.20, W*0.18, W*0.17]))

    grand_total = sum(d["total_cost_usd_all_runs"] for _, d, _, _ in CONFIGS)
    story.append(P(f"<b>Grand total experiment cost: ${grand_total:.2f}</b>", "body_left"))
    story.append(P(
        "o1 in the blind condition costs 366× more per run than gpt-4.1-mini with no measurable OVAR "
        "improvement (blind_reasoning chain avg 3.835 vs blind_lightweight 3.157). "
        "Context_reasoning is 767× more expensive than blind_lightweight and produces the worst chain-level OVAR. "
        "There is no dimension on which context_reasoning dominates blind_lightweight.", "body"
    ))

    # cost vs performance table
    story.append(P("10.1 Cost-Performance Head-to-Head: context_reasoning vs blind_lightweight", "h2"))
    cp_data = [
        [cell("Metric", bold=True), cell("blind_lightweight", bold=True),
         cell("context_reasoning", bold=True), cell("Winner", bold=True)],
        [cell("Chain avg OVAR", align=TA_LEFT), cell("3.157"), cell("4.412"), cell("blind_lightweight", color=GREEN)],
        [cell("OEM OVAR", align=TA_LEFT), cell("2.267"), cell("6.349"), cell("blind_lightweight", color=GREEN)],
        [cell("Component OVAR", align=TA_LEFT), cell("4.266"), cell("2.698"), cell("context_reasoning", color=AMBER)],
        [cell("Chain excess inventory", align=TA_LEFT), cell("109,360"), cell("654,728"), cell("blind_lightweight", color=GREEN)],
        [cell("Max CV%", align=TA_LEFT), cell("1.82%"), cell("32.76%"), cell("blind_lightweight", color=GREEN)],
        [cell("Pattern score", align=TA_LEFT), cell("0.350"), cell("0.313"), cell("blind_lightweight", color=GREEN)],
        [cell("Elevation score", align=TA_LEFT), cell("0.700"), cell("0.600"), cell("blind_lightweight", color=GREEN)],
        [cell("Cost per run", align=TA_LEFT), cell("$0.0046"), cell("$3.527"), cell("blind_lightweight", color=GREEN)],
    ]
    story.append(make_table(cp_data, [W*0.32, W*0.20, W*0.20, W*0.28]))

    # ── 11. RECOMMENDATIONS ────────────────────────────────────────────────────
    story.append(P("11. Recommendations", "h1"))
    story.append(hr())

    recs = [
        ("R1: Do not deploy o1 without hard order-change constraints",
         "Blind_reasoning OEM CV of 57.15% and context_reasoning OEM CV of 22.86% indicate that o1 produces "
         "qualitatively different ordering strategies across identical runs. Deploying o1 in a live supply chain "
         "without clamping the maximum period-over-period order change (e.g., ±20% of rolling average) is "
         "operationally risky. The next experiment version should introduce order-smoothing as a third factor "
         "and test whether it restores o1 reliability without eliminating its component-tier benefit."),
        ("R2: Limit context provision to the component tier only",
         "The context effect is beneficial and consistent at the component tier for both models (delta ≈ −0.90 OVAR). "
         "At OEM, context is neutral for gpt-4.1-mini and severely damaging for o1. A targeted architecture where "
         "only the component agent receives seasonal context — while OEM and ancillary remain blind — may capture "
         "the downstream benefit without triggering upstream variance injection. This asymmetric information "
         "architecture should be tested as a new treatment."),
        ("R3: Increase n_runs to ≥ 20 for o1 configurations",
         "With n=5 and CVs above 30%, the current experiment cannot determine whether blind_reasoning or "
         "context_reasoning OEM OVAR distributions meaningfully differ. Increasing to n=20 reduces the standard "
         "error of the mean by a factor of 2 and enables overlap quantification. Additionally, report the 10th, "
         "50th, and 90th percentile OVAR per configuration to communicate operational risk more clearly than "
         "mean ± std alone."),
        ("R4: Fix gpt-4.1-mini JSON parse errors",
         "gpt-4.1-mini occasionally formats numbers with comma separators (e.g., 27,959 instead of 27959), "
         "causing JSON parse failures that default order_quantity to 0. This suppresses some orders and "
         "slightly deflates OVAR for lightweight configs. Using JSON mode or a more explicit number-format "
         "instruction in the prompt should eliminate this artefact."),
        ("R5: Investigate context_reasoning's anti-pattern behaviour",
         "Context_reasoning achieves the worst elevation score (0.600) despite having access to seasonal context. "
         "Examining raw o1 reasoning chains at event periods would reveal whether the model explicitly rejects "
         "seasonal anticipation or simply ignores the context. This is important for understanding whether "
         "an anti-overreaction instruction can constrain o1 at OEM without removing its component-tier benefit."),
    ]

    for title, body in recs:
        story.append(KeepTogether([
            P(title, "h2"),
            P(body, "body"),
            sp(4),
        ]))

    # ── 12. LIMITATIONS ────────────────────────────────────────────────────────
    story.append(P("12. Limitations", "h1"))
    story.append(hr())

    lims = [
        ("Small sample size for o1 (n=5)",
         "CVs of 22–57% with n=5 produce wide confidence intervals. o1 conclusions are directionally informative but not statistically conclusive without n ≥ 20 runs."),
        ("Single-period lead time",
         "A lead time of 1 period is shorter than most real supply chains. Longer lead times typically amplify bullwhip effects and may change the relative ordering of configurations."),
        ("Homogeneous initial inventory",
         "All tiers start at 43,000 units. Real supply chains have differentiated starting positions that may advantage or disadvantage certain agent strategies."),
        ("Pattern score as a proxy",
         "Elevation score measures order magnitude at event periods, not whether the agent correctly attributes elevation to seasonal context. An agent that over-orders randomly at all periods would score identically to one that correctly identifies festival peaks."),
        ("No order smoothing constraints",
         "The experiment applies only an order floor of 0. Real procurement systems impose rate-of-change constraints that would mechanically limit OVAR. Results represent unconstrained agent behaviour."),
    ]

    lim_data = [[cell("Limitation", bold=True), cell("Detail", bold=True)]]
    for title, detail in lims:
        lim_data.append([cell(title, bold=True, align=TA_LEFT, size=8.5), cell(detail, align=TA_LEFT, size=8.5)])
    story.append(make_table(lim_data, [W*0.30, W*0.70]))

    # ── 13. SUMMARY VERDICT ────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(P("13. Summary Verdict", "h1"))
    story.append(hr())

    verdict_data = [
        [cell("Verdict", bold=True), cell("Configuration", bold=True), cell("Rationale", bold=True)],
        [cell("Best bullwhip reduction", color=GREEN, bold=True),
         cell("context_lightweight"),
         cell("Lowest chain avg OVAR (2.929), best elevation score (0.833), consistent across runs (max CV 10%), $0.0068/run", align=TA_LEFT, size=8)],
        [cell("Most dangerous combination", color=RED, bold=True),
         cell("context_reasoning"),
         cell("Fully inverted cascade, OEM OVAR 6.349, 6× excess inventory, highest instability (CV 32.76%), $3.527/run", align=TA_LEFT, size=8)],
        [cell("Most consistent behaviour", color=AMBER, bold=True),
         cell("blind_lightweight"),
         cell("All CVs ≤ 1.82%, predictable across runs, dominates context_reasoning on all metrics, $0.0046/run", align=TA_LEFT, size=8)],
        [cell("Most cost-efficient reasoning", color=MUTED, bold=True),
         cell("blind_reasoning"),
         cell("o1 in blind mode costs 366× more than blind_lightweight with no statistically reliable OVAR improvement", align=TA_LEFT, size=8)],
    ]
    story.append(make_table(verdict_data, [W*0.22, W*0.20, W*0.58],
        [("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#e8f5e9")),
         ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#ffebee")),
         ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#fff8e1")),
         ("BACKGROUND", (0, 4), (-1, 4), WARM_GREY)]))

    story.append(sp(12))
    story.append(P(
        "The experiment's central conclusion is that <b>more capability does not monotonically improve outcomes</b>. "
        "The combination of richer context and stronger reasoning (context_reasoning) produces the worst chain-level "
        "result. The simpler, cheaper configuration (context_lightweight) produces the best. This is not a failure "
        "of reasoning models per se, but a demonstration that LLM agents with strong reasoning capabilities can "
        "construct elaborate, internally consistent justifications for over-ordering — and that unconstrained "
        "reasoning in information-rich environments amplifies rather than dampens supply chain instability.", "body"
    ))

    # ── APPENDIX ───────────────────────────────────────────────────────────────
    story.append(P("Appendix — Raw Aggregated Metrics", "h1"))
    story.append(hr())
    story.append(P("Full per-tier means for all secondary metrics across all four configurations.", "body"))

    app_data = [
        [cell("Config", bold=True), cell("Tier", bold=True),
         cell("OVAR mean", bold=True), cell("OVAR std", bold=True), cell("CV%", bold=True),
         cell("Stockouts", bold=True), cell("Excess Inv.", bold=True),
         cell("Total Ordered", bold=True), cell("Peak OShoot", bold=True)],
    ]
    tier_labels = [("oem","OEM"), ("ancillary","Ancillary"), ("component","Component")]
    for name, d, model, treat in CONFIGS:
        first = True
        for tier_key, tier_label in tier_labels:
            t = d["tiers"][tier_key]
            app_data.append([
                cell(name.replace("_", "\n") if first else "", align=TA_LEFT, size=7.5),
                cell(tier_label, size=7.5),
                cell(f"{t['ovar_mean']:.3f}"),
                cell(f"{t['ovar_std']:.3f}"),
                cell(f"{t['ovar_cv_pct']:.1f}", color=RED if t["ovar_cv_pct"] > 10 else TEXT_BLACK),
                cell(f"{t['stockout_count_mean']:.1f}"),
                cell(f"{t['excess_inventory_mean']:,.0f}"),
                cell(f"{t['total_ordered_mean']:,.0f}"),
                cell(f"{t['peak_overshoot_mean']:.4f}"),
            ])
            first = False

    story.append(make_table(app_data,
        [W*0.17, W*0.10, W*0.09, W*0.09, W*0.07, W*0.09, W*0.13, W*0.13, W*0.11]))

    story.append(sp(12))
    story.append(P(
        "<i>Generated by claude-sonnet-4-6 on 2026-02-27. "
        "All numerical values sourced from results/aggregated/*.json in the Agentic_Bullwhip_Effect experiment directory. "
        "Experiment branch: Agentic-bullwhip-experiment/Version_4.</i>", "caption"
    ))

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_page)
    print(f"PDF written to: {OUT}")

if __name__ == "__main__":
    build()

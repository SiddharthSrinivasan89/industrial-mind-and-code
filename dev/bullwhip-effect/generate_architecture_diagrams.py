#!/usr/bin/env python3
"""
Generate architecture diagrams for the bullwhip experiment README.
Outputs PNG files to results/figures/.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np


FIGURES_DIR = "results/figures"


def draw_system_layers():
    """Four-layer system architecture diagram."""
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")

    layers = [
        {
            "y": 7.5, "height": 1.8,
            "color": "#dbeafe", "edge": "#2563eb",
            "title": "Orchestration Layer",
            "files": "run_experiment.py  |  supply_chain.py",
            "desc": "Experiment loop, period sequencing, metrics (OVAR), visualization",
        },
        {
            "y": 5.3, "height": 1.8,
            "color": "#fef3c7", "edge": "#d97706",
            "title": "Agent Layer",
            "files": "base_agent.py  |  blind_agent.py  |  context_agent.py",
            "desc": "Prompt construction, LLM decision parsing, order history tracking",
        },
        {
            "y": 3.1, "height": 1.8,
            "color": "#d1fae5", "edge": "#059669",
            "title": "State Layer",
            "files": "inventory_manager.py  |  AgentState dataclass",
            "desc": "Inventory tracking, backlog, deliveries, fulfillment, stockout detection",
        },
        {
            "y": 0.9, "height": 1.8,
            "color": "#fce7f3", "edge": "#db2777",
            "title": "Inference Layer",
            "files": "foundry_client.py",
            "desc": "Azure OpenAI API calls, retry + backoff, rate limiting, JSON parsing, call logging",
        },
    ]

    for layer in layers:
        box = FancyBboxPatch(
            (0.8, layer["y"]), 12.4, layer["height"],
            boxstyle="round,pad=0.15",
            facecolor=layer["color"], edgecolor=layer["edge"],
            linewidth=2.0,
        )
        ax.add_patch(box)

        ax.text(1.4, layer["y"] + layer["height"] - 0.35,
                layer["title"],
                fontsize=13, fontweight="bold", color=layer["edge"],
                va="top")

        ax.text(7.0, layer["y"] + layer["height"] / 2 + 0.15,
                layer["files"],
                fontsize=10, fontfamily="monospace", color="#374151",
                ha="center", va="center")

        ax.text(7.0, layer["y"] + layer["height"] / 2 - 0.35,
                layer["desc"],
                fontsize=9, color="#6b7280",
                ha="center", va="center", style="italic")

    # Arrows between layers
    for i in range(len(layers) - 1):
        top_y = layers[i]["y"]
        bot_y = layers[i + 1]["y"] + layers[i + 1]["height"]
        mid_x = 7.0
        ax.annotate("", xy=(mid_x, bot_y + 0.05), xytext=(mid_x, top_y - 0.05),
                     arrowprops=dict(arrowstyle="<->", color="#9ca3af",
                                     lw=1.5, connectionstyle="arc3"))

    fig.suptitle("System Architecture", fontsize=16, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(f"{FIGURES_DIR}/architecture_system_layers.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {FIGURES_DIR}/architecture_system_layers.png")


def draw_supply_chain_flow():
    """3-tier supply chain cascade with information flow."""
    fig, ax = plt.subplots(figsize=(16, 7))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 8.5)
    ax.axis("off")

    # Demand source
    demand_box = FancyBboxPatch(
        (0.5, 3.2), 2.8, 2.0,
        boxstyle="round,pad=0.15",
        facecolor="#f3f4f6", edgecolor="#6b7280", linewidth=1.5, linestyle="--",
    )
    ax.add_patch(demand_box)
    ax.text(1.9, 4.5, "Consumer\nDemand", fontsize=11, fontweight="bold",
            ha="center", va="center", color="#374151")
    ax.text(1.9, 3.65, "Vecta production\ntargets (CSV)", fontsize=8,
            ha="center", va="center", color="#6b7280", style="italic")

    # Tier boxes
    tiers = [
        {
            "x": 4.5, "label": "Tier 1: OEM", "sublabel": "Tatva Motors",
            "color": "#dbeafe", "edge": "#2563eb",
            "sees": "Consumer demand\n+ 3-month forecast",
        },
        {
            "x": 8.5, "label": "Tier 2: Lighting Mfr", "sublabel": "Headlight assembler",
            "color": "#fef3c7", "edge": "#d97706",
            "sees": "OEM's order qty\n(no forecast)",
        },
        {
            "x": 12.5, "label": "Tier 3: LED Supplier", "sublabel": "LED module producer",
            "color": "#fce7f3", "edge": "#db2777",
            "sees": "Lighting Mfr's order qty\n(no forecast)",
        },
    ]

    for tier in tiers:
        box = FancyBboxPatch(
            (tier["x"] - 1.4, 2.8), 2.8, 2.8,
            boxstyle="round,pad=0.15",
            facecolor=tier["color"], edgecolor=tier["edge"], linewidth=2.0,
        )
        ax.add_patch(box)
        ax.text(tier["x"], 5.1, tier["label"],
                fontsize=11, fontweight="bold", ha="center", va="center",
                color=tier["edge"])
        ax.text(tier["x"], 4.55, tier["sublabel"],
                fontsize=9, ha="center", va="center", color="#374151")

        # Agent + InventoryManager inside
        ax.text(tier["x"], 3.85, "Agent", fontsize=9,
                ha="center", va="center", color="#374151",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                          edgecolor="#d1d5db", linewidth=0.8))
        ax.text(tier["x"], 3.25, "InventoryMgr", fontsize=8,
                ha="center", va="center", color="#374151",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                          edgecolor="#d1d5db", linewidth=0.8))

    # Arrows: demand -> OEM -> Lighting -> Supplier
    arrow_style = dict(arrowstyle="-|>", color="#374151", lw=2.0)
    # Demand -> OEM
    ax.annotate("", xy=(3.1, 4.2), xytext=(3.3, 4.2),
                arrowprops=arrow_style)
    ax.annotate("", xy=(4.5 - 1.4, 4.2), xytext=(3.3, 4.2),
                arrowprops=arrow_style)
    # OEM -> Lighting
    ax.annotate("", xy=(8.5 - 1.4, 4.2), xytext=(4.5 + 1.4, 4.2),
                arrowprops=arrow_style)
    # Lighting -> Supplier
    ax.annotate("", xy=(12.5 - 1.4, 4.2), xytext=(8.5 + 1.4, 4.2),
                arrowprops=arrow_style)

    # Labels on arrows
    ax.text(3.45, 4.55, "demand", fontsize=8, color="#6b7280", style="italic")
    ax.text(6.5, 4.55, "OEM order qty", fontsize=8, color="#6b7280",
            ha="center", style="italic")
    ax.text(10.5, 4.55, "Mfr order qty", fontsize=8, color="#6b7280",
            ha="center", style="italic")

    # Information visibility labels below
    for tier in tiers:
        ax.text(tier["x"], 2.2, "Sees:", fontsize=8, fontweight="bold",
                ha="center", va="center", color="#374151")
        ax.text(tier["x"], 1.55, tier["sees"], fontsize=8,
                ha="center", va="center", color="#6b7280", style="italic")

    # "No inter-tier visibility" callout
    ax.text(8.0, 7.6, "No inter-tier visibility — each tier sees only orders from its immediate customer",
            fontsize=10, ha="center", va="center", color="#dc2626", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#fef2f2",
                      edgecolor="#fca5a5", linewidth=1.2))

    # LLM cloud
    ax.text(8.0, 0.5, "Azure OpenAI  (gpt-4.1-mini  |  o1)",
            fontsize=10, ha="center", va="center", color="#7c3aed",
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#ede9fe",
                      edgecolor="#a78bfa", linewidth=1.5))
    # Dashed lines from each agent to LLM
    for tier in tiers:
        ax.annotate("", xy=(8.0, 0.85), xytext=(tier["x"], 2.8),
                     arrowprops=dict(arrowstyle="-|>", color="#a78bfa",
                                     lw=1.0, linestyle="--"))

    fig.suptitle("Supply Chain Cascade — Per-Period Decision Flow",
                 fontsize=15, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(f"{FIGURES_DIR}/architecture_supply_chain_flow.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {FIGURES_DIR}/architecture_supply_chain_flow.png")


def draw_agent_decision_cycle():
    """Single-period agent decision cycle."""
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis("off")

    # Steps in the cycle
    steps = [
        {"x": 2.0, "y": 6.0, "label": "1. Sync State", "color": "#dbeafe", "edge": "#2563eb",
         "desc": "Pull inventory, backlog,\nin-transit from\nInventoryManager"},
        {"x": 6.0, "y": 6.0, "label": "2. Build Prompt", "color": "#fef3c7", "edge": "#d97706",
         "desc": "Blind: numbers only\nContext: + role, product,\ncalendar, market"},
        {"x": 10.0, "y": 6.0, "label": "3. LLM Call", "color": "#ede9fe", "edge": "#7c3aed",
         "desc": "Single-turn, stateless\nSystem + User prompt\nJSON response expected"},
        {"x": 12.0, "y": 3.5, "label": "4. Parse & Validate", "color": "#d1fae5", "edge": "#059669",
         "desc": "Extract order_quantity\nClamp negatives to 0\nStore reasoning trace"},
        {"x": 8.0, "y": 1.5, "label": "5. Process Inventory", "color": "#fce7f3", "edge": "#db2777",
         "desc": "Receive deliveries\nFulfill demand + backlog\nPlace order in transit"},
        {"x": 3.5, "y": 1.5, "label": "6. Cascade", "color": "#f3f4f6", "edge": "#6b7280",
         "desc": "Order becomes demand\nfor downstream tier\n(repeat steps 1-5)"},
    ]

    for step in steps:
        box = FancyBboxPatch(
            (step["x"] - 1.5, step["y"] - 0.8), 3.0, 1.8,
            boxstyle="round,pad=0.15",
            facecolor=step["color"], edgecolor=step["edge"], linewidth=2.0,
        )
        ax.add_patch(box)
        ax.text(step["x"], step["y"] + 0.45, step["label"],
                fontsize=11, fontweight="bold", ha="center", va="center",
                color=step["edge"])
        ax.text(step["x"], step["y"] - 0.3, step["desc"],
                fontsize=8, ha="center", va="center", color="#374151")

    # Arrows connecting the steps
    arrow_kw = dict(arrowstyle="-|>", color="#9ca3af", lw=2.0)
    # 1 -> 2
    ax.annotate("", xy=(4.5, 6.0), xytext=(3.5, 6.0), arrowprops=arrow_kw)
    # 2 -> 3
    ax.annotate("", xy=(8.5, 6.0), xytext=(7.5, 6.0), arrowprops=arrow_kw)
    # 3 -> 4
    ax.annotate("", xy=(11.5, 4.3), xytext=(11.0, 5.2), arrowprops=arrow_kw)
    # 4 -> 5
    ax.annotate("", xy=(9.5, 2.0), xytext=(10.5, 2.8), arrowprops=arrow_kw)
    # 5 -> 6
    ax.annotate("", xy=(5.0, 1.5), xytext=(6.5, 1.5), arrowprops=arrow_kw)
    # 6 -> 1 (loop)
    ax.annotate("", xy=(1.5, 5.2), xytext=(2.3, 2.3),
                arrowprops=dict(arrowstyle="-|>", color="#9ca3af", lw=2.0,
                                connectionstyle="arc3,rad=0.4"))

    # Callout: stateless
    ax.text(10.0, 7.5,
            "Each period is an independent LLM call — no conversation memory across periods",
            fontsize=9.5, ha="center", va="center", color="#dc2626", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#fef2f2",
                      edgecolor="#fca5a5", linewidth=1.2))

    fig.suptitle("Agent Decision Cycle (per tier, per period)",
                 fontsize=15, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(f"{FIGURES_DIR}/architecture_decision_cycle.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {FIGURES_DIR}/architecture_decision_cycle.png")


def draw_prompt_comparison():
    """Side-by-side comparison of blind vs context agent prompts."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 9))

    for ax in (ax1, ax2):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 12)
        ax.axis("off")

    # Blind agent
    ax1.set_title("Blind Agent", fontsize=14, fontweight="bold", color="#2563eb", pad=15)
    blind_box = FancyBboxPatch(
        (0.3, 0.3), 9.4, 11.0,
        boxstyle="round,pad=0.2",
        facecolor="#f8fafc", edgecolor="#2563eb", linewidth=2.0,
    )
    ax1.add_patch(blind_box)

    blind_fields = [
        ("System Prompt", '"Supply chain ordering agent.\nRespond with valid JSON only."', True),
        ("Inventory on hand", "46,318 units", True),
        ("Backlog", "0 units", True),
        ("Orders in transit", "43,812 units arriving month 2", True),
        ("Lead time", "1 month", True),
        ("This month's demand", "46,318 units", True),
        ("Recent order history", "Month 1: ordered 43,812 units", True),
        ("Role / Identity", "", False),
        ("Product context", "", False),
        ("Month / Year", "", False),
        ("Market / Geography", "", False),
        ("Demand forecast", "", False),
        ("Pattern analysis", "", False),
    ]

    y_pos = 10.8
    for label, value, present in blind_fields:
        color = "#059669" if present else "#dc2626"
        symbol = "+" if present else "-"
        alpha = 1.0 if present else 0.5
        ax1.text(0.8, y_pos, f"{symbol}", fontsize=12, fontweight="bold",
                 color=color, va="center", alpha=alpha)
        ax1.text(1.4, y_pos, label, fontsize=9, fontweight="bold",
                 color="#374151", va="center", alpha=alpha)
        if value:
            ax1.text(1.4, y_pos - 0.45, value, fontsize=8,
                     color="#6b7280", va="center", style="italic", alpha=alpha)
            y_pos -= 1.0
        else:
            y_pos -= 0.65

    # Context agent
    ax2.set_title("Context Agent", fontsize=14, fontweight="bold", color="#d97706", pad=15)
    context_box = FancyBboxPatch(
        (0.3, 0.3), 9.4, 11.0,
        boxstyle="round,pad=0.2",
        facecolor="#fffbeb", edgecolor="#d97706", linewidth=2.0,
    )
    ax2.add_patch(context_box)

    context_fields = [
        ("System Prompt", '"Supply chain agent in Indian\nautomotive component industry."', True),
        ("Inventory on hand", "46,318 units", True),
        ("Backlog", "0 units", True),
        ("Orders in transit", "43,812 units arriving month 2", True),
        ("Lead time", "1 month", True),
        ("This month's demand", "46,318 units (Vecta production target)", True),
        ("Recent order history", "Month 1: ordered 43,812 units", True),
        ("Role / Identity", '"Supply Chain Planner at Tatva\nMotors, manages Vecta procurement"', True),
        ("Product context", '"LED headlight assembly for the\nTatva Motors Vecta"', True),
        ("Month / Year", '"January 2025 (period 2)"', True),
        ("Market / Geography", '"India"', True),
        ("Demand forecast", "3-month lookahead (OEM only)", True),
        ("Pattern analysis", '"Analyze seasonal, cultural,\nfinancial calendar patterns"', True),
    ]

    y_pos = 10.8
    for label, value, present in context_fields:
        color = "#059669" if present else "#dc2626"
        symbol = "+"
        ax2.text(0.8, y_pos, symbol, fontsize=12, fontweight="bold",
                 color=color, va="center")
        ax2.text(1.4, y_pos, label, fontsize=9, fontweight="bold",
                 color="#374151", va="center")
        if value:
            ax2.text(1.4, y_pos - 0.45, value, fontsize=8,
                     color="#6b7280", va="center", style="italic")
            y_pos -= 1.0
        else:
            y_pos -= 0.65

    fig.suptitle("Prompt Information: Blind vs Context Agent",
                 fontsize=15, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(f"{FIGURES_DIR}/architecture_prompt_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {FIGURES_DIR}/architecture_prompt_comparison.png")


if __name__ == "__main__":
    draw_system_layers()
    draw_supply_chain_flow()
    draw_agent_decision_cycle()
    draw_prompt_comparison()
    print("\nAll architecture diagrams generated.")

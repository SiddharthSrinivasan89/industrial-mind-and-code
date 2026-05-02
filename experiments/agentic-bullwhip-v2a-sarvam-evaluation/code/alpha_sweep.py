"""
Alpha sensitivity sweep for exponential smoothing baselines.

Tests alpha in {0.10, 0.20, 0.30, 0.50} for both exp_smoothing and
order_up_to policies. Reports OVAR and stockouts at each tier and
at the OEM tier (bullwhip numerator) to check result sensitivity.

Run from the code/ directory:
    python alpha_sweep.py
"""

import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Import policy functions and demand loading from existing codebase
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from simulation import (
    TIERS,
    TierState,
    apply_fulfilment,
    policy_exp_smoothing,
    policy_order_up_to,
)

DATA_FILE = Path("data/synthetic/tatva_monthly_dispatches_25m.csv")

ALPHAS = [0.10, 0.20, 0.30, 0.50]
POLICIES = ["exp_smoothing", "order_up_to"]


def derive_S(demand_df):
    mu = demand_df["retail_demand"].mean()
    sigma = demand_df["retail_demand"].std(ddof=1)
    return int(round(mu + 1.65 * sigma)), mu, sigma


def run_baseline(demand_df, policy, alpha, S, safety_stock):
    """Run one 25-period simulation for a heuristic policy at a given alpha."""
    states = {tier: TierState(S) for tier in TIERS}
    first_demand = int(demand_df.iloc[0]["retail_demand"])
    for tier in TIERS:
        states[tier].exp_forecast = float(first_demand)

    records = []

    for _, row in demand_df.iterrows():
        period = int(row["period"])
        retail_demand = int(row["retail_demand"])

        tier_demand = retail_demand
        for tier in TIERS:
            st = states[tier]
            demand_received = tier_demand  # what this tier received before ordering

            # Receive last period's order
            st.on_hand += st.last_order

            # Fulfil demand
            result = apply_fulfilment(st.on_hand, tier_demand, st.backlog)
            st.on_hand = result["on_hand_after"]
            st.backlog = result["backlog"]

            # Period 25: fulfilment only, no ordering
            if period == 25:
                order = 0
                st.last_order = 0
            else:
                if policy == "exp_smoothing":
                    order, st.exp_forecast = policy_exp_smoothing(
                        st.exp_forecast, tier_demand, st.backlog, alpha=alpha
                    )
                elif policy == "order_up_to":
                    order, st.exp_forecast = policy_order_up_to(
                        st.exp_forecast, tier_demand,
                        st.on_hand - st.backlog, safety_stock, alpha=alpha
                    )
                st.last_order = order

            records.append({
                "tier": tier,
                "period": period,
                "order_placed": order,
                "demand_received": demand_received,
                "stockout": result["stockout"],
            })

            # Pass this tier's order as the next tier's demand
            tier_demand = order

    return records


def compute_metrics(records):
    """Compute OVAR and stockout count per tier."""
    df = pd.DataFrame(records)
    retail_var = None
    metrics = {}

    for tier in TIERS:
        t = df[df["tier"] == tier]
        orders = t["order"].tolist()
        var_orders = pd.Series(orders).var(ddof=1)
        stockouts = t["stockout"].sum()

        if tier == "OEM":
            retail_var = pd.Series(
                df[df["tier"] == "OEM"]["order"].tolist()
            ).var(ddof=1)
            # OVAR = Var(OEM orders) / Var(retail demand) — but retail demand
            # is the input, not stored in records. Compute it separately.

        metrics[tier] = {"var_orders": var_orders, "stockouts": int(stockouts)}

    return metrics


def main():
    demand_df = pd.read_csv(DATA_FILE)
    S, mu, sigma = derive_S(demand_df)
    safety_stock = max(0, S - int(round(mu)))
    retail_var = demand_df["retail_demand"].var(ddof=1)

    print(f"Demand: mean={mu:.0f}, std={sigma:.1f}, S={S}, safety_stock={safety_stock}")
    print(f"Retail demand variance: {retail_var:.1f}\n")

    header = f"{'Policy':<16} {'Alpha':>6} {'Chain OVAR':>12}  {'OEM / Anc / Comp OVAR':<30}  Stockouts"
    print(header)
    print("-" * len(header))

    results = []
    for policy in POLICIES:
        for alpha in ALPHAS:
            records = run_baseline(demand_df, policy, alpha, S, safety_stock)
            df = pd.DataFrame(records)

            # OVAR per tier = Var(order_placed) / Var(demand_received), exclude period 25
            active = df[df["period"] < df["period"].max()]
            tier_ovars = {}
            for tier in TIERS:
                t = active[active["tier"] == tier]
                var_o = t["order_placed"].var(ddof=1)
                var_d = t["demand_received"].var(ddof=1)
                tier_ovars[tier] = var_o / var_d if var_d > 0 else float("nan")

            chain_ovar = sum(tier_ovars.values()) / len(TIERS)

            stockouts = {
                tier: int(df[df["tier"] == tier]["stockout"].sum())
                for tier in TIERS
            }

            print(
                f"{policy:<16} {alpha:>6.2f} {chain_ovar:>12.3f} "
                f"  [{tier_ovars['OEM']:.2f} / {tier_ovars['Ancillary']:.2f} / {tier_ovars['Component']:.2f}]"
                f"  stockouts: OEM={stockouts['OEM']} Anc={stockouts['Ancillary']} Comp={stockouts['Component']}"
            )
            results.append({
                "policy": policy, "alpha": alpha,
                "chain_ovar": round(chain_ovar, 3),
                **{f"ovar_{t}": round(tier_ovars[t], 3) for t in TIERS},
                **{f"stockouts_{t}": stockouts[t] for t in TIERS}
            })

    print()
    print("Current default (alpha=0.30) is marked above.")
    return results


if __name__ == "__main__":
    main()

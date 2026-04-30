"""
Tests — V6 StatelessSwing.

Run from the code/ directory:
    DRY_RUN=1 pytest test_v6.py -v
"""

import math
import os
import sys

import pandas as pd
import pytest

# Ensure code/ is on path when running from this directory
sys.path.insert(0, os.path.dirname(__file__))

os.environ["DRY_RUN"] = "1"   # never hit real backends

from simulation import apply_fulfilment, policy_exp_smoothing, run_simulation, TierState
from agent_interface import (
    ALPHA_FALLBACK,
    ALPHA_VALUES,
    build_alpha_user_prompt,
    get_alpha_system_prompt,
    get_alpha_value,
)
from metrics import (
    compute_ovar,
    compute_chain_ovar,
    compute_alpha_metrics,
    summarise_condition,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def demand_df():
    """Minimal 5-period demand series (4 active + 1 fulfilment-only)."""
    return pd.DataFrame({
        "period":         [1, 2, 3, 4, 5],
        "calendar_month": ["Jan 2025", "Feb 2025", "Mar 2025", "Apr 2025", "May 2025"],
        "retail_demand":  [100, 100, 100, 100, 100],
    })


@pytest.fixture
def demand_df_25m():
    """Load the real 25-month demand series used by the experiment."""
    path = os.path.join(os.path.dirname(__file__), "../data/tatva_monthly_dispatches_25m.csv")
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# apply_fulfilment
# ---------------------------------------------------------------------------

class TestApplyFulfilment:
    def test_no_backlog_sufficient_stock(self):
        r = apply_fulfilment(on_hand=200, demand=100, backlog_prev=0)
        assert r["fulfilled"]     == 100
        assert r["shortfall"]     == 0
        assert r["on_hand_after"] == 100
        assert r["backlog"]       == 0
        assert r["stockout"]      is False

    def test_backlog_carried_forward(self):
        r = apply_fulfilment(on_hand=80, demand=100, backlog_prev=20)
        # total obligation = 120, on_hand = 80 → shortfall = 40
        assert r["fulfilled"]     == 80
        assert r["shortfall"]     == 40
        assert r["backlog"]       == 40
        assert r["stockout"]      is True

    def test_exact_fulfilment(self):
        r = apply_fulfilment(on_hand=100, demand=100, backlog_prev=0)
        assert r["shortfall"]     == 0
        assert r["on_hand_after"] == 0
        assert r["stockout"]      is False

    def test_zero_demand_zero_backlog(self):
        r = apply_fulfilment(on_hand=500, demand=0, backlog_prev=0)
        assert r["fulfilled"]     == 0
        assert r["on_hand_after"] == 500
        assert r["stockout"]      is False


# ---------------------------------------------------------------------------
# policy_exp_smoothing
# ---------------------------------------------------------------------------

class TestPolicyExpSmoothing:
    def test_alpha_0_3_no_backlog(self):
        order, new_fc = policy_exp_smoothing(forecast=100.0, demand=100, backlog=0, alpha=0.3)
        assert new_fc == pytest.approx(100.0)
        assert order == 100

    def test_backlog_added_to_order(self):
        order, _ = policy_exp_smoothing(forecast=100.0, demand=100, backlog=20, alpha=0.3)
        assert order == 120

    def test_order_floor_zero(self):
        # inventory_position much higher than forecast → order should be 0
        order, _ = policy_exp_smoothing(forecast=5.0, demand=5, backlog=-200, alpha=0.3)
        assert order == 0

    def test_alpha_0_1_slow_update(self):
        _, new_fc = policy_exp_smoothing(forecast=100.0, demand=200, backlog=0, alpha=0.1)
        assert new_fc == pytest.approx(0.1 * 200 + 0.9 * 100)

    def test_alpha_0_7_fast_update(self):
        _, new_fc = policy_exp_smoothing(forecast=100.0, demand=200, backlog=0, alpha=0.7)
        assert new_fc == pytest.approx(0.7 * 200 + 0.3 * 100)

    def test_higher_alpha_more_reactive(self):
        """Higher α should track demand swings more aggressively."""
        _, fc_slow = policy_exp_smoothing(100.0, 200, 0, alpha=0.1)
        _, fc_fast = policy_exp_smoothing(100.0, 200, 0, alpha=0.7)
        assert fc_fast > fc_slow


# ---------------------------------------------------------------------------
# build_alpha_user_prompt
# ---------------------------------------------------------------------------

class TestBuildAlphaUserPrompt:
    def test_blind_excludes_calendar_month(self):
        prompt = build_alpha_user_prompt(
            tier="OEM", condition="blind", period=1,
            calendar_month="Jan 2025", demand_history=[100],
            prev_forecast=100.0, forecast_error=None,
        )
        assert "Jan 2025" not in prompt

    def test_context_includes_calendar_month(self):
        prompt = build_alpha_user_prompt(
            tier="OEM", condition="context", period=2,
            calendar_month="Mar 2025", demand_history=[100, 110],
            prev_forecast=102.0, forecast_error=5.0,
        )
        assert "Mar 2025" in prompt

    def test_none_forecast_error_graceful(self):
        prompt = build_alpha_user_prompt(
            tier="OEM", condition="blind", period=1,
            calendar_month="Jan 2025", demand_history=[],
            prev_forecast=100.0, forecast_error=None,
        )
        assert "N/A" in prompt
        assert "first period" in prompt

    def test_empty_demand_history_graceful(self):
        prompt = build_alpha_user_prompt(
            tier="OEM", condition="blind", period=1,
            calendar_month="Jan 2025", demand_history=[],
            prev_forecast=100.0, forecast_error=None,
        )
        assert "No prior demand history" in prompt

    def test_demand_history_shown_oldest_first(self):
        prompt = build_alpha_user_prompt(
            tier="OEM", condition="blind", period=3,
            calendar_month="Mar 2025", demand_history=[80, 90, 100],
            prev_forecast=92.0, forecast_error=8.0,
        )
        # Should appear in order oldest→newest
        idx_80 = prompt.index("80")
        idx_100 = prompt.index("100")
        assert idx_80 < idx_100

    def test_stateful_includes_history(self):
        history = [
            {"period": 1, "demand": 100, "alpha_chosen": 0.3,
             "forecast_error": 5.0, "backlog": 0, "stockout": False},
        ]
        prompt = build_alpha_user_prompt(
            tier="OEM", condition="stateful", period=2,
            calendar_month="Feb 2025", demand_history=[100],
            prev_forecast=100.0, forecast_error=5.0,
            history=history,
        )
        assert "Period 1" in prompt
        assert "alpha=0.3" in prompt

    def test_stateful_stockout_flagged(self):
        history = [
            {"period": 1, "demand": 150, "alpha_chosen": 0.1,
             "forecast_error": -20.0, "backlog": 30, "stockout": True},
        ]
        prompt = build_alpha_user_prompt(
            tier="OEM", condition="stateful", period=2,
            calendar_month="Feb 2025", demand_history=[150],
            prev_forecast=110.0, forecast_error=-20.0,
            history=history,
        )
        assert "STOCKOUT" in prompt

    def test_stateful_no_history_skips_block(self):
        prompt = build_alpha_user_prompt(
            tier="OEM", condition="stateful", period=1,
            calendar_month="Jan 2025", demand_history=[],
            prev_forecast=100.0, forecast_error=None,
            history=[],
        )
        assert "Order history" not in prompt


# ---------------------------------------------------------------------------
# get_alpha_system_prompt
# ---------------------------------------------------------------------------

class TestGetAlphaSystemPrompt:
    def test_blind_same_for_all_tiers(self):
        p_oem  = get_alpha_system_prompt("OEM",       "blind")
        p_anc  = get_alpha_system_prompt("Ancillary", "blind")
        p_comp = get_alpha_system_prompt("Component", "blind")
        assert p_oem == p_anc == p_comp

    def test_context_tier_specific(self):
        p_oem  = get_alpha_system_prompt("OEM",       "context")
        p_comp = get_alpha_system_prompt("Component", "context")
        assert p_oem != p_comp
        assert "Tatva Motors" in p_oem
        assert "two tiers upstream" in p_comp

    def test_stateful_adds_history_instruction(self):
        p_ctx      = get_alpha_system_prompt("OEM", "context")
        p_stateful = get_alpha_system_prompt("OEM", "stateful")
        assert "self-correct" in p_stateful
        assert "self-correct" not in p_ctx

    def test_invalid_condition_raises(self):
        with pytest.raises(ValueError, match="Unknown condition"):
            get_alpha_system_prompt("OEM", "invalid")

    def test_all_prompts_contain_alpha_choices(self):
        for condition in ("blind", "context", "stateful"):
            for tier in ("OEM", "Ancillary", "Component"):
                prompt = get_alpha_system_prompt(tier, condition)
                assert "0.1" in prompt
                assert "0.3" in prompt
                assert "0.5" in prompt
                assert "0.7" in prompt

    def test_all_prompts_contain_json_instruction(self):
        for condition in ("blind", "context", "stateful"):
            prompt = get_alpha_system_prompt("OEM", condition)
            assert '"alpha"' in prompt
            assert '"rationale"' in prompt


# ---------------------------------------------------------------------------
# get_alpha_value (dry-run backend)
# ---------------------------------------------------------------------------

class TestGetAlphaValue:
    def test_returns_valid_alpha(self):
        result = get_alpha_value(
            tier="OEM", condition="blind", period=1,
            calendar_month="Jan 2025", demand_history=[],
            prev_forecast=100.0, forecast_error=None,
            model_tier="lightweight", run_id="test",
        )
        assert result["alpha"] in ALPHA_VALUES
        assert result["alpha_fallback"] is False

    def test_fallback_constant_is_valid_alpha(self):
        assert ALPHA_FALLBACK in ALPHA_VALUES

    def test_dry_run_returns_0_3(self):
        result = get_alpha_value(
            tier="OEM", condition="context", period=5,
            calendar_month="May 2025", demand_history=[100, 100, 100],
            prev_forecast=100.0, forecast_error=0.0,
            model_tier="lightweight", run_id="test",
        )
        assert result["alpha"] == 0.3


# ---------------------------------------------------------------------------
# run_simulation — exp_smoothing baselines
# ---------------------------------------------------------------------------

class TestRunSimulationBaselines:
    def test_exp_smooth_0_3_returns_75_records(self, demand_df_25m):
        records = run_simulation(
            demand_series=demand_df_25m, condition="blind",
            model_tier=None, policy="exp_smoothing",
            S=43609, safety_stock=5061, initial_inventory=43609,
            alpha=0.3, condition_label="exp_smooth_0.3",
        )
        assert len(records) == 75  # 25 periods × 3 tiers

    def test_exp_smooth_period_25_order_zero(self, demand_df_25m):
        records = run_simulation(
            demand_series=demand_df_25m, condition="blind",
            model_tier=None, policy="exp_smoothing",
            S=43609, safety_stock=5061, initial_inventory=43609,
            alpha=0.3, condition_label="exp_smooth_0.3",
        )
        period_25 = [r for r in records if r["period"] == 25]
        assert all(r["order_placed"] == 0 for r in period_25)

    def test_exp_smooth_period_25_alpha_none(self, demand_df_25m):
        records = run_simulation(
            demand_series=demand_df_25m, condition="blind",
            model_tier=None, policy="exp_smoothing",
            S=43609, safety_stock=5061, initial_inventory=43609,
            alpha=0.3, condition_label="exp_smooth_0.3",
        )
        period_25 = [r for r in records if r["period"] == 25]
        assert all(r["alpha_chosen"] is None for r in period_25)

    def test_exp_smooth_alpha_recorded_correctly(self, demand_df_25m):
        for alpha in (0.1, 0.3, 0.5):
            records = run_simulation(
                demand_series=demand_df_25m, condition="blind",
                model_tier=None, policy="exp_smoothing",
                S=43609, safety_stock=5061, initial_inventory=43609,
                alpha=alpha, condition_label=f"exp_smooth_{alpha}",
            )
            active = [r for r in records if r["period"] < 25]
            assert all(r["alpha_chosen"] == alpha for r in active)
            assert all(r["alpha_fallback"] is False for r in active)

    def test_exp_smooth_ovar_0_3_matches_v4_baseline(self, demand_df_25m):
        """exp_smooth_0.3 must reproduce V4 baseline OVAR (~0.545)."""
        records = run_simulation(
            demand_series=demand_df_25m, condition="blind",
            model_tier=None, policy="exp_smoothing",
            S=43609, safety_stock=5061, initial_inventory=43609,
            alpha=0.3, condition_label="exp_smooth_0.3",
        )
        df = pd.DataFrame(records)
        df["run_id"] = "single"
        ovar_df = compute_ovar(df)
        chain_ovar = compute_chain_ovar(ovar_df).iloc[0]
        assert chain_ovar == pytest.approx(0.5446, abs=0.005)

    def test_alpha_0_3_beats_0_1_and_0_5(self, demand_df_25m):
        """α=0.3 should produce lower OVAR than α=0.1 or α=0.5 on this series."""
        ovars = {}
        for alpha in (0.1, 0.3, 0.5):
            records = run_simulation(
                demand_series=demand_df_25m, condition="blind",
                model_tier=None, policy="exp_smoothing",
                S=43609, safety_stock=5061, initial_inventory=43609,
                alpha=alpha, condition_label=f"test_{alpha}",
            )
            df = pd.DataFrame(records)
            df["run_id"] = "single"
            ovars[alpha] = compute_chain_ovar(compute_ovar(df)).iloc[0]
        assert ovars[0.3] < ovars[0.1]
        assert ovars[0.3] < ovars[0.5]


# ---------------------------------------------------------------------------
# run_simulation — adaptive_alpha (dry-run backend returns 0.3 every period)
# ---------------------------------------------------------------------------

class TestRunSimulationAdaptiveAlpha:
    def test_adaptive_alpha_dry_run_matches_0_3(self, demand_df_25m):
        """Dry-run always returns alpha=0.3 → OVAR should equal exp_smooth_0.3."""
        records = run_simulation(
            demand_series=demand_df_25m, condition="blind",
            model_tier="lightweight", policy="adaptive_alpha",
            S=43609, safety_stock=5061, initial_inventory=43609,
            condition_label="mini_blind",
        )
        df = pd.DataFrame(records)
        df["run_id"] = "single"
        ovar_df = compute_ovar(df)
        chain_ovar = compute_chain_ovar(ovar_df).iloc[0]
        assert chain_ovar == pytest.approx(0.5446, abs=0.005)

    def test_adaptive_alpha_alpha_chosen_populated(self, demand_df_25m):
        records = run_simulation(
            demand_series=demand_df_25m, condition="blind",
            model_tier="lightweight", policy="adaptive_alpha",
            S=43609, safety_stock=5061, initial_inventory=43609,
            condition_label="mini_blind",
        )
        active = [r for r in records if r["period"] < 25]
        assert all(r["alpha_chosen"] in ALPHA_VALUES for r in active)
        assert all(r["alpha_fallback"] is False for r in active)

    def test_adaptive_demand_history_grows(self, demand_df_25m):
        """demand_history passed to LLM should grow each period (capped at 5)."""
        import simulation as sim_module

        captured = []
        original_get = sim_module.get_alpha_value

        def patched_get(demand_history, **kwargs):
            captured.append(list(demand_history))
            return original_get(demand_history=demand_history, **kwargs)

        sim_module.get_alpha_value = patched_get

        try:
            run_simulation(
                demand_series=demand_df_25m, condition="blind",
                model_tier="lightweight", policy="adaptive_alpha",
                S=43609, safety_stock=5061, initial_inventory=43609,
                condition_label="mini_blind",
            )
        finally:
            sim_module.get_alpha_value = original_get

        # OEM calls: period 1 gets empty list, period 2 gets 1 item, ..., period 6+ gets 5 items
        oem_calls = captured[::3]   # every 3rd call is OEM (OEM, Ancillary, Component order)
        assert len(oem_calls[0]) == 0   # period 1: no history yet
        assert len(oem_calls[1]) == 1   # period 2: 1 item
        assert len(oem_calls[5]) == 5   # period 6: capped at 5
        assert len(oem_calls[-1]) == 5  # late periods: still capped


# ---------------------------------------------------------------------------
# metrics — compute_alpha_metrics
# ---------------------------------------------------------------------------

class TestComputeAlphaMetrics:
    def _make_df(self, alphas: list[float], policy="adaptive_alpha") -> pd.DataFrame:
        """Build a minimal records DataFrame with the given alpha sequence at OEM."""
        records = []
        for i, a in enumerate(alphas):
            records.append({
                "run_id": "r1", "tier": "OEM", "policy": policy,
                "period": i + 1, "alpha_chosen": a, "alpha_fallback": False,
                "order_placed": 100, "demand_received": 100,
                "on_hand_before_order": 200, "backlog": 0,
            })
        # Add period beyond active (simulates period 25) so _active_periods works
        records.append({
            "run_id": "r1", "tier": "OEM", "policy": policy,
            "period": len(alphas) + 1, "alpha_chosen": None, "alpha_fallback": None,
            "order_placed": 0, "demand_received": 100,
            "on_hand_before_order": 100, "backlog": 0,
        })
        return pd.DataFrame(records)

    def test_alpha_mean_correct(self):
        df = self._make_df([0.1, 0.3, 0.5, 0.7])
        result = compute_alpha_metrics(df)
        assert result.iloc[0]["alpha_mean"] == pytest.approx(0.4)

    def test_alpha_fallback_rate_zero(self):
        df = self._make_df([0.3, 0.3, 0.3])
        result = compute_alpha_metrics(df)
        assert result.iloc[0]["alpha_fallback_rate"] == 0.0

    def test_alpha_entropy_uniform_is_max(self):
        """4 equally-distributed alpha values → max entropy = log2(4) = 2.0"""
        df = self._make_df([0.1, 0.3, 0.5, 0.7])
        result = compute_alpha_metrics(df)
        assert result.iloc[0]["alpha_entropy"] == pytest.approx(2.0, abs=0.01)

    def test_alpha_entropy_constant_is_zero(self):
        df = self._make_df([0.3, 0.3, 0.3, 0.3])
        result = compute_alpha_metrics(df)
        assert result.iloc[0]["alpha_entropy"] == pytest.approx(0.0, abs=0.001)

    def test_non_adaptive_policy_returns_empty(self):
        df = self._make_df([0.3, 0.3], policy="exp_smoothing")
        result = compute_alpha_metrics(df)
        assert result.empty


# ---------------------------------------------------------------------------
# summarise_condition
# ---------------------------------------------------------------------------

class TestSummariseCondition:
    def test_baseline_summary_has_no_alpha_keys(self, demand_df_25m):
        records = run_simulation(
            demand_series=demand_df_25m, condition="blind",
            model_tier=None, policy="exp_smoothing",
            S=43609, safety_stock=5061, initial_inventory=43609,
            alpha=0.3, condition_label="exp_smooth_0.3",
        )
        df = pd.DataFrame(records)
        summary = summarise_condition(df, "exp_smooth_0.3")
        assert "alpha_mean" not in summary
        assert "alpha_entropy" not in summary

    def test_adaptive_summary_has_alpha_keys(self, demand_df_25m):
        records = run_simulation(
            demand_series=demand_df_25m, condition="blind",
            model_tier="lightweight", policy="adaptive_alpha",
            S=43609, safety_stock=5061, initial_inventory=43609,
            condition_label="mini_blind",
        )
        df = pd.DataFrame(records)
        summary = summarise_condition(df, "mini_blind")
        assert "alpha_mean" in summary
        assert "alpha_entropy" in summary
        assert "alpha_fallback_rate" in summary
        assert "alpha_distribution" in summary

    def test_ovar_key_always_present(self, demand_df_25m):
        for policy, alpha in [("exp_smoothing", 0.3), ("adaptive_alpha", None)]:
            records = run_simulation(
                demand_series=demand_df_25m, condition="blind",
                model_tier="lightweight" if policy == "adaptive_alpha" else None,
                policy=policy, S=43609, safety_stock=5061, initial_inventory=43609,
                alpha=alpha or 0.3, condition_label="test",
            )
            df = pd.DataFrame(records)
            summary = summarise_condition(df, "test")
            assert "chain_ovar" in summary
            assert "tier_ovar" in summary

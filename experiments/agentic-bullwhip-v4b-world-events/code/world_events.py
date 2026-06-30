"""
World Events — disruption schedule for V3 supply chain simulation.

Three event types modelled on real disruptions:
  - Pandemic       : COVID-19 style — demand collapse + supply collapse, then demand surge
  - Conflict       : Russia-Ukraine style — supply shock, demand largely unaffected
  - Port disruption: Suez/LA-port style — acute lead time spike, short duration

Each event modifies three simulation parameters:
  - demand_multiplier   : scales retail_demand for that period (noise is applied on top)
  - fill_rate_cap       : maximum fraction of an order that can be delivered
  - lead_time_multiplier: scales the stochastic lead time draw

Outside event periods all multipliers are 1.0 and fill_rate_cap is 1.0.

Usage:
    events = WorldEvents()
    dm  = events.demand_multiplier(period)
    cap = events.fill_rate_cap(period)
    ltm = events.lead_time_multiplier(period)
    lbl = events.event_label(period)       # None if normal period
    sig = events.event_signal(period)      # news headline for unstructured prompt
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class _EventPeriod:
    """One phase of one world event."""
    start:                int
    end:                  int      # inclusive
    phase_name:           str
    demand_multiplier:    float
    fill_rate_cap:        float
    lead_time_multiplier: float
    signal:               str      # news headline shown to unstructured agents


# ---------------------------------------------------------------------------
# Event schedule
# ---------------------------------------------------------------------------
# Periods 1-36 map to Jan 2025 -- Dec 2027.
# Calibrated against real historical magnitudes documented in DESIGN.md.
#
# Pandemic (periods 7-12, mid-2025):
#   Placed in Year 1 so agents experience both the shock and the recovery
#   before the conflict arrives in Year 2.
#   Phase 1 — shock:    demand -45%, fill rate 40%, lead time 2.5x
#   Phase 2 — surge:    demand +35%, fill rate 55%, lead time 2.0x
#   Phase 3 — recovery: demand +10%, fill rate 75%, lead time 1.3x
#
# Conflict (periods 19-21, mid-2026):
#   Supply shock only. Demand barely moves (-5 to -10%).
#   Fill rate drops to 45-50%. Lead time 2x. Duration ~3 months.
#
# Port disruption (periods 28-30, mid-2027):
#   Acute, short. Demand unaffected. Lead time spikes 3x. Fill rate 65%.

_SCHEDULE: list[_EventPeriod] = [

    # -----------------------------------------------------------------------
    # PANDEMIC — 6 periods (Jul 2025 -- Dec 2025)
    # -----------------------------------------------------------------------
    _EventPeriod(
        start=7, end=9,
        phase_name="pandemic_shock",
        demand_multiplier=0.55,
        fill_rate_cap=0.40,
        lead_time_multiplier=2.5,
        signal=(
            "Global pandemic declared. Factory closures widespread. "
            "Logistics severely disrupted. Consumer demand has collapsed."
        ),
    ),
    _EventPeriod(
        start=10, end=11,
        phase_name="pandemic_surge",
        demand_multiplier=1.35,
        fill_rate_cap=0.55,
        lead_time_multiplier=2.0,
        signal=(
            "Economies reopening. Consumer demand surging strongly. "
            "Supply chains remain constrained — factories not yet at full capacity."
        ),
    ),
    _EventPeriod(
        start=12, end=12,
        phase_name="pandemic_recovery",
        demand_multiplier=1.10,
        fill_rate_cap=0.75,
        lead_time_multiplier=1.3,
        signal=(
            "Pandemic recovery underway. Demand elevated. "
            "Supply chains gradually normalising — lead times improving."
        ),
    ),

    # -----------------------------------------------------------------------
    # GEOPOLITICAL CONFLICT — 3 periods (Jul 2026 -- Sep 2026)
    # -----------------------------------------------------------------------
    _EventPeriod(
        start=19, end=19,
        phase_name="conflict_onset",
        demand_multiplier=0.95,
        fill_rate_cap=0.45,
        lead_time_multiplier=2.0,
        signal=(
            "Major geopolitical conflict disrupting raw material supply. "
            "Semiconductor and rare earth shortages reported. Logistics rerouting adds weeks."
        ),
    ),
    _EventPeriod(
        start=20, end=21,
        phase_name="conflict_sustained",
        demand_multiplier=0.90,
        fill_rate_cap=0.50,
        lead_time_multiplier=1.8,
        signal=(
            "Geopolitical conflict ongoing. Component supply severely constrained. "
            "Energy costs elevated. Production capacity curtailed across the sector."
        ),
    ),

    # -----------------------------------------------------------------------
    # PORT / LOGISTICS DISRUPTION — 3 periods (Apr 2027 -- Jun 2027)
    # -----------------------------------------------------------------------
    _EventPeriod(
        start=28, end=28,
        phase_name="port_disruption_acute",
        demand_multiplier=1.00,
        fill_rate_cap=0.65,
        lead_time_multiplier=3.0,
        signal=(
            "Major port strike halting shipments. Lead times tripling. "
            "Demand unaffected — supply side only."
        ),
    ),
    _EventPeriod(
        start=29, end=30,
        phase_name="port_disruption_tail",
        demand_multiplier=1.00,
        fill_rate_cap=0.70,
        lead_time_multiplier=2.0,
        signal=(
            "Port dispute partially resolved. Backlog clearing. "
            "Lead times remain elevated — full normalisation expected next month."
        ),
    ),
]


class WorldEvents:
    """
    Returns disruption parameters for any simulation period.

    By default all three event types are enabled. Pass enabled_events to
    run with a subset — useful for ablation studies:
        WorldEvents(enabled_events={"pandemic"})
        WorldEvents(enabled_events=set())   # baseline, no events
    """

    ALL_EVENTS = {"pandemic", "conflict", "port_disruption"}

    def __init__(self, enabled_events: Optional[set[str]] = None):
        if enabled_events is None:
            enabled_events = self.ALL_EVENTS
        self._enabled = enabled_events

        # Filter schedule to only enabled event types
        self._active: list[_EventPeriod] = []
        for ep in _SCHEDULE:
            family = ep.phase_name.split("_")[0]   # "pandemic", "conflict", "port"
            key = "port_disruption" if family == "port" else family
            if key in self._enabled:
                self._active.append(ep)

    def _lookup(self, period: int) -> Optional[_EventPeriod]:
        """Return the active event phase for this period, or None."""
        for ep in self._active:
            if ep.start <= period <= ep.end:
                return ep
        return None

    def demand_multiplier(self, period: int) -> float:
        ep = self._lookup(period)
        return ep.demand_multiplier if ep else 1.0

    def fill_rate_cap(self, period: int) -> float:
        ep = self._lookup(period)
        return ep.fill_rate_cap if ep else 1.0

    def lead_time_multiplier(self, period: int) -> float:
        ep = self._lookup(period)
        return ep.lead_time_multiplier if ep else 1.0

    def event_label(self, period: int) -> Optional[str]:
        ep = self._lookup(period)
        return ep.phase_name if ep else None

    def event_signal(self, period: int) -> Optional[str]:
        """News headline for the unstructured context condition. None in normal periods."""
        ep = self._lookup(period)
        return ep.signal if ep else None

    def is_disrupted(self, period: int) -> bool:
        return self._lookup(period) is not None

    def summary(self) -> None:
        """Print the event schedule — useful for debugging."""
        print(f"WorldEvents — enabled: {self._enabled}")
        print(f"{'Period':>8}  {'Phase':<28}  {'DemMult':>8}  {'FillCap':>8}  {'LTMult':>7}")
        print("-" * 65)
        for ep in self._active:
            for p in range(ep.start, ep.end + 1):
                print(f"{p:>8}  {ep.phase_name:<28}  {ep.demand_multiplier:>8.2f}"
                      f"  {ep.fill_rate_cap:>8.2f}  {ep.lead_time_multiplier:>7.1f}x")


if __name__ == "__main__":
    WorldEvents().summary()

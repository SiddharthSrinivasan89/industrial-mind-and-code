# Monitoring-Signal / Test / Indicator Reference (the "loose manual" for rung 2)

**Purpose:** the machine reference we hand the model in Phase 1, rung 2 (the aided rung —
see `DESIGN.md`). For a question about a machine, the model sees only that machine's
entries, then must still reason out which one fits the fault.

**Why not "sensor":** not all 55 are direct sensors. Some are tests (gas analysis,
frequency response), inspections (visual), derived metrics (efficiency, coast-down), or
condition indicators (leakage, consumption) — which is why the title isn't just "sensor."

**The rule these follow:** each entry describes **only what is observed or measured —
never which fault it points to.** Naming a fault would leak the answer.

**Scope:** covers the 55 signals in the base single-answer set (`all.jsonl`). The
10-option set (OptionsPert) adds distractor signals from other machines (e.g.
`pressure (head)`, `angular position`) — not covered here; extend before using that rung.

**Please review for:** (1) is the description correct, and (2) does any line leak a fault.
Entries I'm least sure of are marked ⚠️. Data typos kept verbatim so each maps 1:1.

---

## The 55 signals

- **air flow** — the rate or volume of air moving through the machine.
- **air leakage** — the presence or rate of air leaking from the system.
- **amps/ volts/ load** — the machine's current, voltage, and electrical loading.
- **axial flux** — the axial magnetic flux of a rotating electrical machine (motor or generator), read to gauge the condition and internal geometry of its windings and rotor.
- **bushing capacitance** — the measured electrical capacitance of a transformer bushing.
- **coast down** — how the machine slows after power is removed (its run-down behaviour).
- **coast down time** — the time the machine takes to come to rest after shutdown.
- **compresor pressure/ pressure ratio** *(typo: compressor)* — compressor outlet pressure and outlet-to-inlet pressure ratio.
- **compressor efficiency** — compressor output compared with its ideal.
- **compressor pressure** — the pressure the compressor produces.
- **compressor temperature** — the temperature of the compressor or its gas.
- **cooling fluid leak** — the presence or rate of cooling fluid leaking.
- **cooling gas** — the machine's cooling gas (e.g. generator hydrogen): pressure, purity, or flow.
- **current** — the electrical current drawn by the machine.
- **cylinder pressure** — the pressure inside an engine cylinder during operation.
- **dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm)** *(typo: dielectric)* — electrical tests of insulation across frequency and charge/discharge behaviour.
- **dissolved gas analysis** — the gases dissolved in a transformer's insulating oil.
- **engine temperature** — the operating temperature of the engine.
- **excitation current** — the current supplying the field (excitation) winding.
- **exhaust pressure** — the pressure of exhaust gases leaving the machine.
- **exhaust temperature** — the temperature of exhaust gases leaving the machine.
- **fluid leakage** — the presence or rate of fluid leaking from the system.
- **frequency response analysis (fra)** — the electrical response of windings across a range of frequencies.
- **fuel flow** — the rate of fuel supplied to the machine.
- **fuel pressure** — the pressure of the fuel supply.
- **fuel pressure/ fuel flow** — the fuel supply's pressure and flow rate.
- **gas generator temperature** — the temperature in the gas-generator section of a gas turbine.
- **leak reactance flux** — the leakage flux and reactance of a transformer's windings, read to gauge their condition and geometry.
- **length measurement** — a physical length, dimension, clearance, or position.
- **noise** — the sound or acoustic level emitted by the machine.
- **oil condition** — the measured physical and chemical properties of the oil.
- **oil consumption** — the rate at which oil is used up.
- **oil debris** — the count or amount of solid particles in the lubricating oil.
- **oil debris/ contamination** — the count of solid particles and contaminants in the oil.
- **oil leakage** — the presence or rate of oil leaking from the system.
- **oil leakage/ consumption** — the rate of oil leaking and being used up.
- **output power** — the useful power the machine delivers.
- **partial discharge** — small, localized electrical discharges measured within insulation.
- **power** — the machine's power (electrical or mechanical, input or output).
- **power factor/tanδ** — the dielectric loss of insulation (power factor / loss tangent).
- **power turbine temperature** — the temperature of the power-turbine section.
- **pressure or vacuum** — pressure above, or vacuum below, atmospheric in the system.
- **pressure/ pressure ratio** — pressure and the ratio of outlet to inlet pressure.
- **radio frequency emissions** — radio-frequency signals emitted by the machine.
- **resistance** — the measured electrical resistance (e.g. of windings or connections).
- **speed** — the rotational speed (RPM) of the machine.
- **steam leakage** — the presence or rate of steam leaking.
- **temparature** *(typo: temperature)* — the operating temperature.
- **temperature** — the operating temperature of the machine or a section of it.
- **torque** — the rotational (twisting) force on the shaft.
- **turbine efficiency** — turbine output compared with its ideal.
- **ultrasound** — high-frequency (ultrasonic) sound emissions from the machine.
- **vibration** — mechanical oscillation or movement of the machine and its parts.
- **visual** — a direct visual or physical inspection of the machine.
- **voltage** — the electrical voltage at the machine.

---

## Still flagged for your review (⚠️)

- **axial flux** (motor/generator) and **leak reactance flux** (transformer) — confirmed with
  the SME: both read the condition and geometry of the windings/rotor.
- **partial discharge, dissolved gas analysis, ultrasound, radio frequency emissions** —
  closely tied to specific faults. Kept to the measurement only; flag if any still gives the
  answer away.

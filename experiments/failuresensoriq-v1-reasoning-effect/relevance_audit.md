# Benchmark relevance audit — for SME review

For each fault: the sensors the dataset marks **relevant** vs **irrelevant** (from its own answers).
In **SME review**, note any you disagree with — e.g. move a sensor, or flag the classification.
Verdict words you can use: `agree / move-to-relevant / move-to-irrelevant / ambiguous / unclear`.

Total faults: 110 across 10 machines.

---

## aero gas turbine

**air inlet blockage**
- Relevant (dataset): air flow, compresor pressure/ pressure ratio, compressor temperature, speed
- Irrelevant (dataset): exhaust temperature, fuel pressure/ fuel flow, gas generator temperature, oil debris, oil leakage/ consumption, power turbine temperature, pressure/ pressure ratio, vibration
- SME review: 

**bearing wear/ damage**
- Relevant (dataset): oil debris, oil leakage/ consumption, vibration
- Irrelevant (dataset): air flow, compresor pressure/ pressure ratio, compressor temperature, exhaust temperature, fuel pressure/ fuel flow, gas generator temperature, power turbine temperature, pressure/ pressure ratio, speed
- SME review: 

**burner blocked**
- Relevant (dataset): fuel pressure/ fuel flow, pressure/ pressure ratio, speed
- Irrelevant (dataset): air flow, compresor pressure/ pressure ratio, compressor temperature, exhaust temperature, gas generator temperature, oil debris, oil leakage/ consumption, power turbine temperature, vibration
- SME review: 

**combustion chamber holed**
- Relevant (dataset): exhaust temperature, fuel pressure/ fuel flow, speed
- Irrelevant (dataset): air flow, compresor pressure/ pressure ratio, compressor temperature, gas generator temperature, oil debris, oil leakage/ consumption, power turbine temperature, pressure/ pressure ratio, vibration
- SME review: 

**compressor damaged**
- Relevant (dataset): compresor pressure/ pressure ratio, compressor temperature, exhaust temperature, fuel pressure/ fuel flow, gas generator temperature, oil debris, power turbine temperature, pressure/ pressure ratio, speed, vibration
- Irrelevant (dataset): air flow, oil leakage/ consumption
- SME review: 

**compressor fouled**
- Relevant (dataset): air flow, compresor pressure/ pressure ratio, compressor temperature, exhaust temperature, fuel pressure/ fuel flow, gas generator temperature, oil debris, power turbine temperature, pressure/ pressure ratio, speed, vibration
- Irrelevant (dataset): oil leakage/ consumption
- SME review: 

**compressor stall**
- Relevant (dataset): pressure/ pressure ratio, speed, vibration
- Irrelevant (dataset): air flow, compresor pressure/ pressure ratio, compressor temperature, exhaust temperature, fuel pressure/ fuel flow, gas generator temperature, oil debris, oil leakage/ consumption, power turbine temperature
- SME review: 

**fuel filter blockage**
- Relevant (dataset): compresor pressure/ pressure ratio, fuel pressure/ fuel flow, pressure/ pressure ratio, speed
- Irrelevant (dataset): air flow, compressor temperature, exhaust temperature, gas generator temperature, oil debris, oil leakage/ consumption, power turbine temperature, vibration
- SME review: 

**gear defects**
- Relevant (dataset): oil debris, vibration
- Irrelevant (dataset): air flow, compresor pressure/ pressure ratio, compressor temperature, exhaust temperature, fuel pressure/ fuel flow, gas generator temperature, oil leakage/ consumption, power turbine temperature, pressure/ pressure ratio, speed
- SME review: 

**misalignment**
- Relevant (dataset): vibration
- Irrelevant (dataset): air flow, compresor pressure/ pressure ratio, compressor temperature, exhaust temperature, fuel pressure/ fuel flow, gas generator temperature, oil debris, oil leakage/ consumption, power turbine temperature, pressure/ pressure ratio, speed
- SME review: 

**power turbine damage**
- Relevant (dataset): air flow, compresor pressure/ pressure ratio, compressor temperature, oil debris, pressure/ pressure ratio, speed, vibration
- Irrelevant (dataset): exhaust temperature, fuel pressure/ fuel flow, gas generator temperature, oil leakage/ consumption, power turbine temperature
- SME review: 

**power turbine dirty**
- Relevant (dataset): air flow, compresor pressure/ pressure ratio, compressor temperature, power turbine temperature, pressure/ pressure ratio, speed, vibration
- Irrelevant (dataset): exhaust temperature, fuel pressure/ fuel flow, gas generator temperature, oil debris, oil leakage/ consumption
- SME review: 

**seal leakage**
- Relevant (dataset): gas generator temperature, oil debris, oil leakage/ consumption, pressure/ pressure ratio
- Irrelevant (dataset): air flow, compresor pressure/ pressure ratio, compressor temperature, exhaust temperature, fuel pressure/ fuel flow, power turbine temperature, speed, vibration
- SME review: 

**unbalance**
- Relevant (dataset): vibration
- Irrelevant (dataset): air flow, compresor pressure/ pressure ratio, compressor temperature, exhaust temperature, fuel pressure/ fuel flow, gas generator temperature, oil debris, oil leakage/ consumption, power turbine temperature, pressure/ pressure ratio, speed
- SME review: 


## compressor

**bearing damage**
- Relevant (dataset): coast down time, length measurement, oil debris, oil leakage, power, speed, temperature, vibration
- Irrelevant (dataset): fluid leakage, pressure or vacuum
- SME review: 

**bearing wear**
- Relevant (dataset): coast down time, length measurement, oil debris, temperature, vibration
- Irrelevant (dataset): fluid leakage, oil leakage, power, pressure or vacuum, speed
- SME review: 

**cooling system fault**
- Relevant (dataset): fluid leakage, oil debris, pressure or vacuum, temperature
- Irrelevant (dataset): coast down time, length measurement, oil leakage, power, speed, vibration
- SME review: 

**damaged impeller**
- Relevant (dataset): coast down time, length measurement, oil debris, power, pressure or vacuum, speed, temperature, vibration
- Irrelevant (dataset): fluid leakage, oil leakage
- SME review: 

**damaged seals**
- Relevant (dataset): fluid leakage, length measurement, oil debris, pressure or vacuum, speed
- Irrelevant (dataset): coast down time, oil leakage, power, temperature, vibration
- SME review: 

**eccentric impeller**
- Relevant (dataset): coast down time, power, pressure or vacuum, speed, temperature, vibration
- Irrelevant (dataset): fluid leakage, length measurement, oil debris, oil leakage
- SME review: 

**misalignment**
- Relevant (dataset): length measurement, vibration
- Irrelevant (dataset): coast down time, fluid leakage, oil debris, oil leakage, power, pressure or vacuum, speed, temperature
- SME review: 

**mounting fault**
- Relevant (dataset): vibration
- Irrelevant (dataset): coast down time, fluid leakage, length measurement, oil debris, oil leakage, power, pressure or vacuum, speed, temperature
- SME review: 

**unbalance**
- Relevant (dataset): vibration
- Irrelevant (dataset): coast down time, fluid leakage, length measurement, oil debris, oil leakage, power, pressure or vacuum, speed, temperature
- SME review: 

**valve fault**
- Relevant (dataset): fluid leakage, pressure or vacuum, temperature, vibration
- Irrelevant (dataset): coast down time, length measurement, oil debris, oil leakage, power, speed
- SME review: 


## electric generator

**bearing damage**
- Relevant (dataset): coast down, oil debris, temparature, torque, vibration
- Irrelevant (dataset): axial flux, cooling gas, current, partial discharge, power, radio frequency emissions, resistance, voltage
- SME review: 

**brush(es) fault**
- Relevant (dataset): current, power, radio frequency emissions, temparature, torque, voltage
- Irrelevant (dataset): axial flux, coast down, cooling gas, oil debris, partial discharge, resistance, vibration
- SME review: 

**eccentric rotor**
- Relevant (dataset): axial flux, current, vibration
- Irrelevant (dataset): coast down, cooling gas, oil debris, partial discharge, power, radio frequency emissions, resistance, temparature, torque, voltage
- SME review: 

**insulation deterioration**
- Relevant (dataset): cooling gas, current, partial discharge, resistance, voltage
- Irrelevant (dataset): axial flux, coast down, oil debris, power, radio frequency emissions, temparature, torque, vibration
- SME review: 

**loss of output power phase**
- Relevant (dataset): current, vibration, voltage
- Irrelevant (dataset): axial flux, coast down, cooling gas, oil debris, partial discharge, power, radio frequency emissions, resistance, temparature, torque
- SME review: 

**misalignment**
- Relevant (dataset): vibration
- Irrelevant (dataset): axial flux, coast down, cooling gas, current, oil debris, partial discharge, power, radio frequency emissions, resistance, temparature, torque, voltage
- SME review: 

**rotor windings fault**
- Relevant (dataset): axial flux, cooling gas, current, temparature, vibration
- Irrelevant (dataset): coast down, oil debris, partial discharge, power, radio frequency emissions, resistance, torque, voltage
- SME review: 

**stator windings fault**
- Relevant (dataset): axial flux, cooling gas, current, temparature, vibration
- Irrelevant (dataset): coast down, oil debris, partial discharge, power, radio frequency emissions, resistance, torque, voltage
- SME review: 

**unbalance**
- Relevant (dataset): vibration
- Irrelevant (dataset): axial flux, coast down, cooling gas, current, oil debris, partial discharge, power, radio frequency emissions, resistance, temparature, torque, voltage
- SME review: 


## electric motor

**bearing damage**
- Relevant (dataset): coast down time, current, oil debris, temperature, torque, vibration
- Irrelevant (dataset): axial flux, cooling gas, partial discharge, power, resistance, speed, voltage
- SME review: 

**brush(es) fault**
- Relevant (dataset): current, power, temperature, torque, voltage
- Irrelevant (dataset): axial flux, coast down time, cooling gas, oil debris, partial discharge, resistance, speed, vibration
- SME review: 

**eccentric rotor fault**
- Relevant (dataset): axial flux, current, vibration
- Irrelevant (dataset): coast down time, cooling gas, oil debris, partial discharge, power, resistance, speed, temperature, torque, voltage
- SME review: 

**insulation deterioration**
- Relevant (dataset): cooling gas, current, partial discharge, resistance, voltage
- Irrelevant (dataset): axial flux, coast down time, oil debris, power, speed, temperature, torque, vibration
- SME review: 

**loss of input power phase**
- Relevant (dataset): axial flux, current, vibration, voltage
- Irrelevant (dataset): coast down time, cooling gas, oil debris, partial discharge, power, resistance, speed, temperature, torque
- SME review: 

**misalignment**
- Relevant (dataset): vibration
- Irrelevant (dataset): axial flux, coast down time, cooling gas, current, oil debris, partial discharge, power, resistance, speed, temperature, torque, voltage
- SME review: 

**rotor windings fault**
- Relevant (dataset): axial flux, cooling gas, current, power, speed, temperature, torque, vibration
- Irrelevant (dataset): coast down time, oil debris, partial discharge, resistance, voltage
- SME review: 

**stator windings fault**
- Relevant (dataset): axial flux, cooling gas, current, temperature, vibration
- Irrelevant (dataset): coast down time, oil debris, partial discharge, power, resistance, speed, torque, voltage
- SME review: 

**unbalance**
- Relevant (dataset): vibration
- Irrelevant (dataset): axial flux, coast down time, cooling gas, current, oil debris, partial discharge, power, resistance, speed, temperature, torque, voltage
- SME review: 


## fan

**bearing damage**
- Relevant (dataset): coast down time, length measurement, oil debris, oil leakage, power, speed, temperature, vibration
- Irrelevant (dataset): air leakage, pressure or vacuum
- SME review: 

**bearing wear**
- Relevant (dataset): coast down time, length measurement, oil debris, temperature, vibration
- Irrelevant (dataset): air leakage, oil leakage, power, pressure or vacuum, speed
- SME review: 

**damaged bellows**
- Relevant (dataset): air leakage
- Irrelevant (dataset): coast down time, length measurement, oil debris, oil leakage, power, pressure or vacuum, speed, temperature, vibration
- SME review: 

**damaged impeller**
- Relevant (dataset): coast down time, length measurement, oil debris, power, pressure or vacuum, speed, temperature, vibration
- Irrelevant (dataset): air leakage, oil leakage
- SME review: 

**damaged oil seals**
- Relevant (dataset): length measurement, oil debris, oil leakage, pressure or vacuum, speed
- Irrelevant (dataset): air leakage, coast down time, power, temperature, vibration
- SME review: 

**eccentric impeller**
- Relevant (dataset): coast down time, power, pressure or vacuum, speed, temperature, vibration
- Irrelevant (dataset): air leakage, length measurement, oil debris, oil leakage
- SME review: 

**misalignment**
- Relevant (dataset): length measurement, vibration
- Irrelevant (dataset): air leakage, coast down time, oil debris, oil leakage, power, pressure or vacuum, speed, temperature
- SME review: 

**mounting fault**
- Relevant (dataset): vibration
- Irrelevant (dataset): air leakage, coast down time, length measurement, oil debris, oil leakage, power, pressure or vacuum, speed, temperature
- SME review: 

**rotor fouled**
- Relevant (dataset): vibration
- Irrelevant (dataset): air leakage, coast down time, length measurement, oil debris, oil leakage, power, pressure or vacuum, speed, temperature
- SME review: 

**unbalance**
- Relevant (dataset): vibration
- Irrelevant (dataset): air leakage, coast down time, length measurement, oil debris, oil leakage, power, pressure or vacuum, speed, temperature
- SME review: 


## industrial gas turbine

**air inlet blockage**
- Relevant (dataset): air flow, compressor pressure, output power, speed
- Irrelevant (dataset): compressor efficiency, compressor temperature, exhaust temperature, fuel pressure/ fuel flow, oil consumption, oil debris/ contamination, turbine efficiency, vibration
- SME review: 

**bearing wear**
- Relevant (dataset): oil consumption, oil debris/ contamination, vibration
- Irrelevant (dataset): air flow, compressor efficiency, compressor pressure, compressor temperature, exhaust temperature, fuel pressure/ fuel flow, output power, speed, turbine efficiency
- SME review: 

**burner blocked**
- Relevant (dataset): exhaust temperature, fuel pressure/ fuel flow, output power, speed
- Irrelevant (dataset): air flow, compressor efficiency, compressor pressure, compressor temperature, oil consumption, oil debris/ contamination, turbine efficiency, vibration
- SME review: 

**combustion chamber holed**
- Relevant (dataset): fuel pressure/ fuel flow, output power, speed
- Irrelevant (dataset): air flow, compressor efficiency, compressor pressure, compressor temperature, exhaust temperature, oil consumption, oil debris/ contamination, turbine efficiency, vibration
- SME review: 

**compressor damaged**
- Relevant (dataset): air flow, compressor efficiency, compressor pressure, compressor temperature, fuel pressure/ fuel flow, oil debris/ contamination, output power, speed, vibration
- Irrelevant (dataset): exhaust temperature, oil consumption, turbine efficiency
- SME review: 

**compressor fouled**
- Relevant (dataset): air flow, compressor efficiency, compressor pressure, compressor temperature, fuel pressure/ fuel flow, output power, speed
- Irrelevant (dataset): exhaust temperature, oil consumption, oil debris/ contamination, turbine efficiency, vibration
- SME review: 

**fuel filter blockage**
- Relevant (dataset): compressor pressure, fuel pressure/ fuel flow, output power, speed
- Irrelevant (dataset): air flow, compressor efficiency, compressor temperature, exhaust temperature, oil consumption, oil debris/ contamination, turbine efficiency, vibration
- SME review: 

**misalignment**
- Relevant (dataset): vibration
- Irrelevant (dataset): air flow, compressor efficiency, compressor pressure, compressor temperature, exhaust temperature, fuel pressure/ fuel flow, oil consumption, oil debris/ contamination, output power, speed, turbine efficiency
- SME review: 

**power turbine damaged**
- Relevant (dataset): exhaust temperature, oil debris/ contamination, output power, speed, turbine efficiency, vibration
- Irrelevant (dataset): air flow, compressor efficiency, compressor pressure, compressor temperature, fuel pressure/ fuel flow, oil consumption
- SME review: 

**unbalance**
- Relevant (dataset): vibration
- Irrelevant (dataset): air flow, compressor efficiency, compressor pressure, compressor temperature, exhaust temperature, fuel pressure/ fuel flow, oil consumption, oil debris/ contamination, output power, speed, turbine efficiency
- SME review: 


## power transformer

**arcing/ electrical discharge**
- Relevant (dataset): dissolved gas analysis, noise, oil condition, partial discharge, power factor/tanδ, ultrasound, visual
- Irrelevant (dataset): amps/ volts/ load, bushing capacitance, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), excitation current, frequency response analysis (fra), leak reactance flux, resistance, temperature, vibration
- SME review: 

**connection/ bushing faults**
- Relevant (dataset): bushing capacitance, dissolved gas analysis, noise, partial discharge, power factor/tanδ, resistance, temperature, ultrasound
- Irrelevant (dataset): amps/ volts/ load, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), excitation current, frequency response analysis (fra), leak reactance flux, oil condition, vibration, visual
- SME review: 

**core looseness**
- Relevant (dataset): noise, ultrasound, vibration
- Irrelevant (dataset): amps/ volts/ load, bushing capacitance, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), dissolved gas analysis, excitation current, frequency response analysis (fra), leak reactance flux, oil condition, partial discharge, power factor/tanδ, resistance, temperature, visual
- SME review: 

**de-energized tap-changer condition/ fault**
- Relevant (dataset): amps/ volts/ load, dissolved gas analysis, excitation current, frequency response analysis (fra), noise, oil condition, partial discharge, resistance, temperature, ultrasound, vibration
- Irrelevant (dataset): bushing capacitance, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), leak reactance flux, power factor/tanδ, visual
- SME review: 

**external damage/ disturbance**
- Relevant (dataset): visual
- Irrelevant (dataset): amps/ volts/ load, bushing capacitance, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), dissolved gas analysis, excitation current, frequency response analysis (fra), leak reactance flux, noise, oil condition, partial discharge, power factor/tanδ, resistance, temperature, ultrasound, vibration
- SME review: 

**insulation deterioration**
- Relevant (dataset): amps/ volts/ load, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), dissolved gas analysis, excitation current, frequency response analysis (fra), oil condition, partial discharge, power factor/tanδ, resistance, temperature, ultrasound
- Irrelevant (dataset): bushing capacitance, leak reactance flux, noise, vibration, visual
- SME review: 

**low oil level**
- Relevant (dataset): dissolved gas analysis, noise, oil condition, temperature, ultrasound, visual
- Irrelevant (dataset): amps/ volts/ load, bushing capacitance, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), excitation current, frequency response analysis (fra), leak reactance flux, partial discharge, power factor/tanδ, resistance, vibration
- SME review: 

**moisture ingress/ content**
- Relevant (dataset): dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), dissolved gas analysis, oil condition, power factor/tanδ, resistance
- Irrelevant (dataset): amps/ volts/ load, bushing capacitance, excitation current, frequency response analysis (fra), leak reactance flux, noise, partial discharge, temperature, ultrasound, vibration, visual
- SME review: 

**oil circulation system problem**
- Relevant (dataset): dissolved gas analysis, oil condition, temperature, visual
- Irrelevant (dataset): amps/ volts/ load, bushing capacitance, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), excitation current, frequency response analysis (fra), leak reactance flux, noise, partial discharge, power factor/tanδ, resistance, ultrasound, vibration
- SME review: 

**oil leak**
- Relevant (dataset): visual
- Irrelevant (dataset): amps/ volts/ load, bushing capacitance, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), dissolved gas analysis, excitation current, frequency response analysis (fra), leak reactance flux, noise, oil condition, partial discharge, power factor/tanδ, resistance, temperature, ultrasound, vibration
- SME review: 

**oil quality deterioration**
- Relevant (dataset): dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), dissolved gas analysis, oil condition, power factor/tanδ
- Irrelevant (dataset): amps/ volts/ load, bushing capacitance, excitation current, frequency response analysis (fra), leak reactance flux, noise, partial discharge, resistance, temperature, ultrasound, vibration, visual
- SME review: 

**on-load tap-changer condition/ fault**
- Relevant (dataset): amps/ volts/ load, dissolved gas analysis, excitation current, frequency response analysis (fra), noise, oil condition, partial discharge, resistance, temperature, ultrasound, vibration
- Irrelevant (dataset): bushing capacitance, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), leak reactance flux, power factor/tanδ, visual
- SME review: 

**overheating/ auxiliary cooling system fault**
- Relevant (dataset): dissolved gas analysis, oil condition, temperature, ultrasound, visual
- Irrelevant (dataset): amps/ volts/ load, bushing capacitance, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), excitation current, frequency response analysis (fra), leak reactance flux, noise, partial discharge, power factor/tanδ, resistance, vibration
- SME review: 

**supply faults, e.g. excessive harmonics and over fluxing**
- Relevant (dataset): amps/ volts/ load
- Irrelevant (dataset): bushing capacitance, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), dissolved gas analysis, excitation current, frequency response analysis (fra), leak reactance flux, noise, oil condition, partial discharge, power factor/tanδ, resistance, temperature, ultrasound, vibration, visual
- SME review: 

**through fault e.g. lightning strike**
- Relevant (dataset): frequency response analysis (fra), power factor/tanδ
- Irrelevant (dataset): amps/ volts/ load, bushing capacitance, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), dissolved gas analysis, excitation current, leak reactance flux, noise, oil condition, partial discharge, resistance, temperature, ultrasound, vibration, visual
- SME review: 

**winding distortion**
- Relevant (dataset): dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), frequency response analysis (fra), leak reactance flux, ultrasound
- Irrelevant (dataset): amps/ volts/ load, bushing capacitance, dissolved gas analysis, excitation current, noise, oil condition, partial discharge, power factor/tanδ, resistance, temperature, vibration, visual
- SME review: 

**winding looseness**
- Relevant (dataset): noise, ultrasound, vibration
- Irrelevant (dataset): amps/ volts/ load, bushing capacitance, dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm), dissolved gas analysis, excitation current, frequency response analysis (fra), leak reactance flux, oil condition, partial discharge, power factor/tanδ, resistance, temperature, visual
- SME review: 


## pump

**bearing damage**
- Relevant (dataset): coast down time, length measurement, oil debris, oil leakage, power, speed, temperature, vibration
- Irrelevant (dataset): fluid leakage, pressure or vacuum
- SME review: 

**bearing wear**
- Relevant (dataset): coast down time, length measurement, oil debris, temperature, vibration
- Irrelevant (dataset): fluid leakage, oil leakage, power, pressure or vacuum, speed
- SME review: 

**damaged impeller**
- Relevant (dataset): coast down time, length measurement, oil debris, power, pressure or vacuum, speed, temperature, vibration
- Irrelevant (dataset): fluid leakage, oil leakage
- SME review: 

**damaged seals**
- Relevant (dataset): fluid leakage, length measurement, pressure or vacuum, speed, vibration
- Irrelevant (dataset): coast down time, oil debris, oil leakage, power, temperature
- SME review: 

**eccentric impeller**
- Relevant (dataset): coast down time, power, pressure or vacuum, speed, temperature, vibration
- Irrelevant (dataset): fluid leakage, length measurement, oil debris, oil leakage
- SME review: 

**misalignment**
- Relevant (dataset): length measurement, vibration
- Irrelevant (dataset): coast down time, fluid leakage, oil debris, oil leakage, power, pressure or vacuum, speed, temperature
- SME review: 

**mounting fault**
- Relevant (dataset): vibration
- Irrelevant (dataset): coast down time, fluid leakage, length measurement, oil debris, oil leakage, power, pressure or vacuum, speed, temperature
- SME review: 

**unbalance**
- Relevant (dataset): vibration
- Irrelevant (dataset): coast down time, fluid leakage, length measurement, oil debris, oil leakage, power, pressure or vacuum, speed, temperature
- SME review: 


## reciprocating internal combustion engine

**air inlet blockage**
- Relevant (dataset): air flow, cylinder pressure, engine temperature, exhaust pressure
- Irrelevant (dataset): cooling fluid leak, exhaust temperature, fuel flow, fuel pressure, oil consumption, oil debris, output power, vibration
- SME review: 

**bearing wear**
- Relevant (dataset): oil debris, vibration
- Irrelevant (dataset): air flow, cooling fluid leak, cylinder pressure, engine temperature, exhaust pressure, exhaust temperature, fuel flow, fuel pressure, oil consumption, output power
- SME review: 

**cooling system fault**
- Relevant (dataset): cooling fluid leak, exhaust pressure, fuel flow, oil consumption, oil debris
- Irrelevant (dataset): air flow, cylinder pressure, engine temperature, exhaust temperature, fuel pressure, output power, vibration
- SME review: 

**flywheel damage**
- Relevant (dataset): oil debris, vibration
- Irrelevant (dataset): air flow, cooling fluid leak, cylinder pressure, engine temperature, exhaust pressure, exhaust temperature, fuel flow, fuel pressure, oil consumption, output power
- SME review: 

**fuel filter blockage**
- Relevant (dataset): exhaust pressure, fuel flow, fuel pressure
- Irrelevant (dataset): air flow, cooling fluid leak, cylinder pressure, engine temperature, exhaust temperature, oil consumption, oil debris, output power, vibration
- SME review: 

**fuel injector fault**
- Relevant (dataset): air flow, cylinder pressure, engine temperature, exhaust temperature, fuel flow, oil consumption, output power, vibration
- Irrelevant (dataset): cooling fluid leak, exhaust pressure, fuel pressure, oil debris
- SME review: 

**gear defects**
- Relevant (dataset): oil debris, vibration
- Irrelevant (dataset): air flow, cooling fluid leak, cylinder pressure, engine temperature, exhaust pressure, exhaust temperature, fuel flow, fuel pressure, oil consumption, output power
- SME review: 

**ignition fault**
- Relevant (dataset): cylinder pressure, engine temperature, exhaust temperature, fuel flow, oil consumption, output power, vibration
- Irrelevant (dataset): air flow, cooling fluid leak, exhaust pressure, fuel pressure, oil debris
- SME review: 

**misalignment**
- Relevant (dataset): vibration
- Irrelevant (dataset): air flow, cooling fluid leak, cylinder pressure, engine temperature, exhaust pressure, exhaust temperature, fuel flow, fuel pressure, oil consumption, oil debris, output power
- SME review: 

**mounting fault**
- Relevant (dataset): vibration
- Irrelevant (dataset): air flow, cooling fluid leak, cylinder pressure, engine temperature, exhaust pressure, exhaust temperature, fuel flow, fuel pressure, oil consumption, oil debris, output power
- SME review: 

**piston ring fault**
- Relevant (dataset): cylinder pressure, oil consumption, oil debris, output power
- Irrelevant (dataset): air flow, cooling fluid leak, engine temperature, exhaust pressure, exhaust temperature, fuel flow, fuel pressure, vibration
- SME review: 

**seal leakage**
- Relevant (dataset): exhaust pressure, exhaust temperature, oil consumption
- Irrelevant (dataset): air flow, cooling fluid leak, cylinder pressure, engine temperature, fuel flow, fuel pressure, oil debris, output power, vibration
- SME review: 

**secondary balance gear fault**
- Relevant (dataset): vibration
- Irrelevant (dataset): air flow, cooling fluid leak, cylinder pressure, engine temperature, exhaust pressure, exhaust temperature, fuel flow, fuel pressure, oil consumption, oil debris, output power
- SME review: 

**unbalance**
- Relevant (dataset): vibration
- Irrelevant (dataset): air flow, cooling fluid leak, cylinder pressure, engine temperature, exhaust pressure, exhaust temperature, fuel flow, fuel pressure, oil consumption, oil debris, output power
- SME review: 


## steam turbine

**bearing damage**
- Relevant (dataset): coast down time, length measurement, oil debris, oil leakage, power, pressure or vacuum, temperature, vibration
- Irrelevant (dataset): speed, steam leakage
- SME review: 

**bearing wear**
- Relevant (dataset): coast down time, length measurement, oil debris, oil leakage, steam leakage, temperature, vibration
- Irrelevant (dataset): power, pressure or vacuum, speed
- SME review: 

**damaged labyrinth**
- Relevant (dataset): coast down time, power, pressure or vacuum, speed, steam leakage, temperature, vibration
- Irrelevant (dataset): length measurement, oil debris, oil leakage
- SME review: 

**damaged rotor blade**
- Relevant (dataset): coast down time, oil debris, power, steam leakage, temperature, vibration
- Irrelevant (dataset): length measurement, oil leakage, pressure or vacuum, speed
- SME review: 

**eccentric rotor**
- Relevant (dataset): coast down time, steam leakage, vibration
- Irrelevant (dataset): length measurement, oil debris, oil leakage, power, pressure or vacuum, speed, temperature
- SME review: 

**hogging or sagging rotor**
- Relevant (dataset): coast down time, oil debris, steam leakage, vibration
- Irrelevant (dataset): length measurement, oil leakage, power, pressure or vacuum, speed, temperature
- SME review: 

**misalignment**
- Relevant (dataset): vibration
- Irrelevant (dataset): coast down time, length measurement, oil debris, oil leakage, power, pressure or vacuum, speed, steam leakage, temperature
- SME review: 

**unbalance**
- Relevant (dataset): vibration
- Irrelevant (dataset): coast down time, length measurement, oil debris, oil leakage, power, pressure or vacuum, speed, steam leakage, temperature
- SME review: 

**unequal expansion**
- Relevant (dataset): length measurement, steam leakage, temperature, vibration
- Irrelevant (dataset): coast down time, oil debris, oil leakage, power, pressure or vacuum, speed
- SME review: 


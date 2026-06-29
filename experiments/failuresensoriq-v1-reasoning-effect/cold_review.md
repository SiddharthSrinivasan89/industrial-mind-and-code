# Cold run — gemma3:4b (rung 1, no help)

Accuracy: **42.0%** (84/200).  Guessing bar ~28%. Expert ~60%.
Each entry: the question, Gemma's pick, the correct answer, and Gemma's full reply.

---

### id 16 — electric motor — ✅ RIGHT
**Q:** For electric motor, if brush(es) fault happens, which sensor should be prioritized for monitoring this specific failure?
**Options:** A) speed · B) current · C) partial discharge · D) coast down time · E) axial flux
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B  ⏎  ⏎ **Explanation:** ⏎  ⏎ When a brush fault occurs in an electric motor, it dramatically increases the circuit resistance. This leads to a significant and immediate change in the motor's current draw. Monitoring current is the *most direct* and reliable way to detect this fault in real-time. ⏎  ⏎ Here's why the other options are less suitable: ⏎  ⏎ *   **A) Speed:** Speed can be affected by brush faults, but the current change is a more immediate and specific indicator. ⏎ *   **C) Partial Discharge:** Partial discharge is related to insulation breakdown and is not directly caused by brush faults. ⏎ *   **D) Coast Down Time:** This is a consequence of the fault, not a direct monitoring sensor. ⏎ *   **E) Axial Flux:** This refers to a motor design and isn't a sensor for detecting brush faults. ⏎  ⏎ **Therefore, monitoring current is the most responsive and accurate sensor for detecting brush faults in an electric motor.**

---

### id 20 — electric motor — ❌ WRONG
**Q:** For electric motor, if brush(es) fault happens, which sensor should be prioritized for monitoring this specific failure?
**Options:** A) resistance · B) partial discharge · C) coast down time · D) vibration · E) temperature
**Correct answer:** E  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 23 — electric motor — ✅ RIGHT
**Q:** When a electric motor has bearing damage, which sensor out of the choices should be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) axial flux · B) vibration · C) voltage · D) cooling gas · E) partial discharge
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 27 — electric motor — ❌ WRONG
**Q:** For electric motor, if insulation deterioration happens, which sensor should be prioritized for monitoring this specific failure?
**Options:** A) coast down time · B) oil debris · C) temperature · D) torque · E) current
**Correct answer:** E  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 36 — electric motor — ✅ RIGHT
**Q:** Which sensor among the choices best correlates with the presence of unbalance in asset electric motor?
**Options:** A) vibration · B) voltage · C) coast down time · D) temperature · E) speed
**Correct answer:** A  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 48 — steam turbine — ✅ RIGHT
**Q:** Which sensor out of the choices provides the strongest indication of damaged labyrinth in steam turbine?
**Options:** A) oil leakage · B) oil debris · C) vibration · D) length measurement
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 52 — steam turbine — ✅ RIGHT
**Q:** Which sensor among the choices best correlates with the presence of eccentric rotor in asset steam turbine?
**Options:** A) pressure or vacuum · B) oil leakage · C) length measurement · D) temperature · E) vibration
**Correct answer:** E  |  **Gemma picked:** E
**Gemma's reply:** E

---

### id 53 — steam turbine — ❌ WRONG
**Q:** When a steam turbine has eccentric rotor, which sensor out of the choices should be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) temperature · B) speed · C) pressure or vacuum · D) oil debris · E) coast down time
**Correct answer:** E  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 63 — steam turbine — ❌ WRONG
**Q:** Which sensor among the choices best correlates with the presence of bearing wear in asset steam turbine?
**Options:** A) speed · B) pressure or vacuum · C) length measurement · D) power
**Correct answer:** C  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 78 — steam turbine — ✅ RIGHT
**Q:** When a steam turbine has misalignment, which sensor out of the choices should be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) oil leakage · B) oil debris · C) steam leakage · D) vibration · E) coast down time
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 99 — aero gas turbine — ✅ RIGHT
**Q:** When a aero gas turbine has compressor damaged, which sensor out of the choices should be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) air flow · B) oil leakage/ consumption · C) pressure/ pressure ratio
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 127 — aero gas turbine — ❌ WRONG
**Q:** For aero gas turbine, if a failure event power turbine dirty occurs, which sensor out of the choices is the most relevant sensor regarding the occurrence of the failure event?
**Options:** A) oil debris · B) oil leakage/ consumption · C) vibration · D) fuel pressure/ fuel flow · E) gas generator temperature
**Correct answer:** C  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 150 — industrial gas turbine — ❌ WRONG
**Q:** Which sensor out of the choices can indicate the presence of compressor fouled in asset industrial gas turbine?
**Options:** A) oil debris/ contamination · B) vibration · C) speed · D) oil consumption · E) turbine efficiency
**Correct answer:** C  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 151 — industrial gas turbine — ❌ WRONG
**Q:** For industrial gas turbine, if compressor fouled happens, which sensor should be prioritized for monitoring this specific failure?
**Options:** A) oil consumption · B) output power · C) exhaust temperature · D) turbine efficiency · E) vibration
**Correct answer:** B  |  **Gemma picked:** E
**Gemma's reply:** E

---

### id 159 — industrial gas turbine — ❌ WRONG
**Q:** Which sensor out of the choices can indicate the presence of compressor damaged in asset industrial gas turbine?
**Options:** A) output power · B) turbine efficiency · C) exhaust temperature · D) oil consumption
**Correct answer:** A  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 162 — industrial gas turbine — ❌ WRONG
**Q:** Which sensor out of the choices provides the strongest indication of fuel filter blockage in industrial gas turbine?
**Options:** A) oil debris/ contamination · B) oil consumption · C) air flow · D) vibration · E) compressor pressure
**Correct answer:** E  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 164 — industrial gas turbine — ❌ WRONG
**Q:** When a industrial gas turbine has fuel filter blockage, which sensor out of the choices should be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) air flow · B) turbine efficiency · C) exhaust temperature · D) speed · E) vibration
**Correct answer:** D  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 175 — industrial gas turbine — ✅ RIGHT
**Q:** When a industrial gas turbine has power turbine damaged, which sensor out of the choices should be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) fuel pressure/ fuel flow · B) compressor temperature · C) vibration · D) oil consumption · E) compressor efficiency
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 180 — industrial gas turbine — ✅ RIGHT
**Q:** When a industrial gas turbine has bearing wear, which sensor out of the choices should be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) speed · B) output power · C) fuel pressure/ fuel flow · D) turbine efficiency · E) oil debris/ contamination
**Correct answer:** E  |  **Gemma picked:** E
**Gemma's reply:** E

---

### id 190 — pump — ❌ WRONG
**Q:** Which sensor out of the choices can indicate the presence of damaged impeller in asset pump?
**Options:** A) fluid leakage · B) oil leakage · C) coast down time
**Correct answer:** C  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 195 — pump — ❌ WRONG
**Q:** In pump, when damaged seals occurs, which sensor from the choices is most critical in detecting the occurrence of the failure event?
**Options:** A) temperature · B) power · C) oil leakage · D) oil debris · E) speed
**Correct answer:** E  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 199 — pump — ✅ RIGHT
**Q:** Which sensor out of the choices can indicate the presence of eccentric impeller in asset pump?
**Options:** A) fluid leakage · B) length measurement · C) oil debris · D) oil leakage · E) speed
**Correct answer:** E  |  **Gemma picked:** E
**Gemma's reply:** E

---

### id 202 — pump — ❌ WRONG
**Q:** Which sensor among the choices best correlates with the presence of eccentric impeller in asset pump?
**Options:** A) coast down time · B) oil debris · C) fluid leakage · D) oil leakage · E) length measurement
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 207 — pump — ❌ WRONG
**Q:** Which sensor out of the choices provides the strongest indication of bearing damage in pump?
**Options:** A) temperature · B) fluid leakage · C) pressure or vacuum
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 209 — pump — ✅ RIGHT
**Q:** Which sensor out of the choices provides the strongest indication of bearing damage in pump?
**Options:** A) oil debris · B) pressure or vacuum · C) fluid leakage
**Correct answer:** A  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 213 — pump — ❌ WRONG
**Q:** When dealing with bearing wear in pump, which sensor among the choices has the highest relevance in detecting this issue?
**Options:** A) temperature · B) fluid leakage · C) oil leakage · D) power · E) speed
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 214 — pump — ❌ WRONG
**Q:** In pump, when bearing wear occurs, which sensor from the choices is most critical in detecting the occurrence of the failure event?
**Options:** A) power · B) oil leakage · C) pressure or vacuum · D) speed · E) coast down time
**Correct answer:** E  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 215 — pump — ✅ RIGHT
**Q:** When dealing with bearing wear in pump, which sensor among the choices has the highest relevance in detecting this issue?
**Options:** A) oil debris · B) power · C) speed · D) fluid leakage · E) pressure or vacuum
**Correct answer:** A  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 238 — compressor — ❌ WRONG
**Q:** Which sensor out of the choices provides the strongest indication of eccentric impeller in compressor?
**Options:** A) oil debris · B) coast down time · C) oil leakage · D) length measurement · E) fluid leakage
**Correct answer:** B  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 245 — compressor — ✅ RIGHT
**Q:** Which sensor out of the choices can indicate the presence of bearing damage in asset compressor?
**Options:** A) pressure or vacuum · B) fluid leakage · C) oil debris
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 257 — compressor — ✅ RIGHT
**Q:** For compressor, if a failure event valve fault occurs, which sensor out of the choices is the most relevant sensor regarding the occurrence of the failure event?
**Options:** A) speed · B) oil debris · C) length measurement · D) pressure or vacuum · E) coast down time
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 278 — reciprocating internal combustion engine — ❌ WRONG
**Q:** When a reciprocating internal combustion engine has fuel injector fault, which sensor out of the choices should be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) fuel pressure · B) cooling fluid leak · C) oil consumption · D) oil debris · E) exhaust pressure
**Correct answer:** C  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 285 — reciprocating internal combustion engine — ❌ WRONG
**Q:** When a reciprocating internal combustion engine has ignition fault, which sensor out of the choices should be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) oil debris · B) air flow · C) cooling fluid leak · D) exhaust pressure · E) oil consumption
**Correct answer:** E  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 298 — reciprocating internal combustion engine — ❌ WRONG
**Q:** When dealing with cooling system fault in reciprocating internal combustion engine, which sensor among the choices has the highest relevance in detecting this issue?
**Options:** A) fuel flow · B) output power · C) engine temperature · D) fuel pressure · E) cylinder pressure
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 302 — reciprocating internal combustion engine — ❌ WRONG
**Q:** Which sensor among the choices best correlates with the presence of cooling system fault in asset reciprocating internal combustion engine?
**Options:** A) exhaust temperature · B) cooling fluid leak · C) fuel pressure · D) cylinder pressure · E) air flow
**Correct answer:** B  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 303 — reciprocating internal combustion engine — ❌ WRONG
**Q:** When dealing with secondary balance gear fault in reciprocating internal combustion engine, which sensor among the choices has the highest relevance in detecting this issue?
**Options:** A) vibration · B) cylinder pressure · C) exhaust temperature · D) fuel pressure · E) cooling fluid leak
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 311 — electric generator — ❌ WRONG
**Q:** In electric generator, when rotor windings fault occurs, which sensor from the choices is most critical in detecting the occurrence of the failure event?
**Options:** A) current · B) partial discharge · C) oil debris · D) radio frequency emissions · E) power
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B  ⏎  ⏎ **Explanation:** ⏎  ⏎ Partial discharge (PD) is the most critical sensor for detecting rotor winding faults in a generator. Here's why: ⏎  ⏎ *   **Partial Discharge:** PD is a localized electrical breakdown of the insulation within the rotor windings. It generates high-frequency electrical signals (radio frequency emissions) that can be detected by specialized sensors. PD is a direct indicator of the fault's presence and severity. ⏎  ⏎ Let's look at why the other options are less critical: ⏎  ⏎ *   **Current:** While a significant change in current can *indicate* a problem, it doesn't specifically pinpoint a rotor winding fault. ⏎ *   **Oil Debris:** Oil debris can be a consequence of a fault, but it's a secondary indicator, not the primary detection method. ⏎ *   **Radio Frequency Emissions:** These are a *result* of PD, not a direct detection method themselves. ⏎ *   **Power:** Changes in power output can be caused by many things, not just rotor faults. ⏎  ⏎ **Therefore, B is the most direct and reliable sensor for detecting rotor winding faults.**

---

### id 314 — electric generator — ❌ WRONG
**Q:** Which sensor among the choices best correlates with the presence of rotor windings fault in asset electric generator?
**Options:** A) oil debris · B) resistance · C) radio frequency emissions · D) voltage · E) axial flux
**Correct answer:** E  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 326 — electric generator — ❌ WRONG
**Q:** When a electric generator has brush(es) fault, which sensor out of the choices should be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) axial flux · B) power · C) oil debris · D) cooling gas · E) resistance
**Correct answer:** B  |  **Gemma picked:** E
**Gemma's reply:** E

---

### id 334 — electric generator — ✅ RIGHT
**Q:** When dealing with bearing damage in electric generator, which sensor among the choices has the highest relevance in detecting this issue?
**Options:** A) power · B) voltage · C) current · D) oil debris · E) cooling gas
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 368 — fan — ✅ RIGHT
**Q:** For fan, if bearing damage happens, which sensor should be prioritized for monitoring this specific failure?
**Options:** A) air leakage · B) pressure or vacuum · C) vibration
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 376 — fan — ❌ WRONG
**Q:** For fan, if bearing wear happens, which sensor should be prioritized for monitoring this specific failure?
**Options:** A) air leakage · B) pressure or vacuum · C) oil leakage · D) coast down time · E) speed
**Correct answer:** D  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 399 — power transformer — ✅ RIGHT
**Q:** For power transformer, if on-load tap-changer condition/ fault happens, which sensor should be prioritized for monitoring this specific failure?
**Options:** A) bushing capacitance · B) amps/ volts/ load · C) dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm) · D) leak reactance flux · E) power factor/tanδ
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** **B** ⏎  ⏎ Here's why: ⏎  ⏎ *   **Amps/Volts/Load:** When a tap changer fails under load, it causes voltage fluctuations and current imbalances. Monitoring amps, volts, and load closely provides the most immediate and direct indication of this abnormal operation. A sudden change in these parameters is a strong indicator of a tap changer issue. ⏎  ⏎ Let's look at why the other options are less prioritized: ⏎  ⏎ *   **A) Bushing Capacitance:** Bushing capacitance is primarily related to insulation integrity and doesn't directly reflect tap changer malfunction. ⏎ *   **C) DFR/PDC/RVM:** These are diagnostic tests for the transformer itself, not the tap changer. While they might eventually show a consequence of the tap changer failure, they aren't the first line of defense. ⏎ *   **D) Leak Reactance Flux:** This measures transformer losses and is related to the transformer's overall health, not specifically the tap changer. ⏎ *   **E) Power Factor/tanδ:** These are indicators of load characteristics and transformer efficiency, not a direct measure of tap changer failure. ⏎  ⏎ **Important Note:** While monitoring amps, volts, and load is the *priority*, it's crucial to remember that a tap changer failure often *also* causes changes in DFR/PDC/RVM readings. Therefore, a comprehensive monitoring strategy would include all of these, but initially, load/voltage/current are the most critical.

---

### id 467 — power transformer — ❌ WRONG
**Q:** Which sensor among the choices best correlates with the presence of through fault e.g. lightning strike in asset power transformer?
**Options:** A) power factor/tanδ · B) temperature · C) partial discharge · D) excitation current · E) noise
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 480 — electric motor — ❌ WRONG
**Q:** When resistance detects abnormal readings in electric motor, which failure mode is the most relevant?
**Options:** A) misalignment · B) loss of input power phase · C) stator windings fault · D) unbalance · E) insulation deterioration
**Correct answer:** E  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 488 — electric motor — ✅ RIGHT
**Q:** Which failure mode is most relevant for electric motor if there are abnormal readings from vibration?
**Options:** A) brush(es) fault · B) insulation deterioration · C) rotor windings fault
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 493 — electric motor — ✅ RIGHT
**Q:** When vibration in electric motor displays abnormal readings, which failure mode is the most applicable?
**Options:** A) brush(es) fault · B) insulation deterioration · C) unbalance
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 510 — steam turbine — ❌ WRONG
**Q:** Which failure mode should be considered for steam turbine when abnormal readings is detected by steam leakage?
**Options:** A) unbalance · B) bearing damage · C) misalignment · D) eccentric rotor
**Correct answer:** D  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 513 — steam turbine — ❌ WRONG
**Q:** Which failure mode should be considered for steam turbine when abnormal readings is detected by steam leakage?
**Options:** A) misalignment · B) unbalance · C) bearing damage · D) unequal expansion
**Correct answer:** D  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 518 — steam turbine — ❌ WRONG
**Q:** When power in steam turbine displays abnormal readings, which failure mode is the most applicable?
**Options:** A) misalignment · B) damaged labyrinth · C) hogging or sagging rotor · D) unbalance · E) bearing wear
**Correct answer:** B  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 519 — steam turbine — ✅ RIGHT
**Q:** Which failure mode should be considered for steam turbine when abnormal readings is detected by power?
**Options:** A) bearing damage · B) unbalance · C) misalignment · D) eccentric rotor · E) bearing wear
**Correct answer:** A  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 533 — steam turbine — ✅ RIGHT
**Q:** If coast down time in steam turbine shows abnormal readings, which failure mode is most significant?
**Options:** A) unbalance · B) unequal expansion · C) hogging or sagging rotor · D) misalignment
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 548 — aero gas turbine — ❌ WRONG
**Q:** When compresor pressure/ pressure ratio detects abnormal readings in aero gas turbine, which failure mode is the most relevant?
**Options:** A) bearing wear/ damage · B) unbalance · C) seal leakage · D) gear defects · E) fuel filter blockage
**Correct answer:** E  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 588 — aero gas turbine — ✅ RIGHT
**Q:** What is the most relevant failure mode for aero gas turbine if vibration exhibits abnormal readings?
**Options:** A) burner blocked · B) seal leakage · C) air inlet blockage · D) fuel filter blockage · E) compressor stall
**Correct answer:** E  |  **Gemma picked:** E
**Gemma's reply:** E

---

### id 608 — industrial gas turbine — ❌ WRONG
**Q:** Which failure mode is most relevant for industrial gas turbine if there are abnormal readings from compressor pressure?
**Options:** A) power turbine damaged · B) burner blocked · C) unbalance · D) fuel filter blockage · E) misalignment
**Correct answer:** D  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 609 — industrial gas turbine — ✅ RIGHT
**Q:** If air flow in industrial gas turbine shows abnormal readings, which failure mode is most significant?
**Options:** A) air inlet blockage · B) fuel filter blockage · C) unbalance · D) misalignment · E) power turbine damaged
**Correct answer:** A  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 627 — industrial gas turbine — ❌ WRONG
**Q:** If vibration in industrial gas turbine shows abnormal readings, which failure mode is most significant?
**Options:** A) air inlet blockage · B) combustion chamber holed · C) burner blocked · D) power turbine damaged · E) compressor fouled
**Correct answer:** D  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 646 — pump — ❌ WRONG
**Q:** When length measurement detects abnormal readings in pump, which failure mode is the most relevant?
**Options:** A) damaged impeller · B) mounting fault · C) eccentric impeller · D) unbalance
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 652 — pump — ✅ RIGHT
**Q:** If power in pump shows abnormal readings, which failure mode is most significant?
**Options:** A) eccentric impeller · B) damaged seals · C) misalignment · D) mounting fault · E) bearing wear
**Correct answer:** A  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 657 — pump — ✅ RIGHT
**Q:** When speed in pump displays abnormal readings, which failure mode is the most applicable?
**Options:** A) misalignment · B) damaged impeller · C) bearing wear · D) unbalance · E) mounting fault
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 665 — pump — ✅ RIGHT
**Q:** For pump, what is the key failure mode when coast down time has abnormal readings?
**Options:** A) mounting fault · B) misalignment · C) damaged seals · D) damaged impeller · E) unbalance
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 678 — compressor — ✅ RIGHT
**Q:** When length measurement in compressor displays abnormal readings, which failure mode is the most applicable?
**Options:** A) unbalance · B) mounting fault · C) bearing damage · D) valve fault · E) cooling system fault
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 705 — compressor — ✅ RIGHT
**Q:** For compressor, which failure mode is pertinent if temperature registers abnormal readings?
**Options:** A) misalignment · B) unbalance · C) mounting fault · D) eccentric impeller · E) damaged seals
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 706 — compressor — ✅ RIGHT
**Q:** When temperature detects abnormal readings in compressor, which failure mode is the most relevant?
**Options:** A) mounting fault · B) misalignment · C) unbalance · D) bearing damage · E) damaged seals
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 710 — compressor — ❌ WRONG
**Q:** Which failure mode should be considered for compressor when abnormal readings is detected by coast down time?
**Options:** A) cooling system fault · B) compressor stall · C) damaged impeller · D) valve fault · E) unbalance
**Correct answer:** C  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 716 — compressor — ❌ WRONG
**Q:** What is the most relevant failure mode for compressor if oil debris exhibits abnormal readings?
**Options:** A) unbalance · B) bearing damage · C) eccentric impeller · D) mounting fault · E) compressor stall
**Correct answer:** B  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 727 — reciprocating internal combustion engine — ✅ RIGHT
**Q:** For reciprocating internal combustion engine, what is the key failure mode when air flow has abnormal readings?
**Options:** A) fuel filter blockage · B) seal leakage · C) piston ring fault · D) secondary balance gear fault · E) air inlet blockage
**Correct answer:** E  |  **Gemma picked:** E
**Gemma's reply:** E

---

### id 735 — reciprocating internal combustion engine — ✅ RIGHT
**Q:** When exhaust temperature in reciprocating internal combustion engine displays abnormal readings, which failure mode is the most applicable?
**Options:** A) gear defects · B) ignition fault · C) misalignment · D) flywheel damage · E) air inlet blockage
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 739 — reciprocating internal combustion engine — ❌ WRONG
**Q:** What is the most relevant failure mode for reciprocating internal combustion engine if exhaust pressure exhibits abnormal readings?
**Options:** A) seal leakage · B) fuel injector fault · C) piston ring fault · D) gear defects · E) ignition fault
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 792 — electric generator — ❌ WRONG
**Q:** For electric generator, what is the key failure mode when axial flux has abnormal readings?
**Options:** A) bearing damage · B) stator windings fault · C) unbalance · D) misalignment · E) loss of output power phase
**Correct answer:** B  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 796 — electric generator — ✅ RIGHT
**Q:** What is the most relevant failure mode for electric generator if cooling gas exhibits abnormal readings?
**Options:** A) brush(es) fault · B) stator windings fault · C) loss of output power phase · D) unbalance · E) bearing damage
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 807 — fan — ❌ WRONG
**Q:** When pressure or vacuum in fan displays abnormal readings, which failure mode is the most applicable?
**Options:** A) mounting fault · B) rotor fouled · C) bearing damage · D) unbalance · E) damaged impeller
**Correct answer:** E  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 812 — fan — ✅ RIGHT
**Q:** For fan, which failure mode is pertinent if speed registers abnormal readings?
**Options:** A) damaged bellows · B) eccentric impeller · C) rotor fouled · D) bearing wear · E) unbalance
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 821 — fan — ✅ RIGHT
**Q:** For fan, which failure mode is pertinent if vibration registers abnormal readings?
**Options:** A) damaged bellows · B) damaged oil seals · C) misalignment
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 833 — fan — ❌ WRONG
**Q:** If oil debris in fan shows abnormal readings, which failure mode is most significant?
**Options:** A) rotor fouled · B) unbalance · C) mounting fault · D) bearing wear · E) misalignment
**Correct answer:** D  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 834 — fan — ✅ RIGHT
**Q:** Which failure mode should be considered for fan when abnormal readings is detected by oil leakage?
**Options:** A) unbalance · B) damaged oil seals · C) eccentric impeller · D) bearing wear · E) misalignment
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 867 — power transformer — ❌ WRONG
**Q:** When dissolved gas analysis detects abnormal readings in power transformer, which failure mode is the most relevant?
**Options:** A) winding looseness · B) supply faults, e.g. excessive harmonics and over fluxing · C) oil leak · D) insulation deterioration · E) core looseness
**Correct answer:** D  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 928 — electric motor — ❌ WRONG
**Q:** Which sensor out of the choices is not effective in indicating the presence of stator windings fault in electric motor?
**Options:** A) temperature · B) current · C) axial flux · D) vibration · E) voltage
**Correct answer:** E  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 930 — electric motor — ❌ WRONG
**Q:** Which sensor out of the choices does not indicate the presence of stator windings fault in asset electric motor?
**Options:** A) cooling gas · B) vibration · C) partial discharge · D) axial flux · E) current
**Correct answer:** C  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 961 — electric motor — ❌ WRONG
**Q:** When considering insulation deterioration in electric motor, which sensor should be disregarded from the choices for monitoring this failure?
**Options:** A) voltage · B) power · C) current · D) resistance · E) partial discharge
**Correct answer:** B  |  **Gemma picked:** E
**Gemma's reply:** E

---

### id 972 — electric motor — ❌ WRONG
**Q:** When considering loss of input power phase in electric motor, which sensor should be disregarded from the choices for monitoring this failure?
**Options:** A) axial flux · B) voltage · C) vibration · D) current · E) torque
**Correct answer:** E  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 977 — electric motor — ✅ RIGHT
**Q:** For electric motor, if a failure event loss of input power phase occurs, which sensor out of the choices is not relevant regarding the occurrence of the failure event?
**Options:** A) axial flux · B) vibration · C) current · D) cooling gas · E) voltage
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 986 — electric motor — ✅ RIGHT
**Q:** For electric motor, if unbalance occurs, which sensor among the choices is least likely to be relevant in identifying this failure?
**Options:** A) coast down time · B) vibration
**Correct answer:** A  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 992 — electric motor — ✅ RIGHT
**Q:** When a electric motor has misalignment, which sensor out of the choices should not be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) resistance · B) vibration
**Correct answer:** A  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 1006 — steam turbine — ❌ WRONG
**Q:** Which sensor from the choices does not contribute significantly to detecting damaged labyrinth in steam turbine?
**Options:** A) length measurement · B) coast down time · C) vibration · D) temperature · E) power
**Correct answer:** A  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1018 — steam turbine — ✅ RIGHT
**Q:** Which sensor out of the choices does not indicate the presence of bearing wear in asset steam turbine?
**Options:** A) vibration · B) temperature · C) power · D) coast down time · E) oil debris
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1020 — steam turbine — ❌ WRONG
**Q:** When considering bearing wear in steam turbine, which sensor should be disregarded from the choices for monitoring this failure?
**Options:** A) steam leakage · B) length measurement · C) oil leakage · D) vibration · E) speed
**Correct answer:** E  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1029 — steam turbine — ❌ WRONG
**Q:** Which sensor out of the choices does not indicate the presence of unequal expansion in asset steam turbine?
**Options:** A) temperature · B) vibration · C) steam leakage · D) length measurement · E) speed
**Correct answer:** E  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1040 — steam turbine — ✅ RIGHT
**Q:** When a steam turbine has unbalance, which sensor out of the choices should not be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) vibration · B) oil debris
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1048 — steam turbine — ❌ WRONG
**Q:** When a steam turbine has misalignment, which sensor out of the choices should not be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) coast down time · B) vibration
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1049 — steam turbine — ✅ RIGHT
**Q:** Which sensor from the choices does not contribute significantly to detecting misalignment in steam turbine?
**Options:** A) vibration · B) oil debris
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1053 — aero gas turbine — ❌ WRONG
**Q:** When considering air inlet blockage in aero gas turbine, which sensor should be disregarded from the choices for monitoring this failure?
**Options:** A) air flow · B) compressor temperature · C) pressure/ pressure ratio · D) speed · E) compresor pressure/ pressure ratio
**Correct answer:** C  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1057 — aero gas turbine — ✅ RIGHT
**Q:** When considering air inlet blockage in aero gas turbine, which sensor should be disregarded from the choices for monitoring this failure?
**Options:** A) compresor pressure/ pressure ratio · B) speed · C) oil debris · D) compressor temperature · E) air flow
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1069 — aero gas turbine — ❌ WRONG
**Q:** Which sensor out of the choices does not indicate the presence of compressor stall in asset aero gas turbine?
**Options:** A) oil debris · B) pressure/ pressure ratio · C) vibration · D) speed
**Correct answer:** A  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1080 — aero gas turbine — ❌ WRONG
**Q:** In aero gas turbine, which sensor among the choices is least useful for detecting seal leakage?
**Options:** A) pressure/ pressure ratio · B) compresor pressure/ pressure ratio · C) oil debris · D) oil leakage/ consumption · E) gas generator temperature
**Correct answer:** B  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1108 — aero gas turbine — ✅ RIGHT
**Q:** Which sensor out of the choices is not effective in indicating the presence of power turbine dirty in aero gas turbine?
**Options:** A) power turbine temperature · B) pressure/ pressure ratio · C) compresor pressure/ pressure ratio · D) oil debris · E) air flow
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1122 — aero gas turbine — ❌ WRONG
**Q:** Which sensor out of the choices is not effective in indicating the presence of bearing wear/ damage in aero gas turbine?
**Options:** A) oil debris · B) power turbine temperature · C) oil leakage/ consumption · D) vibration
**Correct answer:** B  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1132 — aero gas turbine — ✅ RIGHT
**Q:** When a aero gas turbine has gear defects, which sensor out of the choices should not be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) oil debris · B) exhaust temperature · C) vibration
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1140 — aero gas turbine — ❌ WRONG
**Q:** Which sensor out of the choices is not effective in indicating the presence of unbalance in aero gas turbine?
**Options:** A) pressure/ pressure ratio · B) vibration
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1193 — industrial gas turbine — ✅ RIGHT
**Q:** When a industrial gas turbine has burner blocked, which sensor out of the choices should not be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) speed · B) fuel pressure/ fuel flow · C) compressor efficiency · D) output power · E) exhaust temperature
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C ⏎  ⏎ **Reasoning:** ⏎  ⏎ If the burner is blocked, it directly impacts the fuel supply and combustion process. While compressor efficiency *could* be affected indirectly, it's a less immediate and less specific indicator of a blocked burner.  ⏎  ⏎ Here's why the other options are relevant: ⏎  ⏎ *   **A) Speed:** Burner blockage would likely lead to reduced power output and thus, a corresponding decrease in turbine speed. ⏎ *   **B) Fuel pressure/fuel flow:** A blocked burner would cause a significant drop in fuel pressure and flow. ⏎ *   **D) Output power:** A blocked burner would directly reduce the turbine's output power. ⏎ *   **E) Exhaust temperature:**  A blocked burner would lead to incomplete combustion and a rise in exhaust temperature. ⏎  ⏎ **Therefore, compressor efficiency (C) is the least directly related to a blocked burner and would be the least informative for anomaly detection in this scenario.**

---

### id 1228 — industrial gas turbine — ✅ RIGHT
**Q:** Which sensor out of the choices does not indicate the presence of misalignment in asset industrial gas turbine?
**Options:** A) vibration · B) exhaust temperature
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1255 — pump — ❌ WRONG
**Q:** For pump, if a failure event mounting fault occurs, which sensor out of the choices is not relevant regarding the occurrence of the failure event?
**Options:** A) pressure or vacuum · B) vibration
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1265 — pump — ❌ WRONG
**Q:** For pump, if unbalance occurs, which sensor among the choices is least likely to be relevant in identifying this failure?
**Options:** A) speed · B) vibration
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1270 — pump — ✅ RIGHT
**Q:** Which sensor from the choices does not contribute significantly to detecting misalignment in pump?
**Options:** A) length measurement · B) fluid leakage · C) vibration
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1295 — compressor — ❌ WRONG
**Q:** Which sensor out of the choices does not indicate the presence of bearing wear in asset compressor?
**Options:** A) temperature · B) length measurement · C) oil debris · D) oil leakage · E) vibration
**Correct answer:** D  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1297 — compressor — ✅ RIGHT
**Q:** For compressor, if cooling system fault occurs, which sensor among the choices is least likely to be relevant in identifying this failure?
**Options:** A) temperature · B) oil debris · C) pressure or vacuum · D) power · E) fluid leakage
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1304 — compressor — ❌ WRONG
**Q:** When a compressor has valve fault, which sensor out of the choices should not be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) pressure or vacuum · B) vibration · C) temperature · D) fluid leakage · E) speed
**Correct answer:** E  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1306 — compressor — ✅ RIGHT
**Q:** For compressor, if a failure event valve fault occurs, which sensor out of the choices is not relevant regarding the occurrence of the failure event?
**Options:** A) pressure or vacuum · B) oil debris · C) vibration · D) fluid leakage · E) temperature
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1317 — compressor — ❌ WRONG
**Q:** Which sensor out of the choices does not indicate the presence of compressor stall in asset compressor?
**Options:** A) fluid leakage · B) speed · C) vibration · D) length measurement
**Correct answer:** A  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1325 — compressor — ✅ RIGHT
**Q:** Which sensor out of the choices does not indicate the presence of unbalance in asset compressor?
**Options:** A) vibration · B) length measurement
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1327 — compressor — ✅ RIGHT
**Q:** Which sensor from the choices does not contribute significantly to detecting unbalance in compressor?
**Options:** A) vibration · B) pressure or vacuum
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1340 — compressor — ✅ RIGHT
**Q:** For compressor, if a failure event misalignment occurs, which sensor out of the choices is not relevant regarding the occurrence of the failure event?
**Options:** A) vibration · B) length measurement · C) oil leakage
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1347 — reciprocating internal combustion engine — ❌ WRONG
**Q:** For reciprocating internal combustion engine, if air inlet blockage occurs, which sensor among the choices is least likely to be relevant in identifying this failure?
**Options:** A) oil debris · B) cylinder pressure · C) engine temperature · D) air flow · E) exhaust pressure
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1352 — reciprocating internal combustion engine — ❌ WRONG
**Q:** Which sensor out of the choices is not effective in indicating the presence of fuel injector fault in reciprocating internal combustion engine?
**Options:** A) vibration · B) oil consumption · C) air flow · D) cooling fluid leak · E) fuel flow
**Correct answer:** D  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1360 — reciprocating internal combustion engine — ✅ RIGHT
**Q:** In reciprocating internal combustion engine, which sensor among the choices is least useful for detecting bearing wear?
**Options:** A) vibration · B) oil debris · C) air flow
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1366 — reciprocating internal combustion engine — ✅ RIGHT
**Q:** When a reciprocating internal combustion engine has bearing wear, which sensor out of the choices should not be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) oil debris · B) oil consumption · C) vibration
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1386 — reciprocating internal combustion engine — ✅ RIGHT
**Q:** Which sensor out of the choices is not effective in indicating the presence of piston ring fault in reciprocating internal combustion engine?
**Options:** A) output power · B) oil consumption · C) cylinder pressure · D) engine temperature · E) oil debris
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1442 — reciprocating internal combustion engine — ✅ RIGHT
**Q:** When a reciprocating internal combustion engine has mounting fault, which sensor out of the choices should not be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) cooling fluid leak · B) vibration
**Correct answer:** A  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 1482 — electric generator — ✅ RIGHT
**Q:** In electric generator, which sensor among the choices is least useful for detecting eccentric rotor?
**Options:** A) current · B) vibration · C) axial flux · D) resistance
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1499 — electric generator — ✅ RIGHT
**Q:** In electric generator, which sensor among the choices is least useful for detecting bearing damage?
**Options:** A) vibration · B) coast down · C) voltage · D) torque · E) oil debris
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1523 — electric generator — ✅ RIGHT
**Q:** When a electric generator has loss of output power phase, which sensor out of the choices should not be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) current · B) cooling gas · C) voltage · D) vibration
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B ⏎  ⏎ **Reasoning:** ⏎  ⏎ Loss of output power phase in a generator is fundamentally an electrical problem. While cooling gas might be affected, it's a *consequence* of the electrical failure, not the root cause.  ⏎  ⏎ Here's why the other options are relevant: ⏎  ⏎ *   **A) Current:** Current is a primary indicator of generator output. A sudden drop or instability is a key symptom of a phase loss. ⏎ *   **C) Voltage:** Voltage is directly related to current and output power. A phase loss will cause voltage imbalances. ⏎ *   **D) Vibration:** Abnormal vibration can be a result of imbalances caused by a phase loss, indicating mechanical stress. ⏎  ⏎ **Cooling gas** is a secondary indicator and wouldn't be the most informative sensor for detecting the initial phase loss itself.  An anomaly detection model focused on the core electrical behavior would prioritize current and voltage.

---

### id 1537 — electric generator — ✅ RIGHT
**Q:** When considering misalignment in electric generator, which sensor should be disregarded from the choices for monitoring this failure?
**Options:** A) vibration · B) voltage
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1549 — fan — ❌ WRONG
**Q:** Which sensor out of the choices does not indicate the presence of damaged impeller in asset fan?
**Options:** A) oil leakage · B) speed · C) power · D) vibration · E) pressure or vacuum
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1553 — fan — ❌ WRONG
**Q:** In fan, which sensor among the choices is least useful for detecting damaged oil seals?
**Options:** A) temperature · B) pressure or vacuum · C) length measurement · D) oil leakage · E) speed
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1557 — fan — ❌ WRONG
**Q:** Which sensor out of the choices does not indicate the presence of damaged bellows in asset fan?
**Options:** A) pressure or vacuum · B) air leakage
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1570 — fan — ❌ WRONG
**Q:** Which sensor out of the choices does not indicate the presence of bearing wear in asset fan?
**Options:** A) oil debris · B) air leakage · C) coast down time · D) temperature · E) length measurement
**Correct answer:** B  |  **Gemma picked:** E
**Gemma's reply:** E

---

### id 1585 — fan — ❌ WRONG
**Q:** When a fan has rotor fouled, which sensor out of the choices should not be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) length measurement · B) vibration
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1630 — power transformer — ✅ RIGHT
**Q:** For power transformer, if a failure event on-load tap-changer condition/ fault occurs, which sensor out of the choices is not relevant regarding the occurrence of the failure event?
**Options:** A) temperature · B) excitation current · C) amps/ volts/ load · D) partial discharge · E) bushing capacitance
**Correct answer:** E  |  **Gemma picked:** E
**Gemma's reply:** E

---

### id 1656 — power transformer — ❌ WRONG
**Q:** For power transformer, if arcing/ electrical discharge occurs, which sensor among the choices is least likely to be relevant in identifying this failure?
**Options:** A) power factor/tanδ · B) bushing capacitance · C) oil condition · D) dissolved gas analysis · E) noise
**Correct answer:** B  |  **Gemma picked:** E
**Gemma's reply:** E

---

### id 1677 — power transformer — ❌ WRONG
**Q:** In power transformer, which sensor among the choices is least useful for detecting low oil level?
**Options:** A) oil condition · B) dissolved gas analysis · C) visual · D) noise · E) partial discharge
**Correct answer:** E  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1684 — power transformer — ❌ WRONG
**Q:** Which sensor out of the choices is not effective in indicating the presence of low oil level in power transformer?
**Options:** A) visual · B) oil condition · C) leak reactance flux · D) noise · E) ultrasound
**Correct answer:** C  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 1713 — power transformer — ✅ RIGHT
**Q:** Which sensor out of the choices is not effective in indicating the presence of winding looseness in power transformer?
**Options:** A) vibration · B) noise · C) temperature · D) ultrasound
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1717 — power transformer — ❌ WRONG
**Q:** Which sensor out of the choices is not effective in indicating the presence of winding looseness in power transformer?
**Options:** A) noise · B) resistance · C) ultrasound · D) vibration
**Correct answer:** B  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1718 — power transformer — ❌ WRONG
**Q:** For power transformer, if winding looseness occurs, which sensor among the choices is least likely to be relevant in identifying this failure?
**Options:** A) dielecric frequency response (dfr)/ polarization and de-polarization current (pdc)/ recovery voltage method (rvm) · B) ultrasound · C) vibration · D) noise
**Correct answer:** A  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1768 — power transformer — ✅ RIGHT
**Q:** Which sensor out of the choices does not indicate the presence of through fault e.g. lightning strike in asset power transformer?
**Options:** A) frequency response analysis (fra) · B) power factor/tanδ · C) oil condition
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1779 — power transformer — ❌ WRONG
**Q:** When a power transformer has through fault e.g. lightning strike, which sensor out of the choices should not be the sensor to be monitored for this failure if I want to build an anomaly detection model?
**Options:** A) frequency response analysis (fra) · B) bushing capacitance · C) power factor/tanδ
**Correct answer:** B  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1820 — electric motor — ✅ RIGHT
**Q:** If the sensor power in electric motor shows an abnormal reading, which failure event is insignificant?
**Options:** A) brush(es) fault · B) eccentric rotor fault · C) rotor windings fault
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1826 — electric motor — ❌ WRONG
**Q:** For electric motor, which failure event is not pertinent if the sensor torque registers an abnormal reading?
**Options:** A) brush(es) fault · B) rotor windings fault · C) stator windings fault · D) bearing damage
**Correct answer:** C  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1845 — electric motor — ❌ WRONG
**Q:** What is the irrelevant failure event for electric motor if the sensor temperature exhibits an abnormal reading?
**Options:** A) unbalance · B) rotor windings fault · C) brush(es) fault · D) bearing damage · E) stator windings fault
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1862 — electric motor — ❌ WRONG
**Q:** Which failure event should be excluded for electric motor when an abnormal reading is detected by the sensor oil debris?
**Options:** A) bearing damage · B) eccentric rotor fault
**Correct answer:** B  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 1864 — electric motor — ✅ RIGHT
**Q:** In the context of electric motor, which failure event is not relevant when the sensor oil debris shows an abnormal reading?
**Options:** A) bearing damage · B) insulation deterioration
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1880 — steam turbine — ❌ WRONG
**Q:** In steam turbine, which failure event is unimportant if the sensor length measurement shows an abnormal reading?
**Options:** A) bearing damage · B) bearing wear · C) hogging or sagging rotor · D) unequal expansion
**Correct answer:** C  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1897 — steam turbine — ❌ WRONG
**Q:** What is the irrelevant failure event for steam turbine if the sensor speed exhibits an abnormal reading?
**Options:** A) eccentric rotor · B) damaged labyrinth
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1904 — steam turbine — ❌ WRONG
**Q:** When the sensor temperature in steam turbine displays an abnormal reading, which failure event is not applicable?
**Options:** A) eccentric rotor · B) damaged rotor blade · C) bearing wear · D) damaged labyrinth · E) bearing damage
**Correct answer:** A  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1936 — aero gas turbine — ❌ WRONG
**Q:** Which failure event should be excluded for aero gas turbine when an abnormal reading is detected by the sensor compresor pressure/ pressure ratio?
**Options:** A) compressor fouled · B) air inlet blockage · C) fuel filter blockage · D) bearing wear/ damage · E) power turbine dirty
**Correct answer:** D  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1940 — aero gas turbine — ❌ WRONG
**Q:** When the sensor air flow in aero gas turbine displays an abnormal reading, which failure event is not applicable?
**Options:** A) compressor damaged · B) power turbine damage · C) power turbine dirty · D) compressor fouled · E) air inlet blockage
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 1950 — aero gas turbine — ❌ WRONG
**Q:** When an abnormal reading is detected by the sensor fuel pressure/ fuel flow in aero gas turbine, which failure event is not relevant?
**Options:** A) fuel filter blockage · B) compressor fouled · C) air inlet blockage · D) combustion chamber holed · E) burner blocked
**Correct answer:** C  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 1953 — aero gas turbine — ❌ WRONG
**Q:** If the sensor fuel pressure/ fuel flow in aero gas turbine shows an abnormal reading, which failure event is insignificant?
**Options:** A) fuel filter blockage · B) combustion chamber holed · C) compressor damaged · D) power turbine dirty · E) burner blocked
**Correct answer:** D  |  **Gemma picked:** E
**Gemma's reply:** E

---

### id 1964 — aero gas turbine — ❌ WRONG
**Q:** When the sensor gas generator temperature in aero gas turbine displays an abnormal reading, which failure event is not applicable?
**Options:** A) compressor damaged · B) air inlet blockage · C) compressor fouled · D) seal leakage
**Correct answer:** B  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 1990 — aero gas turbine — ✅ RIGHT
**Q:** For aero gas turbine, what is the non-relevant failure event when the sensor power turbine temperature has an abnormal reading?
**Options:** A) power turbine dirty · B) unbalance · C) compressor damaged · D) compressor fouled
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2000 — aero gas turbine — ❌ WRONG
**Q:** For aero gas turbine, what is the non-relevant failure event when the sensor exhaust temperature has an abnormal reading?
**Options:** A) compressor fouled · B) combustion chamber holed · C) compressor damaged · D) gear defects
**Correct answer:** D  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2008 — aero gas turbine — ❌ WRONG
**Q:** If the sensor oil debris in aero gas turbine shows an abnormal reading, which failure event is insignificant?
**Options:** A) compressor damaged · B) seal leakage · C) compressor fouled · D) air inlet blockage · E) gear defects
**Correct answer:** D  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2034 — industrial gas turbine — ❌ WRONG
**Q:** Which failure event is irrelevant for industrial gas turbine if there is an abnormal reading from the sensor compressor temperature?
**Options:** A) compressor fouled · B) compressor damaged · C) unbalance
**Correct answer:** C  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2039 — industrial gas turbine — ❌ WRONG
**Q:** When an abnormal reading is detected by the sensor compressor pressure in industrial gas turbine, which failure event is not relevant?
**Options:** A) bearing wear · B) compressor damaged · C) air inlet blockage · D) fuel filter blockage · E) compressor fouled
**Correct answer:** A  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 2059 — industrial gas turbine — ❌ WRONG
**Q:** If the sensor exhaust temperature in industrial gas turbine shows an abnormal reading, which failure event is insignificant?
**Options:** A) power turbine damaged · B) burner blocked · C) compressor damaged
**Correct answer:** C  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2076 — industrial gas turbine — ❌ WRONG
**Q:** If the sensor compressor efficiency in industrial gas turbine shows an abnormal reading, which failure event is insignificant?
**Options:** A) burner blocked · B) compressor fouled · C) compressor damaged
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2081 — industrial gas turbine — ✅ RIGHT
**Q:** What is the irrelevant failure event for industrial gas turbine if the sensor turbine efficiency exhibits an abnormal reading?
**Options:** A) power turbine damaged · B) air inlet blockage
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2090 — industrial gas turbine — ✅ RIGHT
**Q:** For industrial gas turbine, which failure event is not pertinent if the sensor oil debris/ contamination registers an abnormal reading?
**Options:** A) bearing wear · B) air inlet blockage · C) compressor damaged · D) power turbine damaged
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2095 — industrial gas turbine — ❌ WRONG
**Q:** For industrial gas turbine, which failure event is not pertinent if the sensor oil debris/ contamination registers an abnormal reading?
**Options:** A) compressor damaged · B) unbalance · C) power turbine damaged · D) bearing wear
**Correct answer:** B  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 2102 — industrial gas turbine — ✅ RIGHT
**Q:** In industrial gas turbine, which failure event is unimportant if the sensor oil consumption shows an abnormal reading?
**Options:** A) bearing wear · B) burner blocked
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2107 — pump — ✅ RIGHT
**Q:** When an abnormal reading is detected by the sensor fluid leakage in pump, which failure event is not relevant?
**Options:** A) damaged seals · B) eccentric impeller
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2134 — pump — ✅ RIGHT
**Q:** For pump, what is the non-relevant failure event when the sensor coast down time has an abnormal reading?
**Options:** A) damaged impeller · B) damaged seals · C) eccentric impeller · D) bearing damage · E) bearing wear
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B ⏎  ⏎ **Explanation:** ⏎  ⏎ The "sensor coast down time" refers to the time it takes for a pump sensor to return to its baseline reading after a change in flow. An abnormal coast down time *primarily* indicates issues with the seals (specifically, leakage allowing air to enter the system and affecting the sensor's response). ⏎  ⏎ Let's break down why the other options are less relevant: ⏎  ⏎ *   **A) damaged impeller:** A damaged impeller would directly affect pump performance and flow, but wouldn't necessarily cause an abnormal sensor coast down time. ⏎ *   **C) eccentric impeller:** An eccentric impeller would cause vibration and uneven flow, but the sensor coast down time would be related to the leakage affecting the sensor. ⏎ *   **D) bearing damage/E) bearing wear:** Bearing issues primarily cause noise, vibration, and reduced efficiency, not an abnormal sensor coast down time. ⏎  ⏎ Therefore, **B) damaged seals** is the most directly related failure event when the sensor coast down time has an abnormal reading.

---

### id 2144 — pump — ✅ RIGHT
**Q:** When an abnormal reading is detected by the sensor oil leakage in pump, which failure event is not relevant?
**Options:** A) bearing damage · B) damaged seals
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2145 — pump — ❌ WRONG
**Q:** For pump, what is the non-relevant failure event when the sensor oil leakage has an abnormal reading?
**Options:** A) eccentric impeller · B) bearing damage
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2156 — compressor — ✅ RIGHT
**Q:** If the sensor fluid leakage in compressor shows an abnormal reading, which failure event is insignificant?
**Options:** A) cooling system fault · B) valve fault · C) unbalance · D) damaged seals
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 2168 — compressor — ❌ WRONG
**Q:** Which failure event is irrelevant for compressor if there is an abnormal reading from the sensor power?
**Options:** A) compressor stall · B) bearing damage · C) damaged impeller · D) eccentric impeller
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2179 — compressor — ❌ WRONG
**Q:** In compressor, which failure event is unimportant if the sensor speed shows an abnormal reading?
**Options:** A) damaged impeller · B) eccentric impeller · C) bearing damage · D) compressor stall · E) valve fault
**Correct answer:** E  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2210 — compressor — ✅ RIGHT
**Q:** When the sensor oil leakage in compressor displays an abnormal reading, which failure event is not applicable?
**Options:** A) bearing damage · B) compressor stall
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2218 — reciprocating internal combustion engine — ✅ RIGHT
**Q:** When an abnormal reading is detected by the sensor engine temperature in reciprocating internal combustion engine, which failure event is not relevant?
**Options:** A) air inlet blockage · B) secondary balance gear fault · C) fuel injector fault · D) ignition fault
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2246 — reciprocating internal combustion engine — ❌ WRONG
**Q:** When an abnormal reading is detected by the sensor fuel pressure in reciprocating internal combustion engine, which failure event is not relevant?
**Options:** A) air inlet blockage · B) fuel filter blockage
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2279 — reciprocating internal combustion engine — ❌ WRONG
**Q:** What is the irrelevant failure event for reciprocating internal combustion engine if the sensor exhaust temperature exhibits an abnormal reading?
**Options:** A) seal leakage · B) misalignment · C) ignition fault · D) fuel injector fault
**Correct answer:** B  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 2311 — reciprocating internal combustion engine — ❌ WRONG
**Q:** Which failure event should be excluded for reciprocating internal combustion engine when an abnormal reading is detected by the sensor oil consumption?
**Options:** A) piston ring fault · B) fuel injector fault · C) flywheel damage · D) cooling system fault · E) seal leakage
**Correct answer:** C  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 2318 — reciprocating internal combustion engine — ✅ RIGHT
**Q:** For reciprocating internal combustion engine, what is the non-relevant failure event when the sensor oil debris has an abnormal reading?
**Options:** A) bearing wear · B) fuel filter blockage · C) flywheel damage · D) piston ring fault · E) cooling system fault
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2332 — reciprocating internal combustion engine — ✅ RIGHT
**Q:** When an abnormal reading is detected by the sensor cooling fluid leak in reciprocating internal combustion engine, which failure event is not relevant?
**Options:** A) gear defects · B) cooling system fault
**Correct answer:** A  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 2342 — electric generator — ❌ WRONG
**Q:** Which failure event should be excluded for electric generator when an abnormal reading is detected by the sensor voltage?
**Options:** A) eccentric rotor · B) loss of output power phase · C) brush(es) fault · D) insulation deterioration
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 2346 — electric generator — ✅ RIGHT
**Q:** When an abnormal reading is detected by the sensor resistance in electric generator, which failure event is not relevant?
**Options:** A) insulation deterioration · B) rotor windings fault
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2357 — electric generator — ❌ WRONG
**Q:** What is the irrelevant failure event for electric generator if the sensor partial discharge exhibits an abnormal reading?
**Options:** A) brush(es) fault · B) insulation deterioration
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2367 — electric generator — ❌ WRONG
**Q:** For electric generator, what is the non-relevant failure event when the sensor power has an abnormal reading?
**Options:** A) loss of output power phase · B) brush(es) fault
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2370 — electric generator — ❌ WRONG
**Q:** In electric generator, which failure event is unimportant if the sensor torque shows an abnormal reading?
**Options:** A) rotor windings fault · B) brush(es) fault · C) bearing damage
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2386 — electric generator — ✅ RIGHT
**Q:** For electric generator, which failure event is not pertinent if the sensor vibration registers an abnormal reading?
**Options:** A) misalignment · B) bearing damage · C) insulation deterioration · D) loss of output power phase · E) eccentric rotor
**Correct answer:** C  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 2392 — electric generator — ❌ WRONG
**Q:** When the sensor coast down in electric generator displays an abnormal reading, which failure event is not applicable?
**Options:** A) rotor windings fault · B) bearing damage
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2397 — electric generator — ❌ WRONG
**Q:** When an abnormal reading is detected by the sensor coast down in electric generator, which failure event is not relevant?
**Options:** A) loss of output power phase · B) bearing damage
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2401 — electric generator — ❌ WRONG
**Q:** When an abnormal reading is detected by the sensor axial flux in electric generator, which failure event is not relevant?
**Options:** A) eccentric rotor · B) rotor windings fault · C) bearing damage · D) stator windings fault
**Correct answer:** C  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 2408 — electric generator — ❌ WRONG
**Q:** Which failure event is irrelevant for electric generator if there is an abnormal reading from the sensor oil debris?
**Options:** A) eccentric rotor · B) bearing damage
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2420 — fan — ✅ RIGHT
**Q:** In fan, which failure event is unimportant if the sensor air leakage shows an abnormal reading?
**Options:** A) damaged bellows · B) damaged impeller
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2422 — fan — ✅ RIGHT
**Q:** Which failure event is irrelevant for fan if there is an abnormal reading from the sensor air leakage?
**Options:** A) damaged bellows · B) eccentric impeller
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2423 — fan — ❌ WRONG
**Q:** Which failure event should be excluded for fan when an abnormal reading is detected by the sensor air leakage?
**Options:** A) damaged bellows · B) bearing damage
**Correct answer:** B  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 2429 — fan — ❌ WRONG
**Q:** When the sensor length measurement in fan displays an abnormal reading, which failure event is not applicable?
**Options:** A) damaged bellows · B) damaged oil seals · C) damaged impeller · D) bearing damage · E) misalignment
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 2432 — fan — ✅ RIGHT
**Q:** Which failure event is irrelevant for fan if there is an abnormal reading from the sensor length measurement?
**Options:** A) damaged oil seals · B) bearing wear · C) bearing damage · D) rotor fouled · E) misalignment
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 2434 — fan — ❌ WRONG
**Q:** If the sensor power in fan shows an abnormal reading, which failure event is insignificant?
**Options:** A) eccentric impeller · B) bearing damage · C) damaged oil seals · D) damaged impeller
**Correct answer:** C  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2436 — fan — ❌ WRONG
**Q:** When the sensor power in fan displays an abnormal reading, which failure event is not applicable?
**Options:** A) damaged impeller · B) eccentric impeller · C) bearing damage · D) bearing wear
**Correct answer:** D  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 2462 — fan — ❌ WRONG
**Q:** If the sensor coast down time in fan shows an abnormal reading, which failure event is insignificant?
**Options:** A) bearing damage · B) eccentric impeller · C) damaged oil seals · D) damaged impeller · E) bearing wear
**Correct answer:** C  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2488 — power transformer — ❌ WRONG
**Q:** Which failure event is irrelevant for power transformer if there is an abnormal reading from the sensor amps/ volts/ load?
**Options:** A) oil circulation system problem · B) de-energized tap-changer condition/ fault · C) insulation deterioration · D) on-load tap-changer condition/ fault · E) supply faults, e.g. excessive harmonics and over fluxing
**Correct answer:** A  |  **Gemma picked:** C
**Gemma's reply:** C

---

### id 2523 — power transformer — ❌ WRONG
**Q:** Which failure event should be excluded for power transformer when an abnormal reading is detected by the sensor temperature?
**Options:** A) supply faults, e.g. excessive harmonics and over fluxing · B) on-load tap-changer condition/ fault · C) low oil level · D) insulation deterioration · E) connection/ bushing faults
**Correct answer:** A  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 2552 — power transformer — ❌ WRONG
**Q:** When the sensor noise in power transformer displays an abnormal reading, which failure event is not applicable?
**Options:** A) supply faults, e.g. excessive harmonics and over fluxing · B) de-energized tap-changer condition/ fault · C) arcing/ electrical discharge · D) low oil level · E) winding looseness
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2584 — power transformer — ✅ RIGHT
**Q:** When an abnormal reading is detected by the sensor resistance in power transformer, which failure event is not relevant?
**Options:** A) on-load tap-changer condition/ fault · B) connection/ bushing faults · C) de-energized tap-changer condition/ fault · D) oil quality deterioration · E) insulation deterioration
**Correct answer:** D  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 2621 — power transformer — ❌ WRONG
**Q:** When the sensor excitation current in power transformer displays an abnormal reading, which failure event is not applicable?
**Options:** A) moisture ingress/ content · B) on-load tap-changer condition/ fault · C) de-energized tap-changer condition/ fault · D) insulation deterioration
**Correct answer:** A  |  **Gemma picked:** D
**Gemma's reply:** D

---

### id 2627 — power transformer — ✅ RIGHT
**Q:** For power transformer, what is the non-relevant failure event when the sensor excitation current has an abnormal reading?
**Options:** A) de-energized tap-changer condition/ fault · B) oil circulation system problem · C) on-load tap-changer condition/ fault · D) insulation deterioration
**Correct answer:** B  |  **Gemma picked:** B
**Gemma's reply:** B

---

### id 2657 — power transformer — ❌ WRONG
**Q:** What is the irrelevant failure event for power transformer if the sensor bushing capacitance exhibits an abnormal reading?
**Options:** A) connection/ bushing faults · B) overheating/ auxiliary cooling system fault
**Correct answer:** B  |  **Gemma picked:** A
**Gemma's reply:** A

---

### id 2660 — power transformer — ❌ WRONG
**Q:** In power transformer, which failure event is unimportant if the sensor bushing capacitance shows an abnormal reading?
**Options:** A) winding distortion · B) connection/ bushing faults
**Correct answer:** A  |  **Gemma picked:** B
**Gemma's reply:** B

---

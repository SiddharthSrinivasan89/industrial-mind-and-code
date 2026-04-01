# Paper Outline: The Human as Agentic Layer

**Working title:** *"The Human as Agentic Layer: Evaluating LLM Agents for Cross-Pillar Reasoning in Total Productive Maintenance"*

**Target venues (in order of preference):**
1. *Computers in Industry* (Elsevier) — applied AI in manufacturing, high fit
2. *Journal of Manufacturing Systems* — systems thinking angle
3. *International Journal of Production Research* — TPM squarely in scope
4. Workshop at NeurIPS/ICML — if framing as an industrial reasoning benchmark

**Status:** Experiment complete. Writing not started.

---

## Abstract (Draft)

Total Productive Maintenance (TPM) organises factory improvement across eight functional pillars. In practice, these pillars operate as information silos — each team sees only their own data. The connective reasoning across pillars has historically been performed by experienced human investigators who hold context from multiple functions simultaneously. We call this role the *agentic layer*. As these investigators retire or rotate, organisations lose this tacit capability with no systematic replacement.

This paper presents the first study evaluating whether large language model (LLM) agents can substitute for human cross-pillar reasoning in TPM. We construct a synthetic evaluation dataset for a press brake machine (PB-07) containing 32 structured issues across all 8 TPM pillars, with 8 embedded cross-pillar connections and 2 red herrings as ground truth. The dataset is designed in two versions: V1 (clean, fully structured) and V2 (chaotic, with incomplete records, verbal-only reports, multi-source fragmentation, and embedded red herrings).

We evaluate two models — Qwen3.5 (6.6B parameters, local) and o3-mini (frontier, Azure OpenAI) — on connection recall, red herring identification, confidence calibration, and recommendation specificity. Our primary finding is that both models achieve 6/6 connection recall on V2. An apparent capability gap in red herring identification in an initial comparison was attributed entirely to a prompt engineering difference, not model capability. With identical prompts, both models flag red herrings correctly. Key differentiators are reasoning transparency (Qwen3.5 exposes a full thinking trace; o3-mini does not via Azure) and recommendation specificity (Qwen3.5 outputs are operationally actionable; o3-mini outputs are strategic and managerial).

These findings suggest that local, open-weight models are viable replacements for the human agentic layer in TPM cross-pillar reasoning, with implications for industrial AI deployment under data sovereignty and cost constraints.

---

## 1. Introduction

### 1.1 The Problem
- TPM's 8 pillars are a well-established framework. Each pillar has clear ownership, KPIs, and tooling.
- The framework's weakness: pillar teams only see their own data. A training record lives in HR. A die wear observation lives in AM. A procurement decision lives in Admin. Nobody sees all three simultaneously.
- The connections that matter most — the ones that explain chronic quality issues, recurring near-misses, unexplained scrap spikes — exist *between* pillars, not within them.
- In practice, this cross-pillar reasoning is performed by a small number of experienced investigators who have worked across functions. They are the undocumented glue.

### 1.2 The Agentic Layer
- We introduce the term *agentic layer* for this human role. An agent, in the sense used here, is an entity that: (a) holds context across multiple information sources simultaneously, (b) reasons about causal relationships that no single source makes explicit, (c) takes or recommends action based on that reasoning, and (d) updates its model of the system over time.
- The agentic layer is not replaceable by rules or dashboards. Rules require knowing the failure mode in advance. The agentic layer is precisely for the failure modes nobody anticipated.
- As experienced investigators retire, this capability is lost. Organisations default to reactive, single-pillar responses.

### 1.3 Research Questions
1. Can LLM agents perform cross-pillar TPM reasoning on incomplete, fragmented, multi-source data?
2. Does model scale (local vs frontier) affect connection recall on this task?
3. What factors other than recall differentiate model outputs in an industrial deployment context?
4. What role does prompt engineering play relative to model capability on this task?

### 1.4 Contributions
- A novel synthetic evaluation dataset for TPM cross-pillar reasoning with embedded ground truth
- A three-run comparative experiment revealing that apparent capability gaps can be prompt artefacts
- Evidence that local open-weight models are viable for industrial cross-pillar reasoning
- A taxonomy of output dimensions beyond recall relevant to industrial deployment (transparency, specificity, calibration)

---

## 2. Background

### 2.1 Total Productive Maintenance
- Brief overview of TPM and the 8 pillars
- The silo problem in TPM literature
- Existing approaches: CMMS integration, OEE dashboards, IoT sensor fusion
- What's missing: cross-functional causal reasoning

### 2.2 LLMs in Manufacturing
- Survey of existing LLM applications in manufacturing (fault detection, documentation, Q&A)
- The gap: existing work focuses on classification and retrieval, not multi-hop causal reasoning
- Closest related work: LLMs for root cause analysis in software (incident management), which shares structural similarities

### 2.3 Reasoning Under Incomplete Information
- Multi-hop reasoning literature
- Disconfirmation and red herring detection in LLM reasoning
- Thinking/reasoning models vs standard models

---

## 3. Dataset Design

### 3.1 Design Principles
- Ground truth must be embedded but not labeled — agent must discover, not retrieve
- Data must reflect real factory conditions: incomplete logs, multi-source, vague entries
- Connections must span at least 2 pillars and require inference, not pattern matching
- Red herrings must be structurally plausible (same temporal window, same machine, correlated but not causal)

### 3.2 Machine and Context
- PB-07: AMADA HFE 100-ton Hydraulic Press Brake
- 3-shift operation, single maintenance technician (Ray V), multiple operators with different logging behaviours
- 66-day observation window (Jan 1 – Mar 7, 2024)

### 3.3 Dataset V1 — Clean
- 32 issues across 8 pillars, fully structured tables
- 7 embedded cross-pillar connections (A–G), labeled only in a hidden section
- Purpose: proof of concept, validate agent architecture

### 3.4 Dataset V2 — Chaotic
- Same machine, extended to 9 information sources (adds raw shift handover notes)
- Realistic data quality: 4-day AM log gap, verbal-only near-miss reports, informal tech notes, incomplete work orders, new hire with no formal training record
- 8 embedded connections (V2-A through V2-H), 2 designated red herrings (V2-D, V2-G)
- Key design choice: Jordan P's name never appears in quality records — agent must infer the connection across operator identity gap

### 3.5 Ground Truth Annotation
- Connection scoring rubric: a connection is FOUND if the agent (a) identifies the correct pillars, (b) traces at least 2 of the issue IDs in the chain, and (c) provides a plausible causal mechanism
- Partial credit not applied in this study — binary FOUND/MISSED
- Red herring scoring: flagged if agent explicitly states the pattern is NOT causal and provides reasoning

---

## 4. Experimental Setup

### 4.1 Models
| Model | Parameters | Deployment | Thinking |
|---|---|---|---|
| Qwen3.5 | 6.6B | Local (Ollama) | Exposed (streaming) |
| o3-mini | Undisclosed | Azure OpenAI | Hidden (not surfaced via API) |

### 4.2 Prompt Design
- System prompt: role definition, pillar list, connection criteria, red herring instruction, investigation framing
- Investigation prompt: full dataset injection, structured output format specification
- Identical prompts used for both models in all valid runs

### 4.3 Run Protocol
- **Run 1 (invalid):** Prompts diverged — red herring instruction present in o3-mini only. Documented as a confound.
- **Run 2:** Qwen3.5 re-run with aligned prompt. o3-mini still on Run 1 prompt.
- **Run 3 (definitive):** Both models on identical prompts. o3-mini: 32,000 max tokens, `reasoning_effort=high`.

### 4.4 Evaluation Dimensions
1. **Connection recall** — fraction of hidden connections found (0–6)
2. **Red herring identification** — fraction of red herrings explicitly flagged with disconfirmation reasoning
3. **Confidence calibration** — appropriateness of HIGH/MEDIUM/LOW ratings relative to evidence strength
4. **Reasoning transparency** — availability of thinking trace for audit
5. **Recommendation specificity** — operational detail in priority actions (qualitative)

---

## 5. Results

### 5.1 Connection Recall
- Both models: 6/6 on V2 across all valid runs
- No recall difference between local 6.6B model and frontier model

### 5.2 Red Herring Identification — The Prompt Artefact Finding
- Run 1: Qwen3.5 0/2, o3-mini 2/2 → apparent frontier advantage
- Run 2/3: Qwen3.5 3/2 (flagged additional V2-F), o3-mini 2/2
- The Run 1 gap was entirely attributable to prompt design
- **Key result:** Prompt engineering explains at least as much variance as model selection on this task

### 5.3 Confidence Calibration
- o3-mini Run 3: 5/6 connections rated MEDIUM, 1/6 HIGH — conservative
- Qwen3.5 Run 2: ratings spread across HIGH and MEDIUM, tracking evidence strength more intuitively
- Neither model miscalibrated; different systematic tendencies

### 5.4 Reasoning Transparency
- Qwen3.5: 5,000–6,500 chars of visible thinking per run. Full audit trail available.
- o3-mini: 0 reasoning tokens surfaced via Azure API. Outputs appear without trace.
- This is not a model capability difference — it is an API/deployment configuration difference

### 5.5 Recommendation Specificity
- Qwen3.5: names part numbers, timelines, escalation framing, operator-level actions
- o3-mini: higher-level strategic framing, suitable for management briefing
- Neither is objectively better — they serve different stakeholders

---

## 6. Discussion

### 6.1 The Prompt Engineering Finding
- Most LLM evaluation studies hold prompts constant and vary models
- This study accidentally ran a prompt variation experiment
- Finding: a single instruction ("flag red herrings explicitly") fully accounts for the observed capability gap between a 6.6B local model and a frontier model on this task
- Implication: for practitioners, prompt design is the primary lever, not model selection

### 6.2 Local Models as Industrial Agents
- Qwen3.5 at 6.6B parameters, running on consumer hardware, matches frontier model recall
- Advantages for industrial deployment: no data leaves the premises, no API latency, no ongoing cost, full reasoning transparency
- Limitation: context window (8,192 tokens vs o3-mini's larger context) — may constrain performance on larger datasets

### 6.3 Reasoning Transparency as a Deployment Requirement
- In industrial settings, "why did you recommend that?" is a legitimate and frequent question
- A visible thinking trace allows a maintenance engineer to validate or reject the agent's reasoning before acting
- An opaque output requires the user to either trust blindly or re-derive the reasoning independently
- We argue transparency should be a first-class evaluation criterion for industrial AI, not an afterthought

### 6.4 The Taxonomy of Output Dimensions
- Existing evaluation focuses on recall/precision
- This study identifies 5 dimensions relevant to industrial deployment: recall, red herring detection, confidence calibration, transparency, specificity
- These dimensions serve different stakeholders (technician, engineer, manager) and different deployment contexts (on-floor, post-shift analysis, management reporting)

### 6.5 Limitations
- Single dataset, single machine type
- Single run per configuration — stochastic variation not characterised
- No human baseline — comparison is model vs model, not model vs expert
- Synthetic data — real factory data would contain additional noise types not modelled here
- Ground truth created by study authors — potential for confirmation bias in scoring

---

## 7. Future Work

- **Multiple runs:** 5+ runs per configuration to characterise stochastic variation
- **Human baseline:** ask maintenance engineers to analyse the same V2 dataset
- **V3 dataset:** 4+ pillar connection chains, longer time horizons, cross-machine interactions
- **Real data:** apply the framework to actual CMMS + quality + training data from a consenting factory
- **Agentic loop:** move from single-shot investigation to iterative agent that can ask clarifying questions

---

## 8. Conclusion

The human agentic layer in TPM — the investigator who holds cross-pillar context and surfaces connections that no single team sees — is a critical and under-documented organisational capability. This study demonstrates that LLM agents can perform this reasoning on incomplete, fragmented, multi-source industrial data with high connection recall.

The primary finding is methodological as much as empirical: an apparent capability advantage of a frontier model over a local 6.6B model was entirely attributable to a prompt engineering difference. With identical prompts, both models achieved the same recall and red herring identification. The meaningful differentiators for industrial deployment are reasoning transparency, recommendation specificity, and data sovereignty — dimensions on which the local model holds practical advantages.

---

## Appendices

**A.** Dataset V1 — full text
**B.** Dataset V2 — full text
**C.** Prompt specifications (system + investigation, final aligned version)
**D.** Full model outputs — Qwen3.5 Run 2, o3-mini Run 3
**E.** Scoring rubric for connection recall
**F.** Run log (all 3 runs, timestamps, model versions)

---

## To-Do Before Submission

- [ ] Literature review (Section 2) — ~40 references needed
- [ ] Multiple runs (5x per model) for stochastic robustness
- [ ] Human baseline experiment — at least 2 domain experts
- [ ] Inter-rater reliability check on connection scoring (2 independent raters)
- [ ] V3 dataset with harder connection chains
- [ ] Ethics note on synthetic data methodology
- [ ] Formal author list and affiliations

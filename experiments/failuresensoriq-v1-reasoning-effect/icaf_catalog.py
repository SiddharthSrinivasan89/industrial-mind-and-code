#!/usr/bin/env python3
"""ICAF task catalog — block 2 (Task Suitability) source of truth.

Maps a named industrial workflow to its task class. The class drives the temperature regime:
deterministic (one right answer) -> low temp; generative (open-ended) -> provider default.
This is a config catalog, not an inference — the commissioning loop runs entirely on-prem.
"""

# Deterministic regime: low temperature within 0-0.3 (reproducible, auditable, factual).
# Fixed at 0.3 (top of the deterministic band) — 0.2 was judged too low.
DETERMINISTIC_TEMP = 0.3

CATALOG = {
    # deterministic — the decision core
    "fault-diagnosis":      {"class": "deterministic", "desc": "sensor reading -> failure mode"},
    "alarm-classification": {"class": "deterministic", "desc": "alarm critical vs not"},
    "ticket-routing":       {"class": "deterministic", "desc": "route to team / asset"},
    "spec-extraction":      {"class": "deterministic", "desc": "pull a spec / parameter / part no."},
    "control-decision":     {"class": "deterministic", "desc": "valve setting, reorder quantity"},
    "compliance-check":     {"class": "deterministic", "desc": "meets standard: yes / no"},
    "root-cause-select":    {"class": "deterministic", "desc": "pick root cause from a known set"},
    # generative — the communication wrapper
    "work-order-draft":     {"class": "generative", "desc": "draft a work order / shift handover"},
    "fault-explanation":    {"class": "generative", "desc": "explain probable cause to an operator"},
    "alarm-summary":        {"class": "generative", "desc": "summarize the day's alarms"},
    "procedure-draft":      {"class": "generative", "desc": "draft a repair procedure / checklist"},
    "operator-chat":        {"class": "generative", "desc": "conversational operator interface"},
}

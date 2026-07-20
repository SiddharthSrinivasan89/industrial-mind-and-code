# Data — pdm-component-attribution-v1-azure

Raw data is not republished here; fetch it from the source below. Per-file SHA-256 checksums and
the pinned source commit are in [PROVENANCE.json](PROVENANCE.json).

## Source and license

- **Dataset:** Microsoft Azure Predictive Maintenance sample ("Predictive Maintenance Modelling
  Guide Data Sets") — five files: `PdM_telemetry.csv`, `PdM_errors.csv`, `PdM_maint.csv`,
  `PdM_machines.csv`, `PdM_failures.csv`. Simulated by Microsoft ("a synthesis of multiple
  real-world business problems").
- **Obtained from:** the Microsoft-owned repository
  [github.com/microsoft/sqlworkshops](https://github.com/microsoft/sqlworkshops), path
  `SQLServerAndAzureMachineLearning/ML Services for SQL Server/data/`, at a pinned commit
  (recorded in PROVENANCE.json). The original Azure AI (Cortana Intelligence) Gallery
  publication is retired.
- **License:** MIT (the license of the distributing repository). MIT permits use, modification,
  redistribution, and publication of derived artifacts with the copyright/license notice
  retained.
- **Attribution:** "Microsoft Azure Predictive Maintenance sample dataset (Predictive
  Maintenance Modelling Guide), © Microsoft Corporation, MIT License, obtained from
  github.com/microsoft/sqlworkshops."

## What the data contains (verified at fetch)

100 simulated machines over calendar 2015: hourly telemetry (voltage, rotation, pressure,
vibration; 876,100 rows), dated error events (error1–error5; 3,919 rows), component replacements
(comp1–comp4; 3,286 rows, history from mid-2014), machine metadata (model1–model4, age 0–20),
and dated component failures (761 rows). After collapsing to unique (machine, timestamp) events
and excluding 42 multi-component events, 677 single-component failure events over 98 machines
remain. A time-based split at 2015-09-01 gives 464 training and 213 evaluation events.

The failure log records a component replacement at the exact failure timestamp for the failed
component, so any evidence window must be censored strictly before the failure time to avoid
label leakage. This is enforced in the feature builder and checked by the data-gate audits.

# H2b power simulation notes (2026-07-18)

Question: can TOST at δ = 0.10 ever pass on the materialized 51-event / 22-machine Arm C
probe? Method: paired binary outcomes per event via Gaussian copula (ρ = 0.6), Arm B accuracy
a_B = 0.5, Arm C accuracy a_B − gap; machine-cluster bootstrap (resample the 22 probe
machines) 90% percentile CI of the mean paired gap; TOST passes iff the CI lies inside
(−0.10, +0.10). 400 simulations × 400 replicates per cell.

| True gap | TOST pass rate |
|---|---|
| 0.00 | 0.007 |
| 0.05 | 0.015 |
| 0.10 | 0.010 |

Conclusion: the CI is far wider than ±10 points at this size — equivalence testing is
infeasible; even a genuinely invariant subject would "fail" to show equivalence >99% of the
time. Consequence (FROZEN-SPEC §5): R9–R10 are descriptive (gap + 90% CI + MDE) with the
pre-declared cap rule only; no equivalence verdict exists at this design. Enlarging the probe
was not adopted — it would exceed the probe scope Sid ruled on 2026-07-18 and multiply the
metered Arm C cost.

Caveats: ρ and a_B are assumptions, not estimates; the qualitative conclusion (CI width ≫ δ)
is insensitive to both within plausible ranges. Rerun with observed values at analysis time
for the reported MDE.

---
description: Run a Monte Carlo ensemble (N=1000 by default) over the scenario's parameter uncertainties using the surrogate, producing P10/P50/P90 bands.
argument-hint: <scenario_name_from_demo/scenarios.yaml or inline scenario JSON>
---

# /parallel-mc

Run a Monte Carlo ensemble for uncertainty quantification.

**Scenario:** $ARGUMENTS

## Steps

1. Load the scenario — either from `demo/scenarios.yaml` (by name) or parse inline JSON.
2. Invoke the `geologist` subagent to validate the base scenario and produce default distributions for the parameters.
3. Invoke the `uq-specialist` subagent with:
   - base scenario
   - parameter distributions from geologist
   - `n_samples=1000`
   - `engine="surrogate"`
4. Invoke the `visualizer` subagent with the resulting bands (p10, p50, p90) — produce a UQ-band figure.
5. Invoke the `reviewer` subagent on the p50 result.
6. Present the result: mean P10/P50/P90 field plots, wall-clock time, reviewer findings.

## Guardrails

- Never run MC through the solver (hours of compute).
- If geologist rejects the base scenario, stop.
- If reviewer flags physics violations in p50, surface them.

## Expected wall-clock

~3–5 seconds for N=1000 on the surrogate.

---
name: monte-carlo-uq
description: Run Monte Carlo ensembles over user-specified parameter distributions and produce P10/P50/P90 bands. Also supports one-at-a-time sensitivity analysis. Use via the uq-specialist agent whenever the user asks about uncertainty, confidence intervals, sensitivity, or risk.
---

# Monte Carlo UQ Skill

Quantify uncertainty by sampling parameter distributions and aggregating surrogate inference results.

## When to Use

- User asks "how confident are you?"
- User asks "what's the range of outcomes?"
- User asks "which parameter matters most?" (→ sensitivity)
- Any Q2 sustainability question (uncertainty materially changes the answer)

## Method: Monte Carlo Ensemble

```python
from tools.monte_carlo import run_ensemble

out = run_ensemble(
    base_scenario=scenario_dict,
    param_distributions={
        "log_k": ("uniform", -14.5, -13.5),         # (dist_type, lo, hi) or (dist_type, μ, σ)
        "porosity": ("truncnorm", 0.08, 0.02, 0.01, 0.15),
        "base_T_C": ("normal", 250.0, 5.0),
    },
    n_samples=1000,
    engine="surrogate",   # always use surrogate for MC (3ms × 1000 = 3s)
    seed=42,
)

# out["samples"]: shape (1000, scenario dim)
# out["predictions"]: shape (1000, 10, 32, 32)  # 10 = 5T + 5P channels
# out["bands"]: dict of p10/p50/p90 per channel
```

## Method: Sensitivity (One-at-a-time)

```python
from tools.sensitivity import one_at_a_time

out = one_at_a_time(
    base_scenario=scenario_dict,
    params=["log_k", "porosity", "base_T_C", "base_P_MPa", "depth_m"],
    perturbation=0.20,   # ±20%
    engine="surrogate",
)

# out["ranking"]: list of dicts sorted by |ΔT_mean|
# [
#   {"param": "log_k", "delta_T_mean_pos": 8.2, "delta_T_mean_neg": -7.9, "abs_delta": 8.05},
#   {"param": "base_T_C", ...},
#   ...
# ]
```

## Aggregation

P10/P50/P90 are computed **per cell, per timestep** (not globally). This preserves spatial structure of uncertainty.

```python
p10 = np.percentile(ensemble, 10, axis=0)   # shape (10, 32, 32)
p50 = np.percentile(ensemble, 50, axis=0)
p90 = np.percentile(ensemble, 90, axis=0)
```

## Runtime Guide

| N_samples | Surrogate wall-clock |
|---|---|
| 100 | ~0.3 s |
| 1,000 | ~3 s |
| 10,000 | ~30 s |

For demo responsiveness, default to N=1000.

## Defaults for Common Parameters

If the user says "with uncertainty" without specifying distributions:

| Parameter | Default distribution |
|---|---|
| `log_k` | Uniform(μ - 0.5, μ + 0.5) |
| `porosity` | Truncnorm(μ, σ=0.02, bounds=[0.01, 0.15]) |
| `base_T_C` | Normal(μ, σ=5) |
| `base_P_MPa` | Normal(μ, σ=0.3) |
| `depth_m` | Normal(μ, σ=50) |

## Anti-patterns

- Do not run MC through the solver (8+ hours for N=1000).
- Do not report only the mean — always include bands.
- Do not collapse time dimension when aggregating.
- Do not sample outside geologist-validated ranges.

---
name: analytical-benchmarks
description: Closed-form analytical solutions for validating GeoForce-Solver. Includes Theis (line-source pressure drawdown) and 1D heat conduction (Fourier). Use these as the truth against which the numerical solver must agree within 5% relative error before any output is trusted.
---

# Analytical Benchmarks Skill

Closed-form solutions used as ground truth for the GeoForce-Solver solver.

## 1. Theis Line-Source Solution (Pressure)

Classic groundwater/reservoir engineering benchmark. A single production well in an infinite, homogeneous, single-phase aquifer.

### Equation

```
drawdown(r, t) = (Q / (4π T)) * W(u)
u = (r² S) / (4 T t)
W(u) ≈ -γ - ln(u) + u - u²/4 + ...    # exponential integral
```

Where:
- `Q` = production rate (m³/s)
- `T` = transmissivity = k·h/μ
- `S` = storativity = φ·c_t·h
- `r` = radial distance from well (m)
- `t` = time (s)

### Implementation

```python
from solver.benchmarks.theis import theis_drawdown

dp = theis_drawdown(
    r_m=50.0,
    t_s=86400 * 30,       # 30 days
    Q_m3_s=0.01,
    k_m2=1e-13,
    mu_Pa_s=1e-4,
    h_m=100.0,
    phi=0.1,
    c_t_Pa=5e-10,
)
# dp: pressure drawdown in Pa
```

### Test

`tests/test_solver_theis.py`:

1. Run GeoForce-Solver on a single-producer, homogeneous scenario for 30 days
2. Extract pressure drawdown at radial distances (r=10, 50, 100, 200 m)
3. Compute analytical Theis at same (r, t)
4. Assert `max |P_numerical - P_analytical| / |P_analytical| < 0.05`

## 2. 1D Heat Conduction (Temperature)

Semi-infinite slab with step temperature change at boundary. Simplest heat benchmark.

### Equation

```
T(z, t) - T_ambient = (T_wall - T_ambient) * erfc(z / (2 sqrt(α t)))
α = k / (ρ c_p)         # thermal diffusivity
```

Where:
- `T_wall` = boundary temperature at z=0
- `T_ambient` = initial temperature
- `z` = depth (m)
- `t` = time (s)
- `α` = thermal diffusivity (m²/s)

### Implementation

```python
from solver.benchmarks.conduction_1d import conduction_1d

T_z = conduction_1d(
    z_m=10.0,
    t_s=86400 * 365,      # 1 year
    T_wall_C=200.0,
    T_ambient_C=25.0,
    alpha_m2_s=1e-6,
)
# T_z: temperature at depth z and time t
```

### Test

`tests/test_solver_conduction.py`:

1. Run GeoForce-Solver on a scenario with a fixed hot boundary at top (z=0), cold interior, **no flow** (Darcy disabled or log_k → -∞)
2. Extract T at depth z=5, 10, 20, 50 m after t=1 year
3. Compute analytical erfc solution at same (z, t)
4. Assert `max |T_numerical - T_analytical| < 5.0 °C` AND `max relative error < 0.05`

## Why These Two?

- **Theis** isolates the pressure/Darcy solver — no temperature coupling
- **1D conduction** isolates the energy/heat solver — no pressure coupling
- Together they gate the coupled solver: if both isolated solvers work, the coupled version's failure is the coupling logic itself (narrower debug target)

## Acceptance Thresholds

Both tests must pass before solver output is trusted. If either fails:
- Investigate once: try smaller timestep, finer grid, check boundary conditions
- If second attempt fails: **drop solver from critical path**, fall back to surrogate-only

## Anti-patterns

- Do not relax the 5% threshold to make the test pass
- Do not compare only at t=0 (trivially correct)
- Do not run these tests against the *uncoupled* solver and claim the *coupled* solver passes
- Do not skip the well-placement geometry — Theis needs a real point source

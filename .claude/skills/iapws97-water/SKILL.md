---
name: iapws97-water
description: Compute liquid water properties (density, viscosity, enthalpy) using the IAPWS-IF97 industrial formulation. Use whenever you need ρ(T,P), μ(T), or h(T,P) for geothermal reservoir calculations. Valid range: 0–350°C, 0.1–100 MPa, liquid phase only.
---

# IAPWS-IF97 Water Properties Skill

Standard industrial-grade formulation for liquid water thermodynamic properties. Used by GeoForce-Solver's solver and for any property lookup in the codebase.

## Dependency

```bash
pip install iapws>=1.5.3
```

## Usage

```python
from iapws import IAPWS97

# T in Kelvin, P in MPa
state = IAPWS97(T=298.15, P=1.0)

state.rho    # kg/m³ (density)
state.mu     # Pa·s (viscosity)
state.h      # kJ/kg (specific enthalpy)
state.cp     # kJ/(kg·K) (specific heat at const pressure)
state.k      # W/(m·K) (thermal conductivity)
```

## Vectorized Wrapper

For grid-wide computations, use the wrapper in `solver/properties.py`:

```python
from solver.properties import rho_field, mu_field, h_field

T_K = np.full((30, 50), 523.15)   # 250°C everywhere
P_MPa = np.full((30, 50), 10.0)   # 10 MPa everywhere

rho = rho_field(T_K, P_MPa)       # kg/m³
mu  = mu_field(T_K, P_MPa)        # Pa·s
h   = h_field(T_K, P_MPa)         # kJ/kg
```

## Important Constraints

- **Liquid phase only.** If pressure drops below saturation for a given T, IAPWS97 raises `NotImplementedError`. Clamp P ≥ P_sat(T) + ε upstream.
- **Temperature range:** 273.15 K to 623.15 K (0°C to 350°C). Outside this range, use polynomial fits (out of scope for v0.1).
- **Performance:** IAPWS97 is ~0.1 ms per call. For a 50×30 grid, ~1500 calls per field → ~150 ms. Acceptable per time step; cache where possible.

## Caching Strategy

Density ρ varies slowly with T. For Boussinesq approximation:
- Compute ρ at base (T₀, P₀) once — use as reference density
- Compute ρ only where gravity buoyancy is evaluated
- Skip ρ updates within the linear solver

## Validation

Reference values (sanity check):

| T (°C) | P (MPa) | ρ (kg/m³) | μ (Pa·s) | h (kJ/kg) |
|---|---|---|---|---|
| 25 | 1 | 997.1 | 8.90e-4 | 104.9 |
| 150 | 1 | 916.8 | 1.82e-4 | 632.3 |
| 250 | 10 | 798.4 | 1.08e-4 | 1085.8 |
| 300 | 10 | 713.8 | 8.59e-5 | 1344.0 |

## What This Skill Does NOT Cover

- Steam properties (gaseous phase) — requires IAPWS95 or two-phase logic
- Saturation pressure P_sat(T) — use `iapws.IAPWS97_PT` or wrappers if needed
- Salt effects — would need EWASG module (out of scope for v0.1)

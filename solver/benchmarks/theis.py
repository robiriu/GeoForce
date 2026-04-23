"""Theis (1935) analytical solution for a line-source/sink in a 2D confined aquifer.

Pressure change at radial distance r and time t from a constant mass-rate well:

    Delta_p(r, t) = (Q_m * mu) / (4 * pi * rho * k * h) * W(u)

with

    u = phi * mu * c_t * r^2 / (4 * k * t)
    W(u) = E_1(u) = integral_u^inf (exp(-s)/s) ds

Convention:
    * Q_m > 0 is INJECTION -> Delta_p > 0 (pressure rises).
    * Q_m < 0 is PRODUCTION -> Delta_p < 0 (pressure falls).

Assumptions:
    * Infinite, homogeneous, isotropic 2D aquifer of constant thickness h.
    * Point source, single-phase liquid, constant fluid properties.
"""

from __future__ import annotations

import numpy as np
from scipy.special import exp1


def well_function(u: float | np.ndarray) -> np.ndarray | float:
    """Theis well function W(u) = E_1(u).

    scipy.special.exp1 computes the exponential integral for positive u.
    For u -> 0, W(u) -> -gamma - ln(u) (logarithmic singularity).
    """
    return exp1(np.asarray(u))


def theis_pressure_change(
    *,
    r: float | np.ndarray,
    t: float | np.ndarray,
    mass_rate: float,
    permeability: float,
    viscosity: float,
    density: float,
    porosity: float,
    total_compressibility: float,
    thickness: float = 1.0,
) -> np.ndarray:
    """Analytical Theis pressure change at (r, t).

    Args:
        r: radial distance (m). Scalar or array.
        t: time since well start (s). Scalar or array. Broadcast with r.
        mass_rate: well mass rate (kg/s), positive for injection.
        permeability: aquifer permeability (m^2).
        viscosity: fluid dynamic viscosity (Pa.s).
        density: fluid density (kg/m^3).
        porosity: porosity (dimensionless).
        total_compressibility: rock + fluid (1/Pa).
        thickness: out-of-plane aquifer thickness (m). Default 1 for 2D slab.

    Returns:
        Pressure change array broadcast from r and t, in Pa.
    """
    r = np.asarray(r, dtype=np.float64)
    t = np.asarray(t, dtype=np.float64)

    u = porosity * viscosity * total_compressibility * r**2 / (4.0 * permeability * t)
    w = well_function(u)
    coeff = (mass_rate * viscosity) / (4.0 * np.pi * density * permeability * thickness)
    return coeff * w

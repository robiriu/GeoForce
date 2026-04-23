"""Analytical 1D heat conduction in a semi-infinite slab.

For an initially uniform medium at T_initial, with the x=0 surface suddenly
raised to T_boundary at t=0 (step change), the temperature field is:

    T(x, t) = T_initial + (T_boundary - T_initial) * erfc( x / (2 * sqrt(alpha * t)) )

where alpha = lambda / (rho * cp) is the thermal diffusivity.

Assumptions:
    * 1D, semi-infinite slab (x >= 0).
    * Constant thermal properties.
    * Dirichlet BC at x=0, initial condition T(x, 0) = T_initial for x > 0.
"""

from __future__ import annotations

import numpy as np
from scipy.special import erfc


def conduction_step_temperature(
    *,
    x: float | np.ndarray,
    t: float | np.ndarray,
    T_initial: float,
    T_boundary: float,
    thermal_diffusivity: float,
) -> np.ndarray:
    """Return T(x, t) for a step-temperature semi-infinite slab.

    Args:
        x: distance from the Dirichlet surface (m). Scalar or array.
        t: elapsed time since the step change (s). Scalar or array.
        T_initial: uniform initial temperature (any consistent unit).
        T_boundary: temperature held at x=0 for t > 0 (same unit as T_initial).
        thermal_diffusivity: alpha = lambda / (rho*cp), (m^2/s).

    Returns:
        Temperature array broadcast from x and t.
    """
    x = np.asarray(x, dtype=np.float64)
    t = np.asarray(t, dtype=np.float64)
    eta = x / (2.0 * np.sqrt(thermal_diffusivity * t))
    return T_initial + (T_boundary - T_initial) * erfc(eta)

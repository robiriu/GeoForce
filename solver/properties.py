"""IAPWS-IF97 liquid water properties for GeoForce-Solver.

For the Day-1 Theis benchmark we only need *reference-state* properties
(constant density and viscosity), which matches the linearized Boussinesq
assumption in the pressure equation.

The full IAPWS-IF97 wrapper is available for the coupled T-P solve where
density and viscosity vary with temperature.

Single-phase liquid only. If the user asks for vapor or two-phase, return
NaN — the scope rules forbid that physics in this hackathon build.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from iapws import IAPWS97


def _celsius_to_kelvin(t_c: float) -> float:
    return t_c + 273.15


def _pa_to_mpa(p_pa: float) -> float:
    return p_pa * 1e-6


@dataclass(frozen=True)
class WaterProperties:
    """Constant reference-state water properties (Boussinesq).

    Attributes:
        rho: density (kg/m^3)
        mu:  dynamic viscosity (Pa.s)
        cp:  isobaric specific heat (J/kg/K)
        h:   specific enthalpy (J/kg)
        c_f: isothermal fluid compressibility (1/Pa)
    """

    rho: float
    mu: float
    cp: float
    h: float
    c_f: float

    @classmethod
    def at_reference(cls, t_c: float = 100.0, p_pa: float = 1.0e7) -> "WaterProperties":
        """Compute IAPWS-IF97 properties at the given (T, P) reference state.

        Args:
            t_c: reference temperature in Celsius (default 100 C).
            p_pa: reference pressure in Pa (default 10 MPa).
        """
        state = IAPWS97(T=_celsius_to_kelvin(t_c), P=_pa_to_mpa(p_pa))
        # IAPWS exposes cp in kJ/kg/K and h in kJ/kg, so convert.
        cp_j = state.cp * 1000.0
        h_j = state.h * 1000.0
        c_f = 1.0 / (state.rho * state.w**2)  # isothermal compressibility = 1 / (rho c^2)
        return cls(
            rho=float(state.rho),
            mu=float(state.mu),
            cp=float(cp_j),
            h=float(h_j),
            c_f=float(c_f),
        )


def water_rho(t_c: float | np.ndarray, p_pa: float | np.ndarray) -> np.ndarray:
    """Vectorized liquid density (kg/m^3) via IAPWS-IF97. Arrays are elementwise."""
    t_arr = np.atleast_1d(t_c)
    p_arr = np.atleast_1d(p_pa)
    t_arr, p_arr = np.broadcast_arrays(t_arr, p_arr)
    out = np.empty_like(t_arr, dtype=np.float64)
    for idx in np.ndindex(t_arr.shape):
        s = IAPWS97(T=_celsius_to_kelvin(float(t_arr[idx])), P=_pa_to_mpa(float(p_arr[idx])))
        out[idx] = s.rho
    return out.reshape(np.asarray(t_c).shape) if np.ndim(t_c) else float(out[0])


def water_mu(t_c: float | np.ndarray, p_pa: float | np.ndarray = 1.0e7) -> np.ndarray:
    """Vectorized liquid dynamic viscosity (Pa.s) via IAPWS-IF97."""
    t_arr = np.atleast_1d(t_c)
    p_arr = np.atleast_1d(p_pa)
    t_arr, p_arr = np.broadcast_arrays(t_arr, p_arr)
    out = np.empty_like(t_arr, dtype=np.float64)
    for idx in np.ndindex(t_arr.shape):
        s = IAPWS97(T=_celsius_to_kelvin(float(t_arr[idx])), P=_pa_to_mpa(float(p_arr[idx])))
        out[idx] = s.mu
    return out.reshape(np.asarray(t_c).shape) if np.ndim(t_c) else float(out[0])

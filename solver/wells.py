"""Well source/sink terms for GeoForce-Solver.

Each :class:`WellSpec` is pinned to a single grid cell and carries a
signed mass rate (+ injection, − production) and (for injectors) an
injection temperature. This module does *not* implement a Peaceman
productivity index — the well is just a direct volumetric source in the
host cell. For the 2D vertical-section hackathon scope that is accurate
enough; real wellbore hydraulics are out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .grid import Grid


@dataclass(frozen=True)
class WellSpec:
    """A point well pinned to a single grid cell.

    Attributes:
        i, j: cell indices.
        mass_rate: kg/s. Positive = injection, negative = production.
        injection_temperature: (°C or K — match the solver's T field). Required
            when ``mass_rate > 0``; ignored otherwise.
    """

    i: int
    j: int
    mass_rate: float
    injection_temperature: float | None = None

    def __post_init__(self) -> None:
        if self.mass_rate > 0.0 and self.injection_temperature is None:
            raise ValueError(
                f"Injection well at ({self.i}, {self.j}) requires injection_temperature"
            )


def apply_wells(
    wells: list[WellSpec],
    grid: Grid,
    *,
    rho_ref: float,
    cp_water: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build per-cell source arrays from a list of wells.

    Args:
        wells: list of well specs.
        grid: simulation grid.
        rho_ref: reference water density (kg/m^3) used to convert mass rate to
            a volumetric rate for the Darcy eq.
        cp_water: specific heat of liquid water (J/kg/K).

    Returns:
        ``(q_vol, q_heat_inj, m_prod)`` where
            * ``q_vol`` (shape ``(nx, ny)``, m^3/s) is the signed volumetric
              source for the pressure equation.
            * ``q_heat_inj`` (shape ``(nx, ny)``, W) is the injection-side
              advective heat source — added directly to the RHS of the energy
              equation as ``m_dot * cp_water * T_inj``.
            * ``m_prod`` (shape ``(nx, ny)``, kg/s, ≥ 0) is the magnitude of
              the produced mass rate per cell; the energy solver adds
              ``m_prod * cp_water`` to the diagonal so that produced enthalpy
              leaves at the cell's implicit temperature.
    """
    q_vol = np.zeros(grid.shape, dtype=np.float64)
    q_heat_inj = np.zeros(grid.shape, dtype=np.float64)
    m_prod = np.zeros(grid.shape, dtype=np.float64)
    for w in wells:
        if not (0 <= w.i < grid.nx and 0 <= w.j < grid.ny):
            raise IndexError(f"well at ({w.i}, {w.j}) lies outside grid {grid.shape}")
        q_vol[w.i, w.j] += w.mass_rate / rho_ref
        if w.mass_rate > 0.0:
            q_heat_inj[w.i, w.j] += (
                w.mass_rate * cp_water * float(w.injection_temperature)
            )
        elif w.mass_rate < 0.0:
            m_prod[w.i, w.j] += -w.mass_rate
    return q_vol, q_heat_inj, m_prod

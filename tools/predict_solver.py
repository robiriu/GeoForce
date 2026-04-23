"""Unified `predict(scenario)` wrapper around GeoForce-Solver.

The agent calls this with a plain dict describing the reservoir + wells +
time stepping, and gets back a common schema:

    {
        "temperature": np.ndarray,   # (nx, ny) deg C, final time step
        "pressure":    np.ndarray,   # (nx, ny) Pa,   final time step
        "grid": {
            "nx": int, "ny": int,
            "dx": float, "dy": float,   # meters
            "extent_x": [x_min, x_max],  # meters (cell edges)
            "extent_y": [y_min, y_max],
        },
        "engine": "solver",
        "elapsed_seconds": float,
    }

The scenario dict may omit most keys; sensible defaults match the Indonesian
geothermal scenarios we demo.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from solver.coupled import run_coupled_transient
from solver.grid import Grid
from solver.properties import WaterProperties
from solver.wells import WellSpec

DEFAULTS: dict[str, Any] = {
    "nx": 40,
    "ny": 20,
    "dx": 10.0,
    "dy": 10.0,
    "porosity": 0.12,
    "permeability": 5.0e-13,
    "rho_rock": 2500.0,
    "cp_rock": 1000.0,
    "lam_rock": 2.5,
    "T_initial": 200.0,
    "P_initial": 1.5e7,
    "dt": 5.0e5,
    "n_steps": 60,
    "wells": [],
}


def _coerce_wells(raw: list[dict[str, Any]]) -> list[WellSpec]:
    out: list[WellSpec] = []
    for w in raw:
        out.append(
            WellSpec(
                i=int(w["i"]),
                j=int(w["j"]),
                mass_rate=float(w["mass_rate"]),
                injection_temperature=(
                    float(w["injection_temperature"])
                    if w.get("injection_temperature") is not None
                    else None
                ),
            )
        )
    return out


def predict(scenario: dict[str, Any]) -> dict[str, Any]:
    """Run the coupled GeoForce solver on a scenario dict.

    Args:
        scenario: dict with any subset of the DEFAULTS keys overridden.
            Special keys:
                - ``wells``: list of {i, j, mass_rate, injection_temperature?}.

    Returns:
        Dict with final-time T/P fields + grid metadata + ``engine``.
    """
    cfg = {**DEFAULTS, **scenario}

    grid = Grid(nx=int(cfg["nx"]), ny=int(cfg["ny"]), dx=float(cfg["dx"]), dy=float(cfg["dy"]))

    props = WaterProperties.at_reference(t_c=float(cfg["T_initial"]), p_pa=float(cfg["P_initial"]))

    phi = float(cfg["porosity"])
    rho_cp_eff = (1.0 - phi) * float(cfg["rho_rock"]) * float(cfg["cp_rock"]) + phi * props.rho * props.cp
    lam_eff = (1.0 - phi) * float(cfg["lam_rock"]) + phi * 0.68  # water lam ~0.68 W/m/K

    t0 = np.full(grid.shape, float(cfg["T_initial"]), dtype=np.float64)
    p0 = np.full(grid.shape, float(cfg["P_initial"]), dtype=np.float64)

    wells = _coerce_wells(list(cfg["wells"]))

    start = time.perf_counter()
    p_hist, t_hist = run_coupled_transient(
        grid=grid,
        p_initial=p0,
        t_initial=t0,
        permeability=float(cfg["permeability"]),
        porosity=phi,
        total_compressibility=props.c_f + 1.0e-9,
        mu=props.mu,
        rho=props.rho,
        cp_water=props.cp,
        thermal_conductivity=lam_eff,
        volumetric_heat_capacity=rho_cp_eff,
        dt=float(cfg["dt"]),
        n_steps=int(cfg["n_steps"]),
        wells=wells,
    )
    elapsed = time.perf_counter() - start

    return {
        "temperature": t_hist[-1],
        "pressure": p_hist[-1],
        "grid": {
            "nx": grid.nx,
            "ny": grid.ny,
            "dx": grid.dx,
            "dy": grid.dy,
            "extent_x": [0.0, grid.nx * grid.dx],
            "extent_y": [0.0, grid.ny * grid.dy],
        },
        "engine": "solver",
        "elapsed_seconds": elapsed,
    }

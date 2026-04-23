"""Unified `predict(scenario)` wrapper around the v1.1 CNN surrogate.

Returns the same schema as :func:`tools.predict_solver.predict` so the
agent can swap engines without changing downstream plumbing.

The surrogate is a fixed 32x32 grid trained on a specific physical domain.
The scenario dict may supply `dx`/`dy` as grid metadata for downstream
coordinate mapping, but the CNN itself always runs on 32x32.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from surrogate.predict import predict as _cnn_predict

SURROGATE_NX = 32
SURROGATE_NY = 32

DEFAULTS: dict[str, Any] = {
    "dx": 12.5,  # meters; surrogate native domain is 400m x 400m
    "dy": 12.5,
    "porosity": 0.12,
    "log_permeability": -12.3,  # log10(5e-13)
    "base_pressure": 1.5e7,
    "depth": 1500.0,
    "T_initial": 200.0,
    "wells": [],
}


def _rescale_well_indices(
    wells: list[dict[str, Any]],
    *,
    source_nx: int | None,
    source_ny: int | None,
) -> list[tuple[int, int]]:
    """Map (i, j) cell indices from an arbitrary grid onto the surrogate's 32x32.

    Interprets (i, j) as (row, col) in the source grid. If source_nx/source_ny
    is None, assumes the well indices are already in 32x32 surrogate space.
    """
    out: list[tuple[int, int]] = []
    for w in wells:
        i = int(w["i"])
        j = int(w["j"])
        if source_nx is not None and source_ny is not None:
            i_s = int(round(i * (SURROGATE_NX - 1) / max(source_nx - 1, 1)))
            j_s = int(round(j * (SURROGATE_NY - 1) / max(source_ny - 1, 1)))
        else:
            i_s, j_s = i, j
        i_s = int(np.clip(i_s, 0, SURROGATE_NX - 1))
        j_s = int(np.clip(j_s, 0, SURROGATE_NY - 1))
        out.append((i_s, j_s))
    return out


def predict(scenario: dict[str, Any]) -> dict[str, Any]:
    """Run the v1.1 CNN surrogate on a scenario dict.

    Args:
        scenario: plain dict. Recognised keys:
            - ``T_initial`` (scalar degC) OR ``initial_temperature`` ((32,32) array)
            - ``log_permeability`` (float)
            - ``permeability`` (float, converted via log10 if ``log_permeability`` absent)
            - ``base_pressure`` (Pa)
            - ``porosity``, ``depth``
            - ``wells``: list of {i, j, ...}; indices rescaled from (nx, ny) → 32x32.
            - ``nx``, ``ny``: source-grid dims used to rescale well indices.
            - ``dx``, ``dy``: optional, just used for grid metadata in the output.

    Returns:
        Same schema as predict_solver: temperature/pressure (32, 32) at the
        final time step + grid metadata + engine + elapsed_seconds.
    """
    cfg = {**DEFAULTS, **scenario}

    if "initial_temperature" in cfg:
        t_init = np.asarray(cfg["initial_temperature"], dtype=np.float32)
        if t_init.shape != (SURROGATE_NX, SURROGATE_NY):
            msg = f"initial_temperature shape {t_init.shape} != ({SURROGATE_NX}, {SURROGATE_NY})"
            raise ValueError(msg)
    else:
        t_init = np.full((SURROGATE_NX, SURROGATE_NY), float(cfg["T_initial"]), dtype=np.float32)

    if "log_permeability" in scenario:
        log_k = float(scenario["log_permeability"])
    elif "permeability" in scenario:
        log_k = float(np.log10(float(scenario["permeability"])))
    else:
        log_k = float(cfg["log_permeability"])

    wells_raw = list(cfg["wells"])
    well_locations = _rescale_well_indices(
        wells_raw,
        source_nx=int(cfg["nx"]) if "nx" in cfg else None,
        source_ny=int(cfg["ny"]) if "ny" in cfg else None,
    )

    start = time.perf_counter()
    out = _cnn_predict(
        initial_temperature=t_init,
        log_permeability=log_k,
        well_locations=well_locations,
        base_pressure=float(cfg["base_pressure"]),
        porosity=float(cfg["porosity"]),
        depth=float(cfg["depth"]),
    )
    elapsed = time.perf_counter() - start

    t_final = out["temperature"][-1]
    p_final = out["pressure"][-1]

    dx = float(cfg["dx"])
    dy = float(cfg["dy"])
    return {
        "temperature": t_final,
        "pressure": p_final,
        "grid": {
            "nx": SURROGATE_NX,
            "ny": SURROGATE_NY,
            "dx": dx,
            "dy": dy,
            "extent_x": [0.0, SURROGATE_NX * dx],
            "extent_y": [0.0, SURROGATE_NY * dy],
        },
        "engine": "surrogate",
        "elapsed_seconds": elapsed,
    }

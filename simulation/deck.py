"""Render a Waiwera input deck (JSON) from a (Scenario, GridSpec, WellSet) triple.

Waiwera consumes a JSON input file documented at
https://waiwera.github.io/documentation/input-files . We construct the dict
directly rather than going through PyTOUGH's t2data->json path because that
path requires writing a separate mesh file and complicates round-trip
testing. PyTOUGH's `mulgrid` is still used to produce the companion
ExodusII mesh file that Waiwera reads.

Two-phase water EOS is `we` (water + energy). For pure single-phase liquid
runs `wae` is also valid; we default to `we` since the campaign sweeps
through vapor-dominated and two-phase regimes.

The output of `build_deck()` is a plain dict and a list of files to write
(mesh file path + JSON file path). The caller decides where to put them
on disk — the VPS test path uses a tmp dir; the Kaggle notebook uses
`/kaggle/working/`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from simulation.grid import (
    DX_M,
    DY_M,
    DZ_M,
    NX,
    NY,
    NZ,
    BASEMENT_K,
    CAPROCK_K,
    RESERVOIR_K,
    GridSpec,
    initial_pressure_Pa,
    initial_temperature_C,
    per_cell_properties,
)
from simulation.sampling import Scenario
from simulation.wells import Well, WellSet

EOS_DEFAULT: str = "we"
GRAVITY_M_S2: float = 9.80665
SECONDS_PER_YEAR: float = 365.25 * 86400.0
DEFAULT_TIMESTEPS_YEARS: tuple[float, ...] = (1, 3, 5, 7, 10, 13, 16, 20, 25, 30)


@dataclass(frozen=True)
class DeckBundle:
    """Filesystem artifacts a single Waiwera run needs."""

    json_doc: dict
    mesh_path: Path
    json_path: Path


def _block_index(i: int, j: int, k: int) -> int:
    """Cell-major linear index used as the Waiwera cell id."""
    return (k * NY + j) * NX + i


def _rock_blocks(grid: GridSpec) -> dict[str, list[int]]:
    """Map rock type name -> list of cell ids belonging to that rock."""
    out: dict[str, list[int]] = {"caprock": [], "reservoir": [], "basement": []}
    for k in range(NZ):
        if CAPROCK_K[0] <= k < CAPROCK_K[1]:
            tag = "caprock"
        elif RESERVOIR_K[0] <= k < RESERVOIR_K[1]:
            tag = "reservoir"
        else:
            tag = "basement"
        for j in range(NY):
            for i in range(NX):
                out[tag].append(_block_index(i, j, k))
    return out


def _well_sources(wells: WellSet) -> list[dict]:
    """Translate WellSet to Waiwera 'source' entries (one per (well, cell))."""
    sources: list[dict] = []
    for w_idx, w in enumerate(wells.wells):
        # Distribute the rate evenly across the well's open layers.
        n_layers = w.k_bot - w.k_top
        per_layer_rate = w.rate_kg_s / n_layers
        for k in range(w.k_top, w.k_bot):
            cell_id = _block_index(w.i, w.j, k)
            kind = "producer" if w.kind == "producer" else "injector"
            entry: dict = {
                "name": f"{kind[0].upper()}{w_idx:02d}_k{k}",
                "cell": cell_id,
                "rate": -per_layer_rate if kind == "producer" else per_layer_rate,
                "component": "water",
            }
            if kind == "injector" and w.inj_temp_C is not None:
                # Waiwera takes injection enthalpy in J/kg; approximate as
                # cp_water * T (cp ~= 4186 J/(kg*K) for liquid water).
                entry["enthalpy"] = 4186.0 * w.inj_temp_C
            sources.append(entry)
    return sources


def _initial_conditions(grid: GridSpec, scenario: Scenario) -> dict:
    """Return the Waiwera 'initial' block.

    For two-phase scenarios (initial_steam_saturation > 0) we set per-cell
    primary variables. For single-phase liquid we use a global pressure +
    temperature pair.
    """
    if scenario.initial_steam_saturation > 0.0:
        T_C = initial_temperature_C(grid)
        P_Pa = initial_pressure_Pa(grid)
        # Primary vars for two-phase 'we' EOS: [P, vapor saturation]
        sat_field = np.full_like(T_C, scenario.initial_steam_saturation)
        return {
            "primary": np.stack([P_Pa.ravel(), sat_field.ravel()], axis=1).tolist(),
            "region": 4,
        }
    # Single-phase liquid: [P, T]
    T_C = initial_temperature_C(grid)
    P_Pa = initial_pressure_Pa(grid)
    return {
        "primary": np.stack([P_Pa.ravel(), T_C.ravel()], axis=1).tolist(),
        "region": 1,
    }


def build_deck_doc(
    scenario: Scenario,
    grid: GridSpec,
    wells: WellSet,
    mesh_filename: str = "geoforce_grid.exo",
    eos: str = EOS_DEFAULT,
    timesteps_years: tuple[float, ...] = DEFAULT_TIMESTEPS_YEARS,
) -> dict:
    """Construct the Waiwera JSON document (no I/O)."""
    rock_blocks = _rock_blocks(grid)
    sources = _well_sources(wells)
    initial = _initial_conditions(grid, scenario)

    layers = {
        "caprock": grid.caprock,
        "reservoir": grid.reservoir,
        "basement": grid.basement,
    }
    rock_types = []
    for name, props in layers.items():
        rock_types.append(
            {
                "name": name,
                "permeability": [props.permeability_m2] * 3,
                "porosity": props.porosity,
                "wet_conductivity": props.thermal_conductivity_W_mK,
                "dry_conductivity": props.thermal_conductivity_W_mK * 0.8,
                "density": props.rock_density_kg_m3,
                "specific_heat": props.rock_specific_heat_J_kgK,
                "cells": rock_blocks[name],
            }
        )

    output_times_s = [t * SECONDS_PER_YEAR for t in timesteps_years]
    final_time_s = output_times_s[-1]

    return {
        "title": f"GeoForce v2.0 — {scenario.scenario_id}",
        "thermodynamics": {"name": "iapws", "extrapolate": True},
        "eos": {"name": eos, "primary_variable_names": ["pressure", "vapour_saturation"] if eos == "we" else None},
        "gravity": GRAVITY_M_S2,
        "mesh": {
            "filename": mesh_filename,
            "thickness": DZ_M,
        },
        "rock": {"types": rock_types},
        "initial": initial,
        "boundaries": [
            {
                "primary": [101_325.0, scenario.base_temperature_C - 50.0],
                "region": 1,
                "faces": {"cells": [], "normal": [0, 0, -1]},
            }
        ],
        "source": sources,
        "time": {
            "step": {
                "size": 8.64e4,  # 1 day initial step; Waiwera adapts
                "adapt": {"on": True, "method": "iteration"},
                "maximum": {"size": SECONDS_PER_YEAR},
            },
            "stop": final_time_s,
        },
        "output": {
            "frequency": 0,
            "checkpoint": {"time": output_times_s},
            "filename": f"{scenario.scenario_id}.h5",
            "fields": {
                "fluid": ["temperature", "pressure", "vapour_saturation", "specific_enthalpy", "liquid_density"],
            },
        },
    }


def build_mesh_file(out_dir: Path, mesh_filename: str = "geoforce_grid.exo") -> Path:
    """Write the structured-grid mesh file PyTOUGH/Waiwera will read.

    Uses PyTOUGH's `mulgrid.rectangular` factory. The file is ExodusII-like
    (PyTOUGH writes a `dat` mesh; Waiwera converts internally) — for the
    pilot we write the PyTOUGH `dat` form which Waiwera 1.4+ accepts.
    """
    from mulgrids import mulgrid  # local import; PyTOUGH is heavy
    out_dir.mkdir(parents=True, exist_ok=True)
    geo = mulgrid().rectangular(
        xblocks=[DX_M] * NX,
        yblocks=[DY_M] * NY,
        zblocks=[DZ_M] * NZ,
        atmos_type=2,
    )
    mesh_path = out_dir / mesh_filename
    geo.write(str(mesh_path))
    return mesh_path


def write_deck(
    scenario: Scenario,
    grid: GridSpec,
    wells: WellSet,
    out_dir: Path,
    eos: str = EOS_DEFAULT,
) -> DeckBundle:
    """Render and persist a Waiwera deck (JSON + mesh) to `out_dir`."""
    out_dir = Path(out_dir)
    mesh_filename = "geoforce_grid.dat"
    mesh_path = build_mesh_file(out_dir, mesh_filename)
    doc = build_deck_doc(scenario, grid, wells, mesh_filename=mesh_filename, eos=eos)
    json_path = out_dir / f"{scenario.scenario_id}.json"
    with json_path.open("w") as f:
        json.dump(doc, f, indent=2)
    return DeckBundle(json_doc=doc, mesh_path=mesh_path, json_path=json_path)

"""RFP (Radial Flow Problem) — Waiwera analytical-benchmark deck.

Single-phase liquid radial flow into a point sink in an infinite,
homogeneous, isotropic 2D aquifer. Closed-form solution: Theis (1935).

Block B exit gate: max relative error of Waiwera cell pressures vs the
Theis analytical solution must be <1% at sample radii within the
Theis-window (boundary effects negligible).

Geometry: a wide single-layer Cartesian mesh approximates the infinite
2D aquifer. The producer occupies the center cell. Sample cells lie on
the +x ray of the well center, at offsets large enough that the
discrete Cartesian solution matches the radial one.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

NX_RFP: int = 51
NY_RFP: int = 51
NZ_RFP: int = 1
DX_RFP_M: float = 200.0
DY_RFP_M: float = 200.0
DZ_RFP_M: float = 100.0
WELL_I: int = NX_RFP // 2
WELL_J: int = NY_RFP // 2

RFP_TEMPERATURE_C: float = 80.0
RFP_PRESSURE_PA: float = 5.0e6
RFP_VISCOSITY_PA_S: float = 3.55e-4
RFP_DENSITY_KG_M3: float = 971.8
RFP_TOTAL_COMPRESSIBILITY_1_PA: float = 1.5e-10  # phi*c_w + c_r for water at 80 C
RFP_PERMEABILITY_M2: float = 1.0e-13
RFP_POROSITY: float = 0.10
RFP_MASS_RATE_KG_S: float = -10.0
RFP_DURATION_S: float = 86400.0
SAMPLE_RADIAL_OFFSETS: tuple[int, ...] = (3, 5, 7, 10)


@dataclass(frozen=True)
class TheisParams:
    mass_rate: float
    permeability: float
    viscosity: float
    density: float
    porosity: float
    total_compressibility: float
    thickness: float


@dataclass(frozen=True)
class RfpDeck:
    json_path: Path
    mesh_path: Path
    h5_filename: str
    sample_radii_m: tuple[float, ...]
    sample_cell_ids: tuple[int, ...]
    theis_params: TheisParams
    duration_s: float
    initial_pressure_Pa: float


def _block_index(i: int, j: int, k: int = 0) -> int:
    return (k * NY_RFP + j) * NX_RFP + i


def _build_mesh(out_dir: Path, mesh_filename: str) -> Path:
    from mulgrids import mulgrid
    geo = mulgrid().rectangular(
        xblocks=[DX_RFP_M] * NX_RFP,
        yblocks=[DY_RFP_M] * NY_RFP,
        zblocks=[DZ_RFP_M] * NZ_RFP,
        atmos_type=2,
    )
    mesh_path = out_dir / mesh_filename
    geo.write(str(mesh_path))
    return mesh_path


def build_rfp_deck_doc() -> dict:
    """Pure builder for the Waiwera JSON document — no I/O."""
    n_cells = NX_RFP * NY_RFP * NZ_RFP
    well_cell = _block_index(WELL_I, WELL_J)
    primary = [[RFP_PRESSURE_PA, RFP_TEMPERATURE_C] for _ in range(n_cells)]
    return {
        "title": "GeoForce v2.0 - RFP / Theis benchmark",
        "thermodynamics": {"name": "iapws", "extrapolate": True},
        "eos": {"name": "we", "primary_variable_names": ["pressure", "temperature"]},
        "gravity": 0.0,
        "mesh": {"filename": "rfp_grid.dat", "thickness": DZ_RFP_M},
        "rock": {
            "types": [{
                "name": "rfp_rock",
                "permeability": [RFP_PERMEABILITY_M2] * 3,
                "porosity": RFP_POROSITY,
                "wet_conductivity": 2.0,
                "dry_conductivity": 1.6,
                "density": 2650.0,
                "specific_heat": 1000.0,
                "cells": list(range(n_cells)),
            }]
        },
        "initial": {"primary": primary, "region": 1},
        "source": [{
            "name": "P_central",
            "cell": well_cell,
            "rate": RFP_MASS_RATE_KG_S,
            "component": "water",
        }],
        "time": {
            "step": {
                "size": 60.0,
                "adapt": {"on": True, "method": "iteration"},
                "maximum": {"size": RFP_DURATION_S / 4.0},
            },
            "stop": RFP_DURATION_S,
        },
        "output": {
            "frequency": 0,
            "checkpoint": {"time": [RFP_DURATION_S]},
            "filename": "rfp.h5",
            "fields": {"fluid": ["pressure", "temperature", "liquid_density"]},
        },
    }


def build_rfp_deck(out_dir: Path) -> RfpDeck:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    mesh_path = _build_mesh(out_dir, "rfp_grid.dat")
    doc = build_rfp_deck_doc()
    json_path = out_dir / "rfp.json"
    with json_path.open("w") as f:
        json.dump(doc, f, indent=2)

    sample_radii = tuple(d * DX_RFP_M for d in SAMPLE_RADIAL_OFFSETS)
    sample_cells = tuple(_block_index(WELL_I + d, WELL_J) for d in SAMPLE_RADIAL_OFFSETS)
    return RfpDeck(
        json_path=json_path,
        mesh_path=mesh_path,
        h5_filename="rfp.h5",
        sample_radii_m=sample_radii,
        sample_cell_ids=sample_cells,
        theis_params=TheisParams(
            mass_rate=RFP_MASS_RATE_KG_S,
            permeability=RFP_PERMEABILITY_M2,
            viscosity=RFP_VISCOSITY_PA_S,
            density=RFP_DENSITY_KG_M3,
            porosity=RFP_POROSITY,
            total_compressibility=RFP_TOTAL_COMPRESSIBILITY_1_PA,
            thickness=DZ_RFP_M,
        ),
        duration_s=RFP_DURATION_S,
        initial_pressure_Pa=RFP_PRESSURE_PA,
    )


def run_waiwera_rfp(
    deck: RfpDeck,
    *,
    work_dir: Path,
    waiwera_bin: Path,
    ld_library_path: str,
    timeout_s: float = 600.0,
) -> subprocess.CompletedProcess:
    """Invoke Waiwera on the RFP deck. Caller owns environment setup."""
    env = {**os.environ, "LD_LIBRARY_PATH": ld_library_path}
    return subprocess.run(
        [str(waiwera_bin), str(deck.json_path)],
        cwd=str(work_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )


def parse_rfp_output(h5_path: Path, deck: RfpDeck) -> list[tuple[float, float, float]]:
    """Return [(radius_m, time_s, pressure_Pa), ...] at the final checkpoint."""
    import h5py
    with h5py.File(str(h5_path), "r") as f:
        pressure = np.asarray(f["cell_fields"]["fluid_pressure"])
        time = np.asarray(f["time"])
    last_t = float(time[-1])
    last_p = pressure[-1]
    return [
        (float(r), last_t, float(last_p[c]))
        for r, c in zip(deck.sample_radii_m, deck.sample_cell_ids)
    ]


def compare_to_theis(
    samples: list[tuple[float, float, float]],
    deck: RfpDeck,
) -> list[tuple[float, float, float, float, float]]:
    """Return [(r, t, p_num_Pa, p_ana_Pa, rel_err_on_dp), ...]."""
    from solver.benchmarks.theis import theis_pressure_change

    p0 = deck.initial_pressure_Pa
    out = []
    for r, t, p_num in samples:
        delta_p_ana = float(theis_pressure_change(
            r=r, t=t,
            mass_rate=deck.theis_params.mass_rate,
            permeability=deck.theis_params.permeability,
            viscosity=deck.theis_params.viscosity,
            density=deck.theis_params.density,
            porosity=deck.theis_params.porosity,
            total_compressibility=deck.theis_params.total_compressibility,
            thickness=deck.theis_params.thickness,
        ))
        p_ana = p0 + delta_p_ana
        delta_p_num = p_num - p0
        rel_err = abs(delta_p_num - delta_p_ana) / abs(delta_p_ana)
        out.append((r, t, p_num, p_ana, rel_err))
    return out

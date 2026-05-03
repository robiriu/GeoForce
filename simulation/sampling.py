"""Latin Hypercube sampler over the 12-D scenario space.

Reads `simulation/scenarios_v2.yaml` and produces N scenario dicts ready
for `simulation/grid.py` + `simulation/wells.py` to consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from scipy.stats import qmc

from simulation.grid import LayerProps

SCENARIO_SPEC_PATH = Path(__file__).resolve().parent / "scenarios_v2.yaml"


@dataclass(frozen=True)
class Scenario:
    """One LHS-sampled scenario."""

    scenario_id: str
    base_temperature_C: float
    base_pressure_bar: float
    log10_permeability_m2: float
    porosity: float
    reservoir_top_depth_m: float
    heat_source_depth_m: float
    injection_rate_kg_s: float
    production_rate_kg_s: float
    n_production_wells: int
    n_injection_wells: int
    rock_thermal_conductivity_W_mK: float
    initial_steam_saturation: float

    @property
    def reservoir_props(self) -> LayerProps:
        return LayerProps(
            permeability_m2=10.0 ** self.log10_permeability_m2,
            porosity=self.porosity,
            thermal_conductivity_W_mK=self.rock_thermal_conductivity_W_mK,
        )

    @property
    def injection_temp_C(self) -> float:
        # Reinjection of cooled brine; engineering convention is
        # ~80–120 C below reservoir target. Use 100 C below, clipped.
        return max(40.0, self.base_temperature_C - 100.0)


def load_spec(path: Path = SCENARIO_SPEC_PATH) -> dict[str, Any]:
    with path.open() as f:
        return yaml.safe_load(f)


def _ordered_dim_names(spec: dict[str, Any]) -> list[str]:
    return list(spec["dimensions"].keys())


def sample(n: int, seed: int = 0, spec: dict[str, Any] | None = None) -> list[Scenario]:
    """Draw N scenarios via Latin Hypercube Sampling."""
    if spec is None:
        spec = load_spec()
    dims = spec["dimensions"]
    names = _ordered_dim_names(spec)
    sampler = qmc.LatinHypercube(d=len(names), seed=seed)
    unit = sampler.random(n=n)  # shape (n, d), uniform on [0, 1]^d

    lows = np.array([dims[k]["min"] for k in names], dtype=float)
    highs = np.array([dims[k]["max"] for k in names], dtype=float)
    raw = qmc.scale(unit, lows, highs)

    out: list[Scenario] = []
    for s_idx in range(n):
        row = {names[d]: raw[s_idx, d] for d in range(len(names))}
        for d_name, d_spec in dims.items():
            if d_spec.get("integer"):
                row[d_name] = int(round(row[d_name]))
        out.append(
            Scenario(
                scenario_id=f"sc_{s_idx:04d}",
                base_temperature_C=row["base_temperature_C"],
                base_pressure_bar=row["base_pressure_bar"],
                log10_permeability_m2=row["log10_permeability_m2"],
                porosity=row["porosity"],
                reservoir_top_depth_m=row["reservoir_top_depth_m"],
                heat_source_depth_m=row["heat_source_depth_m"],
                injection_rate_kg_s=row["injection_rate_kg_s"],
                production_rate_kg_s=row["production_rate_kg_s"],
                n_production_wells=row["n_production_wells"],
                n_injection_wells=row["n_injection_wells"],
                rock_thermal_conductivity_W_mK=row["rock_thermal_conductivity_W_mK"],
                initial_steam_saturation=row["initial_steam_saturation"],
            )
        )
    return out

"""Loader for the NREL Open-Source Reservoir (OSR) dataset.

OSR is a CMG-simulated 102-scenario benchmark derived from Brady Hot
Springs (Nevada). Each .xlsx file is one scenario containing 241 monthly
timesteps × 30 well measurements (4 injectors + 6 producers; mass flow,
bottom-hole pressure, bottom-hole temperature) plus an "Obj Func" column
with the cumulative-energy objective at the final step.

Reference:
    Duplyakin, D., Beckers, K. F., Siler, D. L., Martin, M. J.,
    Johnston, H. E. (2022). Modeling Subsurface Performance of a
    Geothermal Reservoir Using Machine Learning. Energies 15(3), 967.
    https://www.mdpi.com/1996-1073/15/3/967

Upstream repo (BSD-3): NREL/geothermal_osr.

Note for v2.0: Brady is a well-time-series benchmark, not a 2D field
benchmark. The v1.1 ReservoirCNN cannot be evaluated on Brady directly
(structurally different I/O). Brady becomes the Phase-5 validation target
for the v2.0 3D U-Net once it produces well outputs as a by-product of
voxel fields (see PLAN-V2 §2 and PROGRESS §1A).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "brady" / "data" / "OpenSourceReservoir-CMG"

N_INJECTORS = 4
N_PRODUCERS = 6
N_TIMESTEPS = 241  # monthly, 2020-01-01 → 2040-01-01

# Column groups in the source xlsx (CMOST_Output sheet).
INJ_FLOW_COLS = [f"I{i}_Mass_Flow_Rate (kg/day)" for i in range(1, N_INJECTORS + 1)]
INJ_BHP_COLS = [f"I{i}_Bottom-Hole_Pressure (kPa)" for i in range(1, N_INJECTORS + 1)]
INJ_BHT_COLS = [f"I{i}_Bottom-Hole_Temperature (C)" for i in range(1, N_INJECTORS + 1)]
PROD_FLOW_COLS = [f"P{i}_Mass_Flow_Rate (kg/day)" for i in range(1, N_PRODUCERS + 1)]
PROD_BHP_COLS = [f"P{i}_Bottom-Hole_Pressure (kPa)" for i in range(1, N_PRODUCERS + 1)]
PROD_BHT_COLS = [f"P{i}_Bottom-Hole_Temperature (C)" for i in range(1, N_PRODUCERS + 1)]


@dataclass
class BradyScenario:
    """One OSR scenario parsed into clean numpy arrays.

    Inputs (controllable by the operator):
        injector_mass_flow: (T, 4) kg/day

    Outputs (predicted by any model):
        producer_mass_flow: (T, 6) kg/day
        injector_bhp:       (T, 4) kPa
        producer_bhp:       (T, 6) kPa
        injector_bht:       (T, 4) deg C
        producer_bht:       (T, 6) deg C

    The Obj Func column from the xlsx is preserved as ``obj_func`` (only
    populated at the final step in the source data).
    """

    scenario_id: str
    dates: pd.DatetimeIndex
    injector_mass_flow: np.ndarray
    producer_mass_flow: np.ndarray
    injector_bhp: np.ndarray
    producer_bhp: np.ndarray
    injector_bht: np.ndarray
    producer_bht: np.ndarray
    obj_func: np.ndarray

    @property
    def n_timesteps(self) -> int:
        return len(self.dates)


def load_scenario(path: Path | str) -> BradyScenario:
    """Parse one OSR_*.xlsx file into a BradyScenario."""
    path = Path(path)
    df = pd.read_excel(path, sheet_name="CMOST_Output")
    if "Date" not in df.columns:
        raise ValueError(f"{path.name}: missing 'Date' column")
    dates = pd.to_datetime(df["Date"])
    return BradyScenario(
        scenario_id=path.stem,
        dates=pd.DatetimeIndex(dates),
        injector_mass_flow=df[INJ_FLOW_COLS].to_numpy(dtype=np.float64),
        producer_mass_flow=df[PROD_FLOW_COLS].to_numpy(dtype=np.float64),
        injector_bhp=df[INJ_BHP_COLS].to_numpy(dtype=np.float64),
        producer_bhp=df[PROD_BHP_COLS].to_numpy(dtype=np.float64),
        injector_bht=df[INJ_BHT_COLS].to_numpy(dtype=np.float64),
        producer_bht=df[PROD_BHT_COLS].to_numpy(dtype=np.float64),
        obj_func=df["Obj Func"].to_numpy(dtype=np.float64),
    )


def load_all(data_dir: Path | str = DATA_DIR) -> list[BradyScenario]:
    """Load every OSR_*.xlsx in data_dir, sorted by scenario_id.

    Returns a list of BradyScenario objects. Files that fail to parse are
    skipped with a warning printed to stderr; the caller is responsible
    for asserting the count matches the Phase 1 exit gate (≥ 95/101 +
    holdout).
    """
    import sys

    data_dir = Path(data_dir)
    paths = sorted(data_dir.glob("OSR_*.xlsx"))
    out: list[BradyScenario] = []
    for p in paths:
        try:
            out.append(load_scenario(p))
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[brady] failed to parse {p.name}: {exc}\n")
    return out


def stack(scenarios: list[BradyScenario]) -> dict[str, np.ndarray]:
    """Stack a list of scenarios into batched arrays for ML use.

    Returns a dict with shape ``(N, T, k)`` arrays where N=len(scenarios),
    T=N_TIMESTEPS, k=4 for injectors, k=6 for producers. Skips any
    scenario whose ``n_timesteps != N_TIMESTEPS``.
    """
    keep = [s for s in scenarios if s.n_timesteps == N_TIMESTEPS]
    if len(keep) < len(scenarios):
        import sys

        sys.stderr.write(
            f"[brady] dropped {len(scenarios) - len(keep)} scenarios with non-standard length\n"
        )
    return {
        "scenario_ids": np.array([s.scenario_id for s in keep]),
        "injector_mass_flow": np.stack([s.injector_mass_flow for s in keep]),
        "producer_mass_flow": np.stack([s.producer_mass_flow for s in keep]),
        "injector_bhp": np.stack([s.injector_bhp for s in keep]),
        "producer_bhp": np.stack([s.producer_bhp for s in keep]),
        "injector_bht": np.stack([s.injector_bht for s in keep]),
        "producer_bht": np.stack([s.producer_bht for s in keep]),
    }

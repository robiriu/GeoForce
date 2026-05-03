"""Smoke tests for the NREL OSR (Brady) loader.

Skips automatically if the data/brady submodule was not cloned.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from data.brady_loader import (
    DATA_DIR,
    N_INJECTORS,
    N_PRODUCERS,
    N_TIMESTEPS,
    load_all,
    load_scenario,
    stack,
)

pytestmark = pytest.mark.skipif(
    not DATA_DIR.is_dir() or not list(DATA_DIR.glob("OSR_*.xlsx")),
    reason="data/brady not cloned — run: cd data && git clone https://github.com/NREL/geothermal_osr brady",
)


def test_load_one_scenario() -> None:
    paths = sorted(DATA_DIR.glob("OSR_*.xlsx"))
    assert paths, "no OSR_*.xlsx files found"
    s = load_scenario(paths[1])  # paths[0] is the daily-granularity holdout
    assert s.scenario_id.startswith("OSR_")
    assert s.injector_mass_flow.shape == (s.n_timesteps, N_INJECTORS)
    assert s.producer_mass_flow.shape == (s.n_timesteps, N_PRODUCERS)
    assert np.all(np.isfinite(s.injector_mass_flow))
    assert np.all(s.producer_bht > 0)  # absolute temperatures in C, post-injection


def test_phase1_exit_gate_count() -> None:
    """Exit gate: at least 95 scenarios must parse and stack at the
    standard length so v2.0 training has consistent tensors.
    """
    scenarios = load_all()
    assert len(scenarios) >= 95, f"only {len(scenarios)} parsed (Phase 1 gate: ≥95)"
    batch = stack(scenarios)
    assert batch["injector_mass_flow"].shape == (
        batch["injector_mass_flow"].shape[0],
        N_TIMESTEPS,
        N_INJECTORS,
    )
    assert batch["injector_mass_flow"].shape[0] >= 95

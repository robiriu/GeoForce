"""Theis benchmark — the Day-1 GO/NO-GO gate for GeoForce-Solver's pressure solver.

Runs an implicit single-phase pressure transient on a 2D (x, y) grid with a
single injection well and compares the simulated pressure buildup at several
radial distances to the analytical Theis solution.

Acceptance: mean relative error < 5% across the sampled (r, t) points within
the Theis validity window (u >= ~0.03 so W(u) is well-behaved and boundary
effects are not yet felt).
"""

from __future__ import annotations

import numpy as np
import pytest

from solver.benchmarks.theis import theis_pressure_change
from solver.darcy import run_pressure_transient
from solver.grid import Grid
from solver.properties import WaterProperties


@pytest.fixture(scope="module")
def scenario():
    """Reference Theis scenario; small k slows diffusion, keeps domain ~infinite."""
    nx, ny = 64, 64
    Lx, Ly = 1000.0, 1000.0  # 1 km square, 15.625 m cells
    grid = Grid(nx=nx, ny=ny, dx=Lx / nx, dy=Ly / ny)

    props = WaterProperties.at_reference(t_c=100.0, p_pa=1.0e7)
    c_rock = 1.0e-9  # 1/Pa
    c_t = props.c_f + c_rock

    scenario = {
        "grid": grid,
        "permeability": 1.0e-13,  # m^2 — reservoir-like; fast enough diffusion
        "porosity": 0.15,
        "mu": props.mu,
        "rho": props.rho,
        "c_t": c_t,
        "mass_rate": 0.01,  # kg/s injected at center
        "well_i": nx // 2,
        "well_j": ny // 2,
        "p_init": 1.0e7,  # 10 MPa baseline
        "dt": 25.0,  # s — small enough to keep temporal error < spatial
        "n_steps": 200,  # total t = 5000 s; sqrt(4*eta*t) ~ 243 m << half-domain 500 m
    }
    return scenario


def _simulate(scenario: dict) -> tuple[np.ndarray, np.ndarray]:
    grid: Grid = scenario["grid"]
    q_vol = np.zeros(grid.shape, dtype=np.float64)
    # Mass rate -> volumetric rate at reference density, placed in the well cell.
    q_vol[scenario["well_i"], scenario["well_j"]] = scenario["mass_rate"] / scenario["rho"]

    p_init = np.full(grid.shape, scenario["p_init"], dtype=np.float64)
    history = run_pressure_transient(
        grid=grid,
        p_initial=p_init,
        permeability=scenario["permeability"],
        porosity=scenario["porosity"],
        total_compressibility=scenario["c_t"],
        mu=scenario["mu"],
        q_vol=q_vol,
        dt=scenario["dt"],
        n_steps=scenario["n_steps"],
    )
    # Time levels 1..n_steps, since step 0 is the initial state.
    times = np.arange(1, scenario["n_steps"] + 1) * scenario["dt"]
    return history, times


def test_theis_pressure_buildup(scenario):
    history, times = _simulate(scenario)
    grid: Grid = scenario["grid"]

    r = grid.radial_distance_from(scenario["well_i"], scenario["well_j"])

    # Sample at r values well away from the well (avoid Peaceman-style mismatch
    # inside 2-3 grid cells) and from the boundary (r << sqrt(4*eta*t_max)).
    dx = grid.dx
    radial_targets_m = np.array([3 * dx, 5 * dx, 7 * dx])  # ~47, 78, 109 m; well inside Theis window

    # Pick cells closest to each target along the +x axis from the well cell.
    i0, j0 = scenario["well_i"], scenario["well_j"]
    sampling_cells = []
    for r_target in radial_targets_m:
        offset = max(1, int(round(r_target / dx)))
        sampling_cells.append((i0 + offset, j0))
    sampled_r = np.array([r[i, j] for i, j in sampling_cells])

    # Sample across times in the second half of the simulation (let transient develop).
    time_idx = [len(times) // 2, len(times) * 3 // 4, len(times) - 1]
    sampled_t = times[time_idx]

    rel_errors = []
    for ti in time_idx:
        t = times[ti]
        for (i, j), rr in zip(sampling_cells, sampled_r, strict=True):
            sim_dp = history[ti + 1, i, j] - scenario["p_init"]
            ana_dp = theis_pressure_change(
                r=rr,
                t=t,
                mass_rate=scenario["mass_rate"],
                permeability=scenario["permeability"],
                viscosity=scenario["mu"],
                density=scenario["rho"],
                porosity=scenario["porosity"],
                total_compressibility=scenario["c_t"],
                thickness=1.0,
            )
            if abs(ana_dp) < 1e-3:
                continue  # skip points where analytical dp is negligible
            rel_err = abs(sim_dp - ana_dp) / abs(ana_dp)
            rel_errors.append(float(rel_err))

    rel_errors = np.array(rel_errors)
    mean_err = float(rel_errors.mean())
    max_err = float(rel_errors.max())

    print(f"\nTheis benchmark: mean_rel_err={mean_err:.4f}, max_rel_err={max_err:.4f}")
    print(f"Sampled r (m): {sampled_r}")
    print(f"Sampled t (s): {sampled_t}")
    assert mean_err < 0.05, f"mean relative error {mean_err:.3%} exceeds 5% threshold"
    assert max_err < 0.10, f"max relative error {max_err:.3%} exceeds 10% tolerance"


def test_transient_is_monotonic_near_well(scenario):
    """Pressure at the well cell should rise monotonically during steady injection."""
    history, _ = _simulate(scenario)
    i, j = scenario["well_i"], scenario["well_j"]
    trace = history[:, i, j]
    diffs = np.diff(trace)
    assert (diffs >= -1.0).all(), "well-cell pressure must not decrease during injection"
    assert trace[-1] > trace[0] + 1e3, "expected non-trivial pressure buildup at the well"

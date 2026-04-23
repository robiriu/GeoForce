"""1D conduction benchmark — Day-1 GO/NO-GO gate for the energy solver.

Configures a 2D grid where all energy flux is along x (y boundaries insulated,
step Dirichlet on the left boundary column) and compares the simulated T(x, t)
to the semi-infinite-slab erfc solution.

Acceptance: mean relative error < 5% across sampled (x, t) pairs inside the
thermal boundary layer (x/2*sqrt(a*t) < ~1.5, so erfc is resolvable).
"""

from __future__ import annotations

import numpy as np
import pytest

from solver.benchmarks.conduction_1d import conduction_step_temperature
from solver.energy import run_temperature_transient
from solver.grid import Grid


@pytest.fixture(scope="module")
def scenario():
    nx, ny = 64, 4
    dx = dy = 1.0  # 1 m cells, 64 m long domain
    grid = Grid(nx=nx, ny=ny, dx=dx, dy=dy)

    # Effective rock + water thermal properties for a liquid-saturated sandstone.
    phi = 0.15
    rho_rock, cp_rock, lam_rock = 2500.0, 1000.0, 2.5
    rho_water, cp_water, lam_water = 958.0, 4217.0, 0.68

    rho_cp_eff = (1.0 - phi) * rho_rock * cp_rock + phi * rho_water * cp_water
    lam_eff = (1.0 - phi) * lam_rock + phi * lam_water
    alpha = lam_eff / rho_cp_eff

    return {
        "grid": grid,
        "lam_eff": lam_eff,
        "rho_cp_eff": rho_cp_eff,
        "alpha": alpha,
        "T_initial": 100.0,
        "T_boundary": 200.0,
        "dt": 5.0e5,  # ~5.8 days
        "n_steps": 200,  # total t = 1e8 s ~ 3.2 years
    }


def _simulate(scenario: dict) -> tuple[np.ndarray, np.ndarray]:
    grid: Grid = scenario["grid"]
    t_init = np.full(grid.shape, scenario["T_initial"], dtype=np.float64)
    dirichlet = {(0, j): scenario["T_boundary"] for j in range(grid.ny)}
    history = run_temperature_transient(
        grid=grid,
        t_initial=t_init,
        thermal_conductivity=scenario["lam_eff"],
        volumetric_heat_capacity=scenario["rho_cp_eff"],
        dt=scenario["dt"],
        n_steps=scenario["n_steps"],
        dirichlet=dirichlet,
    )
    times = np.arange(1, scenario["n_steps"] + 1) * scenario["dt"]
    return history, times


def test_conduction_matches_erfc(scenario):
    history, times = _simulate(scenario)
    grid: Grid = scenario["grid"]
    alpha = scenario["alpha"]
    T_i, T_b = scenario["T_initial"], scenario["T_boundary"]

    # Sample cell indices along x (skip the Dirichlet column) at the middle y row.
    sample_i = [3, 6, 10, 15]
    j_mid = grid.ny // 2
    # Cell-centered Dirichlet at cell 0 (center x = 0.5*dx) fixes T(x=0.5*dx, t) = T_b.
    # Mapping to the semi-infinite analytical: shift origin to cell 0's center, so the
    # effective distance for cell i (center (i+0.5)*dx) is (i+0.5)*dx - 0.5*dx = i*dx.
    x_samples = [i * grid.dx for i in sample_i]

    # Sample at four times — second half of run, so transient is developed.
    time_idx = [len(times) // 2, len(times) * 3 // 4, len(times) - 1]

    rel_errors = []
    diagnostics = []
    for ti in time_idx:
        t = times[ti]
        for i, x in zip(sample_i, x_samples, strict=True):
            sim_T = history[ti + 1, i, j_mid]
            ana_T = conduction_step_temperature(
                x=x, t=t, T_initial=T_i, T_boundary=T_b, thermal_diffusivity=alpha,
            )
            dT_sim = sim_T - T_i
            dT_ana = float(ana_T) - T_i
            if abs(dT_ana) < 0.5:  # skip far-field where analytical dT is tiny
                continue
            rel_err = abs(dT_sim - dT_ana) / abs(dT_ana)
            rel_errors.append(float(rel_err))
            diagnostics.append((i, x, t, sim_T, float(ana_T), rel_err))

    mean_err = float(np.mean(rel_errors))
    max_err = float(np.max(rel_errors))
    print(f"\nConduction benchmark: mean_rel_err={mean_err:.4f}, max_rel_err={max_err:.4f}")
    print("  (i, x_m, t_s, sim_T, ana_T, rel_err)")
    for row in diagnostics:
        print(f"   {row[0]:3d}  {row[1]:5.1f}  {row[2]:.2e}  {row[3]:6.2f}  {row[4]:6.2f}  {row[5]:.3%}")

    assert mean_err < 0.05, f"mean error {mean_err:.3%} exceeds 5% threshold"
    assert max_err < 0.10, f"max error {max_err:.3%} exceeds 10% tolerance"


def test_dirichlet_boundary_holds(scenario):
    history, _ = _simulate(scenario)
    # The Dirichlet column (i=0) must equal T_boundary at every step.
    bdy_col = history[1:, 0, :]  # exclude initial state
    assert np.allclose(bdy_col, scenario["T_boundary"], atol=1e-6)


def test_far_field_remains_at_initial(scenario):
    """At t far below the boundary-to-far-wall diffusion time, the far end should be unchanged."""
    history, times = _simulate(scenario)
    grid: Grid = scenario["grid"]
    # Distance to opposite wall: (nx - 1) * dx ~ 63 m
    # sqrt(4*alpha*t_max) should be much less than this.
    x_far = (grid.nx - 1) * grid.dx
    penetration = float(2.0 * np.sqrt(scenario["alpha"] * times[-1]))
    assert penetration < x_far * 0.4, (
        f"penetration depth {penetration:.1f} m invalidates the semi-infinite assumption"
    )
    # Far-wall temperature rise must be small relative to the step.
    dT_far = history[-1, -1, grid.ny // 2] - scenario["T_initial"]
    assert abs(dT_far) < 1.0, f"far wall T drifted by {dT_far:.2f} C (semi-infinite violated)"

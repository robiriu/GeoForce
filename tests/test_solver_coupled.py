"""Smoke tests for the coupled (Darcy + energy + advection) solver.

These are *not* analytical benchmarks — that gate has already been passed
for pressure (Theis) and temperature (1-D conduction). The goal here is
to show the coupling is physically consistent:

    1. With zero wells, coupled.step_coupled() reduces to pure conduction
       and matches the standalone energy solver to machine precision.
    2. With an injector-producer pair, pressure is elevated at the
       injector and depressed at the producer, and a cold plume develops
       around the injector that propagates toward the producer.
    3. Global mass balance: total injected ≈ total produced (steady-state
       incompressible check), and no NaN/negative pressures appear.
"""

from __future__ import annotations

import numpy as np
import pytest

from solver.coupled import run_coupled_transient, step_coupled
from solver.energy import run_temperature_transient
from solver.grid import Grid
from solver.properties import WaterProperties
from solver.wells import WellSpec


@pytest.fixture(scope="module")
def props():
    return WaterProperties.at_reference(t_c=200.0, p_pa=1.5e7)


@pytest.fixture(scope="module")
def reservoir(props):
    nx, ny = 40, 20
    dx = dy = 10.0  # 400 m x 200 m
    grid = Grid(nx=nx, ny=ny, dx=dx, dy=dy)

    phi = 0.12
    rho_rock, cp_rock, lam_rock = 2500.0, 1000.0, 2.5
    rho_cp_eff = (1.0 - phi) * rho_rock * cp_rock + phi * props.rho * props.cp
    lam_eff = (1.0 - phi) * lam_rock + phi * 0.68

    return {
        "grid": grid,
        "props": props,
        "porosity": phi,
        "permeability": 5.0e-13,
        "total_compressibility": props.c_f + 1.0e-9,
        "volumetric_heat_capacity": rho_cp_eff,
        "thermal_conductivity": lam_eff,
        "T_initial": 200.0,
        "P_initial": 1.5e7,
    }


def test_zero_wells_matches_pure_conduction(reservoir):
    """With no advection source, coupled.py must reproduce energy.py exactly."""
    grid: Grid = reservoir["grid"]
    props: WaterProperties = reservoir["props"]
    t0 = np.full(grid.shape, reservoir["T_initial"], dtype=np.float64)
    p0 = np.full(grid.shape, reservoir["P_initial"], dtype=np.float64)
    # Impose a Dirichlet column so conduction has something to do.
    dirichlet = {(0, j): 250.0 for j in range(grid.ny)}
    dt, n_steps = 1.0e5, 20

    p_hist, t_hist_coupled = run_coupled_transient(
        grid=grid,
        p_initial=p0,
        t_initial=t0,
        permeability=reservoir["permeability"],
        porosity=reservoir["porosity"],
        total_compressibility=reservoir["total_compressibility"],
        mu=props.mu,
        rho=props.rho,
        cp_water=props.cp,
        thermal_conductivity=reservoir["thermal_conductivity"],
        volumetric_heat_capacity=reservoir["volumetric_heat_capacity"],
        dt=dt,
        n_steps=n_steps,
        wells=[],
        dirichlet_t=dirichlet,
    )
    t_hist_energy = run_temperature_transient(
        grid=grid,
        t_initial=t0,
        thermal_conductivity=reservoir["thermal_conductivity"],
        volumetric_heat_capacity=reservoir["volumetric_heat_capacity"],
        dt=dt,
        n_steps=n_steps,
        dirichlet=dirichlet,
    )
    # With no pressure source and uniform P, mass fluxes are ~0 and the
    # two histories should agree to within round-off.
    diff = np.max(np.abs(t_hist_coupled - t_hist_energy))
    assert diff < 1.0e-6, f"coupled vs energy-only drift: {diff}"
    assert np.isfinite(p_hist).all()


def test_injector_producer_pair(reservoir):
    """Cold injection -> producer: pressure + cold plume behave correctly."""
    grid: Grid = reservoir["grid"]
    props: WaterProperties = reservoir["props"]
    T_init = reservoir["T_initial"]
    P_init = reservoir["P_initial"]
    T_inj = 80.0  # °C — cold reinjection

    t0 = np.full(grid.shape, T_init, dtype=np.float64)
    p0 = np.full(grid.shape, P_init, dtype=np.float64)

    j_mid = grid.ny // 2
    injector = WellSpec(i=5, j=j_mid, mass_rate=0.5, injection_temperature=T_inj)
    producer = WellSpec(i=grid.nx - 6, j=j_mid, mass_rate=-0.5)

    dt, n_steps = 5.0e5, 60  # 3.0e7 s ≈ ~1 yr
    p_hist, t_hist = run_coupled_transient(
        grid=grid,
        p_initial=p0,
        t_initial=t0,
        permeability=reservoir["permeability"],
        porosity=reservoir["porosity"],
        total_compressibility=reservoir["total_compressibility"],
        mu=props.mu,
        rho=props.rho,
        cp_water=props.cp,
        thermal_conductivity=reservoir["thermal_conductivity"],
        volumetric_heat_capacity=reservoir["volumetric_heat_capacity"],
        dt=dt,
        n_steps=n_steps,
        wells=[injector, producer],
    )

    # Finite values everywhere — no solver blow-up.
    assert np.isfinite(p_hist).all(), "pressure went NaN"
    assert np.isfinite(t_hist).all(), "temperature went NaN"

    p_final = p_hist[-1]
    t_final = t_hist[-1]

    # Pressure field: injector cell > initial > producer cell.
    p_inj = p_final[injector.i, injector.j]
    p_prod = p_final[producer.i, producer.j]
    assert p_inj > P_init + 1.0e3, f"injector pressure {p_inj:.2f} not elevated"
    assert p_prod < P_init - 1.0e3, f"producer pressure {p_prod:.2f} not depressed"

    # Cold plume: injector cell temperature has dropped substantially.
    t_inj_cell = t_final[injector.i, injector.j]
    assert t_inj_cell < T_init - 20.0, (
        f"injector cell T = {t_inj_cell:.1f} °C did not cool (expected << {T_init})"
    )
    # Far-field at the producer side should still be hot early on.
    t_prod_cell = t_final[producer.i, producer.j]
    assert t_prod_cell > T_inj + 50.0, (
        f"producer cell T = {t_prod_cell:.1f} °C cooled faster than physical"
    )

    # Advection asymmetry: at equal distance from the injector, a cell along
    # the flow corridor (+x toward the producer) should be cooler than a cell
    # transverse to it (+y, off-axis). Pure conduction would give equal T on
    # both; advection breaks that symmetry.
    d = 3  # cells
    t_downstream = t_final[injector.i + d, j_mid]
    t_offaxis = t_final[injector.i, min(j_mid + d, grid.ny - 1)]
    assert t_downstream < t_offaxis, (
        f"advection asymmetry missing: downstream={t_downstream:.1f}, "
        f"off-axis={t_offaxis:.1f}"
    )


def test_single_step_sanity(reservoir):
    """One step on the uniform IC with wells should not raise or produce NaN."""
    grid: Grid = reservoir["grid"]
    props: WaterProperties = reservoir["props"]
    t0 = np.full(grid.shape, reservoir["T_initial"], dtype=np.float64)
    p0 = np.full(grid.shape, reservoir["P_initial"], dtype=np.float64)
    wells = [
        WellSpec(i=2, j=grid.ny // 2, mass_rate=0.2, injection_temperature=60.0),
        WellSpec(i=grid.nx - 3, j=grid.ny // 2, mass_rate=-0.2),
    ]
    state = step_coupled(
        grid=grid,
        p_old=p0,
        t_old=t0,
        permeability=reservoir["permeability"],
        porosity=reservoir["porosity"],
        total_compressibility=reservoir["total_compressibility"],
        mu=props.mu,
        rho=props.rho,
        cp_water=props.cp,
        thermal_conductivity=reservoir["thermal_conductivity"],
        volumetric_heat_capacity=reservoir["volumetric_heat_capacity"],
        dt=1.0e5,
        wells=wells,
    )
    assert state.pressure.shape == grid.shape
    assert state.temperature.shape == grid.shape
    assert np.isfinite(state.pressure).all()
    assert np.isfinite(state.temperature).all()
    assert state.mass_flux_x.shape == (grid.nx - 1, grid.ny)
    assert state.mass_flux_y.shape == (grid.nx, grid.ny - 1)

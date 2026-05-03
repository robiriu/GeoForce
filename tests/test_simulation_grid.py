"""Smoke + invariant tests for simulation/grid.py."""

from __future__ import annotations

import numpy as np

from simulation.grid import (
    ATM_PRESSURE_PA,
    DX_M,
    DY_M,
    DZ_M,
    LX_M,
    LY_M,
    LZ_M,
    NX,
    NY,
    NZ,
    LayerProps,
    build_grid,
    initial_pressure_Pa,
    initial_temperature_C,
    per_cell_properties,
)


def _grid():
    cap = LayerProps(permeability_m2=1e-17, porosity=0.02, thermal_conductivity_W_mK=2.0)
    res = LayerProps(permeability_m2=1e-14, porosity=0.10, thermal_conductivity_W_mK=2.5)
    bas = LayerProps(permeability_m2=1e-18, porosity=0.01, thermal_conductivity_W_mK=2.5)
    return build_grid(cap, res, bas)


def test_grid_shape() -> None:
    g = _grid()
    assert g.cell_centers_xyz.shape == (NX, NY, NZ, 3)
    assert g.layer_index.shape == (NZ,)


def test_cell_dimensions() -> None:
    assert NX * DX_M == LX_M
    assert NY * DY_M == LY_M
    assert NZ * DZ_M == LZ_M


def test_layer_assignment_partitions_z() -> None:
    g = _grid()
    counts = np.bincount(g.layer_index, minlength=3)
    assert counts.tolist() == [2, 6, 2]


def test_initial_temperature_monotone_in_z() -> None:
    g = _grid()
    T = initial_temperature_C(g)
    # bottom layer hotter than top layer everywhere
    assert np.all(T[:, :, -1] > T[:, :, 0])


def test_initial_pressure_increases_with_depth_and_starts_atmospheric() -> None:
    g = _grid()
    P = initial_pressure_Pa(g)
    # surface-most cell ~atmospheric + half-cell of fluid head
    assert P[0, 0, 0] > ATM_PRESSURE_PA
    assert P[0, 0, 0] < ATM_PRESSURE_PA + 5.0e6
    assert np.all(P[:, :, -1] > P[:, :, 0])


def test_per_cell_properties_match_layers() -> None:
    g = _grid()
    props = per_cell_properties(g)
    # caprock cells have caprock perm
    assert np.allclose(props["permeability_m2"][:, :, 0], 1e-17)
    # reservoir cells
    assert np.allclose(props["permeability_m2"][:, :, 4], 1e-14)
    # basement cells
    assert np.allclose(props["permeability_m2"][:, :, -1], 1e-18)

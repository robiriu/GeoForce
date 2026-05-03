"""32x32x10 structured grid with caprock / reservoir / basement layering.

Domain: 2 km x 2 km x 2 km, oriented with z increasing downward (z=0 at
surface, z=2000 m at base). Cells are uniform 62.5 m horizontally and
200 m vertically.

Layering (along z, top -> bottom):
  - caprock:    indices  0..1   ( 2 layers, 0..400 m)
  - reservoir:  indices  2..7   ( 6 layers, 400..1600 m)
  - basement:   indices  8..9   ( 2 layers, 1600..2000 m)

Initial conditions:
  - Hydrostatic pressure with surface boundary at atmospheric (101325 Pa).
  - Geothermal gradient: T_surface + grad_C_per_km * depth_km.
  - Per-layer overrides for permeability, porosity, thermal conductivity.

This module produces only Python data structures. The Waiwera input deck
templating that consumes this lives in `simulation/deck.py` (Block C).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

NX: int = 32
NY: int = 32
NZ: int = 10
LX_M: float = 2000.0
LY_M: float = 2000.0
LZ_M: float = 2000.0

DX_M: float = LX_M / NX
DY_M: float = LY_M / NY
DZ_M: float = LZ_M / NZ

CAPROCK_K: tuple[int, int] = (0, 2)      # half-open [start, stop)
RESERVOIR_K: tuple[int, int] = (2, 8)
BASEMENT_K: tuple[int, int] = (8, 10)

ATM_PRESSURE_PA: float = 101_325.0
GRAVITY_M_S2: float = 9.80665


@dataclass(frozen=True)
class LayerProps:
    """Per-layer rock properties."""

    permeability_m2: float
    porosity: float
    thermal_conductivity_W_mK: float
    rock_density_kg_m3: float = 2650.0
    rock_specific_heat_J_kgK: float = 1000.0


@dataclass(frozen=True)
class GridSpec:
    """Full 3D grid + IC specification."""

    caprock: LayerProps
    reservoir: LayerProps
    basement: LayerProps
    surface_temp_C: float = 25.0
    geothermal_gradient_C_per_km: float = 100.0
    cell_centers_xyz: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0))
    layer_index: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0, dtype=np.int8))


def _layer_index_array() -> np.ndarray:
    """Return (NZ,) array of layer codes: 0=caprock, 1=reservoir, 2=basement."""
    out = np.empty(NZ, dtype=np.int8)
    out[CAPROCK_K[0]:CAPROCK_K[1]] = 0
    out[RESERVOIR_K[0]:RESERVOIR_K[1]] = 1
    out[BASEMENT_K[0]:BASEMENT_K[1]] = 2
    return out


def _cell_centers() -> np.ndarray:
    """Return (NX, NY, NZ, 3) array of cell-center coordinates in meters.

    z is depth below surface (positive downward).
    """
    xs = (np.arange(NX) + 0.5) * DX_M
    ys = (np.arange(NY) + 0.5) * DY_M
    zs = (np.arange(NZ) + 0.5) * DZ_M
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    return np.stack([X, Y, Z], axis=-1)


def build_grid(
    caprock: LayerProps,
    reservoir: LayerProps,
    basement: LayerProps,
    surface_temp_C: float = 25.0,
    geothermal_gradient_C_per_km: float = 100.0,
) -> GridSpec:
    """Build a populated GridSpec."""
    return GridSpec(
        caprock=caprock,
        reservoir=reservoir,
        basement=basement,
        surface_temp_C=surface_temp_C,
        geothermal_gradient_C_per_km=geothermal_gradient_C_per_km,
        cell_centers_xyz=_cell_centers(),
        layer_index=_layer_index_array(),
    )


def initial_temperature_C(grid: GridSpec) -> np.ndarray:
    """Return (NX, NY, NZ) initial temperature in C from geothermal gradient."""
    z = grid.cell_centers_xyz[..., 2]
    return grid.surface_temp_C + grid.geothermal_gradient_C_per_km * (z / 1000.0)


def initial_pressure_Pa(grid: GridSpec, fluid_density_kg_m3: float = 970.0) -> np.ndarray:
    """Return (NX, NY, NZ) hydrostatic initial pressure in Pa.

    Uses a constant fluid density (default 970 kg/m^3, ~150 C liquid water);
    Waiwera will iterate this to a self-consistent profile during steady-state
    initialization. This is the seed.
    """
    z = grid.cell_centers_xyz[..., 2]
    return ATM_PRESSURE_PA + fluid_density_kg_m3 * GRAVITY_M_S2 * z


def per_cell_properties(grid: GridSpec) -> dict[str, np.ndarray]:
    """Return per-cell (NX,NY,NZ) arrays of rock properties keyed by name."""
    layers = (grid.caprock, grid.reservoir, grid.basement)
    nx, ny, nz = NX, NY, NZ
    perm = np.empty((nx, ny, nz))
    poro = np.empty((nx, ny, nz))
    cond = np.empty((nx, ny, nz))
    rho = np.empty((nx, ny, nz))
    cp = np.empty((nx, ny, nz))
    for k in range(nz):
        layer = layers[grid.layer_index[k]]
        perm[:, :, k] = layer.permeability_m2
        poro[:, :, k] = layer.porosity
        cond[:, :, k] = layer.thermal_conductivity_W_mK
        rho[:, :, k] = layer.rock_density_kg_m3
        cp[:, :, k] = layer.rock_specific_heat_J_kgK
    return {
        "permeability_m2": perm,
        "porosity": poro,
        "thermal_conductivity_W_mK": cond,
        "rock_density_kg_m3": rho,
        "rock_specific_heat_J_kgK": cp,
    }

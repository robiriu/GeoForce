"""Pure conduction energy solver (fully-implicit backward-Euler).

Solves, per cell integral:

    V * (rho*cp)_eff * dT/dt = div( lambda_eff * grad T ) + V * q_heat

Advection is deliberately *not* included yet — the Day-1 1D conduction
benchmark only exercises conduction. Advection (coupling to the Darcy flux
from darcy.py) is added by coupled.py for the real geothermal scenarios.

Boundary conditions:
    * All boundaries are no-flow (Neumann zero) by default.
    * Dirichlet conditions are imposed cell-wise via the `dirichlet` mapping.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import spsolve

from .grid import Grid


@dataclass(frozen=True)
class EnergyResult:
    """Output of one implicit energy step."""

    temperature: np.ndarray
    residual_norm: float


def _harmonic_mean(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    denom = a + b
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(denom > 0.0, 2.0 * a * b / denom, 0.0)


def build_thermal_conductance(
    grid: Grid,
    thermal_conductivity: np.ndarray | float,
) -> tuple[np.ndarray, np.ndarray]:
    """Face-wise thermal conductance [W/K]. Harmonic mean of cell lambdas.

    Returns (Cx, Cy) with shapes (nx-1, ny) and (nx, ny-1).
    """
    lam = np.broadcast_to(thermal_conductivity, grid.shape).astype(np.float64)
    lam_x = _harmonic_mean(lam[:-1, :], lam[1:, :])
    lam_y = _harmonic_mean(lam[:, :-1], lam[:, 1:])
    Cx = grid.face_area_x * lam_x / grid.dx
    Cy = grid.face_area_y * lam_y / grid.dy
    return Cx, Cy


def assemble_energy_system(
    grid: Grid,
    *,
    thermal_conductivity: np.ndarray | float,
    volumetric_heat_capacity: np.ndarray | float,
    dt: float,
    t_old: np.ndarray,
    q_heat: np.ndarray,
    dirichlet: dict[tuple[int, int], float] | None = None,
) -> tuple[csr_matrix, np.ndarray]:
    """Assemble (A, b) so that A * T_new = b.

    Args:
        grid: the 2D structured grid.
        thermal_conductivity: per-cell lambda_eff (W/m/K), scalar or (nx, ny).
        volumetric_heat_capacity: per-cell (rho*cp)_eff (J/m^3/K).
        dt: time step (s).
        t_old: previous temperature field (any consistent unit).
        q_heat: volumetric heat source (W/m^3), shape (nx, ny).
        dirichlet: optional mapping {(i, j): T_fixed} enforcing Dirichlet BCs.
    """
    nx, ny = grid.shape
    n = nx * ny
    Cx, Cy = build_thermal_conductance(grid, thermal_conductivity)
    rho_cp = np.broadcast_to(volumetric_heat_capacity, grid.shape).astype(np.float64)
    storage = grid.cell_volume * rho_cp / dt  # J/K per cell per dt

    A = lil_matrix((n, n), dtype=np.float64)
    b = np.zeros(n, dtype=np.float64)

    dirichlet = dirichlet or {}

    for i in range(nx):
        for j in range(ny):
            idx = grid.flat_index(i, j)

            if (i, j) in dirichlet:
                # Dirichlet: identity row, RHS = fixed value.
                A[idx, idx] = 1.0
                b[idx] = dirichlet[(i, j)]
                continue

            diag = storage[i, j]
            if i > 0:
                t = Cx[i - 1, j]
                A[idx, grid.flat_index(i - 1, j)] = -t
                diag += t
            if i < nx - 1:
                t = Cx[i, j]
                A[idx, grid.flat_index(i + 1, j)] = -t
                diag += t
            if j > 0:
                t = Cy[i, j - 1]
                A[idx, grid.flat_index(i, j - 1)] = -t
                diag += t
            if j < ny - 1:
                t = Cy[i, j]
                A[idx, grid.flat_index(i, j + 1)] = -t
                diag += t

            A[idx, idx] = diag
            b[idx] = storage[i, j] * t_old[i, j] + grid.cell_volume * q_heat[i, j]

    return A.tocsr(), b


def step_temperature(
    grid: Grid,
    t_old: np.ndarray,
    *,
    thermal_conductivity: np.ndarray | float,
    volumetric_heat_capacity: np.ndarray | float,
    dt: float,
    q_heat: np.ndarray | None = None,
    dirichlet: dict[tuple[int, int], float] | None = None,
) -> EnergyResult:
    """Advance the temperature field by one implicit backward-Euler step."""
    if q_heat is None:
        q_heat = np.zeros(grid.shape, dtype=np.float64)
    A, b = assemble_energy_system(
        grid=grid,
        thermal_conductivity=thermal_conductivity,
        volumetric_heat_capacity=volumetric_heat_capacity,
        dt=dt,
        t_old=t_old,
        q_heat=q_heat,
        dirichlet=dirichlet,
    )
    t_new_flat = spsolve(A, b)
    t_new = t_new_flat.reshape(grid.shape)
    residual = float(np.linalg.norm(A @ t_new_flat - b))
    return EnergyResult(temperature=t_new, residual_norm=residual)


def run_temperature_transient(
    grid: Grid,
    t_initial: np.ndarray,
    *,
    thermal_conductivity: np.ndarray | float,
    volumetric_heat_capacity: np.ndarray | float,
    dt: float,
    n_steps: int,
    q_heat: np.ndarray | None = None,
    dirichlet: dict[tuple[int, int], float] | None = None,
) -> np.ndarray:
    """Run n_steps of implicit conduction. Returns (n_steps + 1, nx, ny)."""
    history = np.empty((n_steps + 1, grid.nx, grid.ny), dtype=np.float64)
    history[0] = t_initial
    t = t_initial.copy()
    for k in range(n_steps):
        result = step_temperature(
            grid=grid,
            t_old=t,
            thermal_conductivity=thermal_conductivity,
            volumetric_heat_capacity=volumetric_heat_capacity,
            dt=dt,
            q_heat=q_heat,
            dirichlet=dirichlet,
        )
        t = result.temperature
        history[k + 1] = t
    return history

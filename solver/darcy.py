"""Single-phase pressure solver (Darcy + storage), fully-implicit backward-Euler.

Governs liquid water pressure on a 2D structured grid. The linearized
Boussinesq form makes the system linear in P:

    V * phi * c_t * dP/dt = div( (k/mu) * grad P ) * rho + q_mass

which after dividing by rho (treated as the reference-state constant) is

    V * phi * c_t * dP/dt = div( (k/mu) * grad P ) + q_vol

with q_vol the source in m^3/s per cell.

Fully-implicit backward-Euler with a 5-point finite-volume stencil yields
a sparse symmetric-positive-definite linear system solved by scipy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import spsolve

from .grid import Grid


@dataclass(frozen=True)
class DarcyResult:
    """Output of one implicit pressure step."""

    pressure: np.ndarray  # shape (nx, ny), Pa
    residual_norm: float


def _harmonic_mean(a: float | np.ndarray, b: float | np.ndarray) -> np.ndarray | float:
    """Harmonic mean of two (possibly per-cell) permeability values."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    denom = a + b
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(denom > 0.0, 2.0 * a * b / denom, 0.0)


def build_transmissibility(
    grid: Grid,
    permeability: np.ndarray,
    mu: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the (Tx, Ty) arrays of face transmissibilities [m^3 / (Pa s)].

    Tx has shape (nx-1, ny): transmissibility between cells (i, j) and (i+1, j).
    Ty has shape (nx, ny-1): transmissibility between cells (i, j) and (i, j+1).

    T_ij = A_face * k_harmonic / (mu * d_centers)
    """
    k = np.broadcast_to(permeability, (grid.nx, grid.ny)).astype(np.float64)
    k_x = _harmonic_mean(k[:-1, :], k[1:, :])
    k_y = _harmonic_mean(k[:, :-1], k[:, 1:])
    Tx = grid.face_area_x * k_x / (mu * grid.dx)
    Ty = grid.face_area_y * k_y / (mu * grid.dy)
    return Tx, Ty


def assemble_pressure_system(
    grid: Grid,
    permeability: np.ndarray,
    porosity: np.ndarray | float,
    total_compressibility: float,
    mu: float,
    dt: float,
    p_old: np.ndarray,
    q_vol: np.ndarray,
) -> tuple[csr_matrix, np.ndarray]:
    """Assemble (A, b) for the implicit pressure step (A p_new = b).

    Args:
        grid: the 2D structured grid.
        permeability: per-cell absolute permeability [m^2], shape (nx, ny) or scalar.
        porosity: per-cell porosity (dimensionless), same shape or scalar.
        total_compressibility: rock + fluid (1/Pa), treated as constant.
        mu: reference dynamic viscosity (Pa.s).
        dt: time step (s).
        p_old: previous pressure field, shape (nx, ny) in Pa.
        q_vol: volumetric source per cell (m^3/s), shape (nx, ny).
            Positive = injection; negative = production.

    Returns:
        (A, b) with A a scipy csr_matrix of shape (n, n) and b a dense (n,) vector.
    """
    nx, ny = grid.shape
    n = nx * ny
    Tx, Ty = build_transmissibility(grid, permeability, mu)

    phi = np.broadcast_to(porosity, (nx, ny)).astype(np.float64)
    storage = grid.cell_volume * phi * total_compressibility / dt  # shape (nx, ny)

    A = lil_matrix((n, n), dtype=np.float64)
    b = np.zeros(n, dtype=np.float64)

    for i in range(nx):
        for j in range(ny):
            idx = grid.flat_index(i, j)
            diag = storage[i, j]

            # Neighbor (i-1, j)
            if i > 0:
                t = Tx[i - 1, j]
                A[idx, grid.flat_index(i - 1, j)] = -t
                diag += t
            # Neighbor (i+1, j)
            if i < nx - 1:
                t = Tx[i, j]
                A[idx, grid.flat_index(i + 1, j)] = -t
                diag += t
            # Neighbor (i, j-1)
            if j > 0:
                t = Ty[i, j - 1]
                A[idx, grid.flat_index(i, j - 1)] = -t
                diag += t
            # Neighbor (i, j+1)
            if j < ny - 1:
                t = Ty[i, j]
                A[idx, grid.flat_index(i, j + 1)] = -t
                diag += t

            A[idx, idx] = diag
            b[idx] = storage[i, j] * p_old[i, j] + q_vol[i, j]

    return A.tocsr(), b


def step_pressure(
    grid: Grid,
    p_old: np.ndarray,
    *,
    permeability: np.ndarray | float,
    porosity: np.ndarray | float,
    total_compressibility: float,
    mu: float,
    dt: float,
    q_vol: np.ndarray | None = None,
) -> DarcyResult:
    """Advance the pressure field by one implicit backward-Euler step.

    All boundaries are no-flow (Neumann zero). If you need Dirichlet
    boundaries, set a large transmissibility ghost source — but for the
    Theis benchmark no-flow is correct as long as r << domain boundary.
    """
    nx, ny = grid.shape
    if q_vol is None:
        q_vol = np.zeros((nx, ny), dtype=np.float64)

    A, b = assemble_pressure_system(
        grid=grid,
        permeability=permeability,
        porosity=porosity,
        total_compressibility=total_compressibility,
        mu=mu,
        dt=dt,
        p_old=p_old,
        q_vol=q_vol,
    )
    p_new_flat = spsolve(A, b)
    p_new = p_new_flat.reshape((nx, ny))
    residual = float(np.linalg.norm(A @ p_new_flat - b))
    return DarcyResult(pressure=p_new, residual_norm=residual)


def run_pressure_transient(
    grid: Grid,
    p_initial: np.ndarray,
    *,
    permeability: np.ndarray | float,
    porosity: np.ndarray | float,
    total_compressibility: float,
    mu: float,
    q_vol: np.ndarray,
    dt: float,
    n_steps: int,
) -> np.ndarray:
    """Run n_steps of the implicit pressure solver with a fixed source.

    Returns an array of shape (n_steps + 1, nx, ny) with p[0] = p_initial.
    """
    history = np.empty((n_steps + 1, grid.nx, grid.ny), dtype=np.float64)
    history[0] = p_initial
    p = p_initial.copy()
    for k in range(n_steps):
        result = step_pressure(
            grid=grid,
            p_old=p,
            permeability=permeability,
            porosity=porosity,
            total_compressibility=total_compressibility,
            mu=mu,
            dt=dt,
            q_vol=q_vol,
        )
        p = result.pressure
        history[k + 1] = p
    return history

"""Sequential implicit P → T coupling with upwind advection.

Per time step:
    1. Solve Darcy pressure with the well volumetric sources.
    2. Compute face mass fluxes from the new pressure.
    3. Assemble and solve the energy equation with conduction + upwind
       advection + well heat.

Fluid properties (ρ, μ, cp) are held at reference-state constants — this
is the Boussinesq-style linearisation used for numerical stability.
Extending to temperature-dependent ρ(T, P), μ(T) is straightforward but
out of scope for the 48-hour build.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import spsolve

from .darcy import build_transmissibility, step_pressure
from .energy import build_thermal_conductance
from .grid import Grid
from .wells import WellSpec, apply_wells


@dataclass(frozen=True)
class CoupledState:
    """One step of the coupled solver."""

    pressure: np.ndarray  # (nx, ny), Pa
    temperature: np.ndarray  # (nx, ny), same unit as input t_old
    mass_flux_x: np.ndarray  # (nx-1, ny), kg/s, positive in +x
    mass_flux_y: np.ndarray  # (nx, ny-1), kg/s, positive in +y


def compute_mass_flux(
    grid: Grid,
    pressure: np.ndarray,
    permeability: np.ndarray | float,
    mu: float,
    rho: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Face-wise mass flow rate [kg/s] from the Darcy law.

    Sign convention: flux is positive when flow goes from lower index to
    higher index (i → i+1 for x, j → j+1 for y).
    """
    Tx, Ty = build_transmissibility(grid, permeability, mu)
    mx = rho * Tx * (pressure[:-1, :] - pressure[1:, :])
    my = rho * Ty * (pressure[:, :-1] - pressure[:, 1:])
    return mx, my


def assemble_energy_with_advection(
    grid: Grid,
    *,
    thermal_conductivity: np.ndarray | float,
    volumetric_heat_capacity: np.ndarray | float,
    cp_water: float,
    dt: float,
    t_old: np.ndarray,
    mass_flux_x: np.ndarray,
    mass_flux_y: np.ndarray,
    q_heat_inj: np.ndarray,
    m_prod: np.ndarray,
    dirichlet: dict[tuple[int, int], float] | None = None,
) -> tuple[csr_matrix, np.ndarray]:
    """Assemble (A, b) for the implicit conduction + upwind advection step."""
    nx, ny = grid.shape
    n = nx * ny
    Cx, Cy = build_thermal_conductance(grid, thermal_conductivity)
    rho_cp = np.broadcast_to(volumetric_heat_capacity, grid.shape).astype(np.float64)
    storage = grid.cell_volume * rho_cp / dt
    dirichlet = dirichlet or {}

    A = lil_matrix((n, n), dtype=np.float64)
    b = np.zeros(n, dtype=np.float64)

    for i in range(nx):
        for j in range(ny):
            idx = grid.flat_index(i, j)

            if (i, j) in dirichlet:
                A[idx, idx] = 1.0
                b[idx] = dirichlet[(i, j)]
                continue

            diag = storage[i, j]

            # --- Conduction (5-point stencil) ---------------------------------
            if i > 0:
                c = Cx[i - 1, j]
                A[idx, grid.flat_index(i - 1, j)] += -c
                diag += c
            if i < nx - 1:
                c = Cx[i, j]
                A[idx, grid.flat_index(i + 1, j)] += -c
                diag += c
            if j > 0:
                c = Cy[i, j - 1]
                A[idx, grid.flat_index(i, j - 1)] += -c
                diag += c
            if j < ny - 1:
                c = Cy[i, j]
                A[idx, grid.flat_index(i, j + 1)] += -c
                diag += c

            # --- Advection (upwind) -------------------------------------------
            # west face (i-1, j) ↔ (i, j): flow m = mass_flux_x[i-1, j]
            if i > 0:
                m = mass_flux_x[i - 1, j]
                if m >= 0.0:
                    # inflow from (i-1, j) at T_{i-1,j}
                    A[idx, grid.flat_index(i - 1, j)] += -m * cp_water
                else:
                    # outflow to (i-1, j) at T_{i, j}
                    diag += -m * cp_water
            # east face
            if i < nx - 1:
                m = mass_flux_x[i, j]
                if m >= 0.0:
                    diag += m * cp_water
                else:
                    A[idx, grid.flat_index(i + 1, j)] += m * cp_water
            # south face
            if j > 0:
                m = mass_flux_y[i, j - 1]
                if m >= 0.0:
                    A[idx, grid.flat_index(i, j - 1)] += -m * cp_water
                else:
                    diag += -m * cp_water
            # north face
            if j < ny - 1:
                m = mass_flux_y[i, j]
                if m >= 0.0:
                    diag += m * cp_water
                else:
                    A[idx, grid.flat_index(i, j + 1)] += m * cp_water

            # --- Production (implicit sink at cell T) -------------------------
            diag += m_prod[i, j] * cp_water

            A[idx, idx] = diag
            # Injection heat source already contains m_dot * cp_water * T_inj [W]
            b[idx] = storage[i, j] * t_old[i, j] + q_heat_inj[i, j]

    return A.tocsr(), b


def step_coupled(
    grid: Grid,
    *,
    p_old: np.ndarray,
    t_old: np.ndarray,
    permeability: np.ndarray | float,
    porosity: np.ndarray | float,
    total_compressibility: float,
    mu: float,
    rho: float,
    cp_water: float,
    thermal_conductivity: np.ndarray | float,
    volumetric_heat_capacity: np.ndarray | float,
    dt: float,
    wells: list[WellSpec] | None = None,
    dirichlet_t: dict[tuple[int, int], float] | None = None,
) -> CoupledState:
    """Advance (P, T) by one coupled time step."""
    wells = wells or []
    q_vol, q_heat_inj, m_prod = apply_wells(
        wells, grid, rho_ref=rho, cp_water=cp_water
    )

    pressure_result = step_pressure(
        grid=grid,
        p_old=p_old,
        permeability=permeability,
        porosity=porosity,
        total_compressibility=total_compressibility,
        mu=mu,
        dt=dt,
        q_vol=q_vol,
    )
    p_new = pressure_result.pressure

    mx, my = compute_mass_flux(grid, p_new, permeability, mu, rho)

    A, b = assemble_energy_with_advection(
        grid=grid,
        thermal_conductivity=thermal_conductivity,
        volumetric_heat_capacity=volumetric_heat_capacity,
        cp_water=cp_water,
        dt=dt,
        t_old=t_old,
        mass_flux_x=mx,
        mass_flux_y=my,
        q_heat_inj=q_heat_inj,
        m_prod=m_prod,
        dirichlet=dirichlet_t,
    )
    t_new = spsolve(A, b).reshape(grid.shape)

    return CoupledState(pressure=p_new, temperature=t_new, mass_flux_x=mx, mass_flux_y=my)


def run_coupled_transient(
    grid: Grid,
    *,
    p_initial: np.ndarray,
    t_initial: np.ndarray,
    permeability: np.ndarray | float,
    porosity: np.ndarray | float,
    total_compressibility: float,
    mu: float,
    rho: float,
    cp_water: float,
    thermal_conductivity: np.ndarray | float,
    volumetric_heat_capacity: np.ndarray | float,
    dt: float,
    n_steps: int,
    wells: list[WellSpec] | None = None,
    dirichlet_t: dict[tuple[int, int], float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Run n_steps of coupled P–T.

    Returns ``(p_history, t_history)`` each of shape ``(n_steps + 1, nx, ny)``.
    """
    nx, ny = grid.shape
    p_hist = np.empty((n_steps + 1, nx, ny), dtype=np.float64)
    t_hist = np.empty((n_steps + 1, nx, ny), dtype=np.float64)
    p_hist[0] = p_initial
    t_hist[0] = t_initial
    p, t = p_initial.copy(), t_initial.copy()
    for k in range(n_steps):
        state = step_coupled(
            grid=grid,
            p_old=p,
            t_old=t,
            permeability=permeability,
            porosity=porosity,
            total_compressibility=total_compressibility,
            mu=mu,
            rho=rho,
            cp_water=cp_water,
            thermal_conductivity=thermal_conductivity,
            volumetric_heat_capacity=volumetric_heat_capacity,
            dt=dt,
            wells=wells,
            dirichlet_t=dirichlet_t,
        )
        p = state.pressure
        t = state.temperature
        p_hist[k + 1] = p
        t_hist[k + 1] = t
    return p_hist, t_hist

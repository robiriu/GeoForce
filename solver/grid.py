"""Structured 2D grid for GeoForce-Solver.

The grid is logically rectangular with uniform spacing in each direction.
Two conventional orientations are supported:

* **Horizontal (x, y):** used by the Theis benchmark (no gravity).
* **Vertical (x, z):** used by real geothermal demos (gravity + density).

The grid object itself is orientation-agnostic — it just provides cell
volumes, face areas, inter-cell distances, and center coordinates.
The PDE modules (darcy.py, energy.py) choose whether to enable gravity
based on the scenario dictionary, not on the grid type.

For a 2D slab simulation, we fix the out-of-plane thickness to 1 m, so
"volumetric" and "per-unit-thickness" rates coincide.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

THICKNESS = 1.0  # meters; out-of-plane extent of the 2D slab


@dataclass(frozen=True)
class Grid:
    """Uniform structured 2D grid.

    Attributes:
        nx: number of cells along the first axis.
        ny: number of cells along the second axis (y or z depending on orientation).
        dx: cell size along axis 0 (m).
        dy: cell size along axis 1 (m).
    """

    nx: int
    ny: int
    dx: float
    dy: float

    @property
    def shape(self) -> tuple[int, int]:
        return (self.nx, self.ny)

    @property
    def n_cells(self) -> int:
        return self.nx * self.ny

    @property
    def cell_volume(self) -> float:
        """Constant cell volume (m^3) assuming unit out-of-plane thickness."""
        return self.dx * self.dy * THICKNESS

    @property
    def face_area_x(self) -> float:
        """Area of a face normal to axis 0 (m^2)."""
        return self.dy * THICKNESS

    @property
    def face_area_y(self) -> float:
        """Area of a face normal to axis 1 (m^2)."""
        return self.dx * THICKNESS

    def cell_centers(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (X, Y) coordinate arrays of shape (nx, ny) at cell centers."""
        x = (np.arange(self.nx) + 0.5) * self.dx
        y = (np.arange(self.ny) + 0.5) * self.dy
        X, Y = np.meshgrid(x, y, indexing="ij")
        return X, Y

    def flat_index(self, i: int, j: int) -> int:
        """Row-major flattening: flat = i * ny + j."""
        return i * self.ny + j

    def radial_distance_from(self, i0: int, j0: int) -> np.ndarray:
        """Return an (nx, ny) array of distances from the center of cell (i0, j0)."""
        X, Y = self.cell_centers()
        x0 = (i0 + 0.5) * self.dx
        y0 = (j0 + 0.5) * self.dy
        return np.sqrt((X - x0) ** 2 + (Y - y0) ** 2)

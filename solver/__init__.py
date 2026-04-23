"""GeoForce-Solver — minimal single-phase geothermal reservoir solver.

Built live by an Opus 4.7 agent team during the "Built with Opus 4.7" hackathon.
Adopts TOUGH's finite-volume + fully-implicit backward-Euler philosophy;
deliberately simplifies to single-phase liquid water on a 2D structured grid.
"""

from __future__ import annotations

from .grid import Grid
from .properties import WaterProperties

__all__ = ["Grid", "WaterProperties"]

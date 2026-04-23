"""Analytical benchmark solutions for GeoForce-Solver validation."""

from __future__ import annotations

from .conduction_1d import conduction_step_temperature
from .theis import theis_pressure_change, well_function

__all__ = ["conduction_step_temperature", "theis_pressure_change", "well_function"]

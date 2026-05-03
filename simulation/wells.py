"""Randomized well placement on the 32x32x10 grid.

Producers and injectors are placed on the (NX, NY) horizontal plane and
opened across the reservoir layers (k in [2, 8)). Constraints:
  - N_prod in [1, 8]
  - N_inj  in [0, 4]
  - Producers and injectors must be on distinct (i, j) cells
  - Pairwise (i, j) separation >= MIN_WELL_SPACING_CELLS
  - All wells inside an interior margin (no edge cells)

If the constraints can't be satisfied within MAX_PLACEMENT_RETRIES, the
constraints relax (margin first, then min spacing) and a warning is
recorded on the WellSet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from simulation.grid import NX, NY, RESERVOIR_K

MIN_WELL_SPACING_CELLS: int = 3
EDGE_MARGIN_CELLS: int = 2
MAX_PLACEMENT_RETRIES: int = 200


@dataclass(frozen=True)
class Well:
    """A single vertical well."""

    kind: str          # "producer" or "injector"
    i: int             # x-index of the well column
    j: int             # y-index of the well column
    k_top: int         # top reservoir layer (inclusive)
    k_bot: int         # bottom reservoir layer (exclusive)
    rate_kg_s: float   # +ve for injector mass-source, +ve for producer mass-sink
    inj_temp_C: float | None = None  # only for injectors


@dataclass
class WellSet:
    """Collection of wells for one scenario."""

    wells: list[Well] = field(default_factory=list)
    relaxed_margin: bool = False
    relaxed_spacing: bool = False

    @property
    def producers(self) -> list[Well]:
        return [w for w in self.wells if w.kind == "producer"]

    @property
    def injectors(self) -> list[Well]:
        return [w for w in self.wells if w.kind == "injector"]


def _too_close(i: int, j: int, taken: list[tuple[int, int]], min_sep: int) -> bool:
    for ti, tj in taken:
        if abs(ti - i) < min_sep and abs(tj - j) < min_sep:
            return True
    return False


def _sample_positions(
    n: int,
    rng: np.random.Generator,
    taken: list[tuple[int, int]],
    margin: int,
    min_sep: int,
) -> list[tuple[int, int]] | None:
    out: list[tuple[int, int]] = []
    for _ in range(n):
        for _retry in range(MAX_PLACEMENT_RETRIES):
            i = int(rng.integers(margin, NX - margin))
            j = int(rng.integers(margin, NY - margin))
            if not _too_close(i, j, taken + out, min_sep):
                out.append((i, j))
                break
        else:
            return None
    return out


def place_wells(
    n_prod: int,
    n_inj: int,
    prod_rate_kg_s: float,
    inj_rate_kg_s: float,
    inj_temp_C: float,
    rng: np.random.Generator,
) -> WellSet:
    """Sample a constraint-satisfying well layout.

    Returns a WellSet; sets `relaxed_*` flags if constraints were relaxed.
    """
    if not 1 <= n_prod <= 8:
        raise ValueError(f"n_prod {n_prod} outside [1, 8]")
    if not 0 <= n_inj <= 4:
        raise ValueError(f"n_inj {n_inj} outside [0, 4]")

    margin = EDGE_MARGIN_CELLS
    sep = MIN_WELL_SPACING_CELLS
    relaxed_margin = False
    relaxed_spacing = False

    while True:
        prod_pos = _sample_positions(n_prod, rng, [], margin, sep)
        if prod_pos is not None:
            inj_pos = _sample_positions(n_inj, rng, prod_pos, margin, sep)
            if inj_pos is not None:
                break
        if sep > 1:
            sep -= 1
            relaxed_spacing = True
            continue
        if margin > 0:
            margin -= 1
            relaxed_margin = True
            continue
        raise RuntimeError("could not place wells even after relaxing all constraints")

    k_top, k_bot = RESERVOIR_K
    wells: list[Well] = []
    for i, j in prod_pos:
        wells.append(
            Well(kind="producer", i=i, j=j, k_top=k_top, k_bot=k_bot, rate_kg_s=prod_rate_kg_s)
        )
    for i, j in inj_pos:
        wells.append(
            Well(
                kind="injector",
                i=i,
                j=j,
                k_top=k_top,
                k_bot=k_bot,
                rate_kg_s=inj_rate_kg_s,
                inj_temp_C=inj_temp_C,
            )
        )
    return WellSet(wells=wells, relaxed_margin=relaxed_margin, relaxed_spacing=relaxed_spacing)

"""Tests for simulation/wells.py — placement constraints and reproducibility."""

from __future__ import annotations

import numpy as np
import pytest

from simulation.grid import NX, NY, RESERVOIR_K
from simulation.wells import EDGE_MARGIN_CELLS, place_wells


def _rng(seed: int = 0) -> np.random.Generator:
    return np.random.default_rng(seed)


def test_well_counts_respected() -> None:
    ws = place_wells(
        n_prod=4, n_inj=2,
        prod_rate_kg_s=80.0, inj_rate_kg_s=50.0, inj_temp_C=160.0,
        rng=_rng(42),
    )
    assert len(ws.producers) == 4
    assert len(ws.injectors) == 2


def test_unique_ij_positions() -> None:
    ws = place_wells(
        n_prod=8, n_inj=4,
        prod_rate_kg_s=80.0, inj_rate_kg_s=50.0, inj_temp_C=160.0,
        rng=_rng(1),
    )
    positions = [(w.i, w.j) for w in ws.wells]
    assert len(positions) == len(set(positions))


def test_wells_open_in_reservoir_layers() -> None:
    ws = place_wells(
        n_prod=2, n_inj=1,
        prod_rate_kg_s=80.0, inj_rate_kg_s=50.0, inj_temp_C=160.0,
        rng=_rng(7),
    )
    k_top, k_bot = RESERVOIR_K
    for w in ws.wells:
        assert w.k_top == k_top
        assert w.k_bot == k_bot


def test_edge_margin_when_unrelaxed() -> None:
    ws = place_wells(
        n_prod=1, n_inj=0,
        prod_rate_kg_s=80.0, inj_rate_kg_s=50.0, inj_temp_C=160.0,
        rng=_rng(3),
    )
    if not ws.relaxed_margin:
        for w in ws.wells:
            assert EDGE_MARGIN_CELLS <= w.i < NX - EDGE_MARGIN_CELLS
            assert EDGE_MARGIN_CELLS <= w.j < NY - EDGE_MARGIN_CELLS


def test_invalid_counts_rejected() -> None:
    with pytest.raises(ValueError):
        place_wells(0, 0, 80.0, 50.0, 160.0, _rng(0))
    with pytest.raises(ValueError):
        place_wells(9, 0, 80.0, 50.0, 160.0, _rng(0))
    with pytest.raises(ValueError):
        place_wells(1, 5, 80.0, 50.0, 160.0, _rng(0))


def test_reproducible_under_same_seed() -> None:
    a = place_wells(3, 2, 80.0, 50.0, 160.0, _rng(123))
    b = place_wells(3, 2, 80.0, 50.0, 160.0, _rng(123))
    assert [(w.kind, w.i, w.j) for w in a.wells] == [(w.kind, w.i, w.j) for w in b.wells]


def test_injector_temperature_set() -> None:
    ws = place_wells(2, 2, 80.0, 50.0, 160.0, _rng(0))
    for w in ws.injectors:
        assert w.inj_temp_C == 160.0
    for w in ws.producers:
        assert w.inj_temp_C is None

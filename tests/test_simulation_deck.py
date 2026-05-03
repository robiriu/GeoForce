"""Tests for simulation/deck.py — Waiwera JSON structure and round-trip."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from simulation.deck import build_deck_doc, write_deck
from simulation.grid import LayerProps, build_grid, NX, NY, NZ
from simulation.sampling import sample
from simulation.wells import place_wells


def _grid():
    cap = LayerProps(permeability_m2=1e-17, porosity=0.02, thermal_conductivity_W_mK=2.0)
    res = LayerProps(permeability_m2=1e-14, porosity=0.10, thermal_conductivity_W_mK=2.5)
    bas = LayerProps(permeability_m2=1e-18, porosity=0.01, thermal_conductivity_W_mK=2.5)
    return build_grid(cap, res, bas)


def _wellset():
    return place_wells(
        n_prod=2, n_inj=1,
        prod_rate_kg_s=80.0, inj_rate_kg_s=50.0, inj_temp_C=160.0,
        rng=np.random.default_rng(0),
    )


def test_doc_has_required_top_level_keys() -> None:
    s = sample(1, seed=0)[0]
    doc = build_deck_doc(s, _grid(), _wellset())
    for key in ("title", "thermodynamics", "eos", "gravity", "mesh", "rock", "initial", "source", "time", "output"):
        assert key in doc, f"missing top-level key {key}"


def test_rock_blocks_partition_grid() -> None:
    s = sample(1, seed=1)[0]
    doc = build_deck_doc(s, _grid(), _wellset())
    cell_ids = []
    for rt in doc["rock"]["types"]:
        cell_ids.extend(rt["cells"])
    assert len(cell_ids) == NX * NY * NZ
    assert len(set(cell_ids)) == NX * NY * NZ  # no duplicates


def test_well_sources_count_matches() -> None:
    """Each well contributes one source per open layer (k_top..k_bot)."""
    s = sample(1, seed=2)[0]
    ws = _wellset()
    doc = build_deck_doc(s, _grid(), ws)
    expected = sum(w.k_bot - w.k_top for w in ws.wells)
    assert len(doc["source"]) == expected


def test_producer_rates_negative_injector_positive() -> None:
    s = sample(1, seed=3)[0]
    doc = build_deck_doc(s, _grid(), _wellset())
    by_prefix = {"P": [], "I": []}
    for src in doc["source"]:
        by_prefix[src["name"][0]].append(src["rate"])
    assert all(r < 0 for r in by_prefix["P"])
    assert all(r > 0 for r in by_prefix["I"])


def test_injector_carries_enthalpy() -> None:
    s = sample(1, seed=4)[0]
    doc = build_deck_doc(s, _grid(), _wellset())
    inj = [src for src in doc["source"] if src["name"].startswith("I")]
    assert inj, "test fixture should have at least one injector"
    for src in inj:
        assert "enthalpy" in src
        assert src["enthalpy"] > 0


def test_initial_condition_two_phase_when_steam_saturation_positive() -> None:
    s = sample(64, seed=5)
    two_phase = [x for x in s if x.initial_steam_saturation > 0.0]
    assert two_phase, "expected at least one two-phase scenario in 64 LHS samples"
    doc = build_deck_doc(two_phase[0], _grid(), _wellset())
    assert doc["initial"]["region"] == 4


def test_json_round_trip(tmp_path: Path) -> None:
    s = sample(1, seed=6)[0]
    bundle = write_deck(s, _grid(), _wellset(), tmp_path)
    assert bundle.json_path.exists()
    assert bundle.mesh_path.exists()
    reloaded = json.loads(bundle.json_path.read_text())
    assert reloaded["title"] == bundle.json_doc["title"]
    assert len(reloaded["source"]) == len(bundle.json_doc["source"])

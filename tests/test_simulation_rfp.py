"""Offline tests for the RFP benchmark deck builder.

These run on the VPS without Waiwera; they validate deck shape and the
analytical comparison machinery, leaving the actual numerical-vs-Theis
assertion for the Kaggle notebook.
"""

from __future__ import annotations

import math

from simulation.rfp import (
    DX_RFP_M,
    NX_RFP,
    NY_RFP,
    NZ_RFP,
    RFP_DURATION_S,
    RFP_PRESSURE_PA,
    SAMPLE_RADIAL_OFFSETS,
    WELL_I,
    WELL_J,
    build_rfp_deck_doc,
    compare_to_theis,
)


def test_deck_doc_basic_shape():
    doc = build_rfp_deck_doc()
    n_cells = NX_RFP * NY_RFP * NZ_RFP

    assert doc["eos"]["name"] == "we"
    assert doc["initial"]["region"] == 1
    assert len(doc["initial"]["primary"]) == n_cells
    assert len(doc["rock"]["types"][0]["cells"]) == n_cells
    assert doc["time"]["stop"] == RFP_DURATION_S
    assert doc["output"]["checkpoint"]["time"] == [RFP_DURATION_S]


def test_deck_doc_single_central_source():
    doc = build_rfp_deck_doc()
    sources = doc["source"]
    assert len(sources) == 1
    src = sources[0]
    expected_cell = (0 * NY_RFP + WELL_J) * NX_RFP + WELL_I
    assert src["cell"] == expected_cell
    assert src["rate"] < 0.0  # production
    assert src["component"] == "water"


def test_deck_doc_gravity_disabled():
    """Theis assumes no buoyancy; gravity must be 0 in the RFP deck."""
    assert build_rfp_deck_doc()["gravity"] == 0.0


def test_compare_to_theis_zero_error_at_analytical_pressure():
    """Feed the analytical pressure back in; rel_err must be ~0."""
    from solver.benchmarks.theis import theis_pressure_change
    from simulation.rfp import build_rfp_deck_doc  # noqa: F401  (ensure import)
    from simulation.rfp import RFP_DURATION_S, build_rfp_deck

    # We need an RfpDeck instance but without I/O. Use a tmp dir.
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        # build_rfp_deck uses PyTOUGH; only call it if importable.
        try:
            deck = build_rfp_deck(pathlib.Path(td))
        except ImportError:
            return  # PyTOUGH not installed in this env; skip

        # Build synthetic "numerical" pressures equal to analytical.
        synth = []
        for r, c in zip(deck.sample_radii_m, deck.sample_cell_ids):
            dp = float(theis_pressure_change(
                r=r, t=RFP_DURATION_S,
                mass_rate=deck.theis_params.mass_rate,
                permeability=deck.theis_params.permeability,
                viscosity=deck.theis_params.viscosity,
                density=deck.theis_params.density,
                porosity=deck.theis_params.porosity,
                total_compressibility=deck.theis_params.total_compressibility,
                thickness=deck.theis_params.thickness,
            ))
            synth.append((r, RFP_DURATION_S, deck.initial_pressure_Pa + dp))

        rows = compare_to_theis(synth, deck)
        for _, _, _, _, rel_err in rows:
            assert rel_err < 1e-6


def test_sample_radii_and_cells_match_offsets():
    import tempfile, pathlib
    from simulation.rfp import build_rfp_deck
    with tempfile.TemporaryDirectory() as td:
        try:
            deck = build_rfp_deck(pathlib.Path(td))
        except ImportError:
            return

    assert deck.sample_radii_m == tuple(d * DX_RFP_M for d in SAMPLE_RADIAL_OFFSETS)
    for offset, cell_id in zip(SAMPLE_RADIAL_OFFSETS, deck.sample_cell_ids):
        expected = (0 * NY_RFP + WELL_J) * NX_RFP + (WELL_I + offset)
        assert cell_id == expected


def test_theis_window_safety_margins():
    """The Theis dimensionless time u at the farthest sample radius
    should be small enough for the well function to be evaluable, and
    boundary effects (u at the half-domain extent) should be negligible.
    """
    from simulation.rfp import (
        RFP_PERMEABILITY_M2,
        RFP_POROSITY,
        RFP_TOTAL_COMPRESSIBILITY_1_PA,
        RFP_VISCOSITY_PA_S,
    )
    r_far = max(SAMPLE_RADIAL_OFFSETS) * DX_RFP_M
    u_far = (
        RFP_POROSITY * RFP_VISCOSITY_PA_S * RFP_TOTAL_COMPRESSIBILITY_1_PA
        * r_far ** 2 / (4.0 * RFP_PERMEABILITY_M2 * RFP_DURATION_S)
    )
    assert u_far < 2.0, f"farthest sample is past the Theis window (u={u_far:.3g})"

    half_domain = (NX_RFP // 2) * DX_RFP_M
    u_boundary = (
        RFP_POROSITY * RFP_VISCOSITY_PA_S * RFP_TOTAL_COMPRESSIBILITY_1_PA
        * half_domain ** 2 / (4.0 * RFP_PERMEABILITY_M2 * RFP_DURATION_S)
    )
    # W(3) ~ 0.013 — boundary contribution under 2% of nearest-sample signal.
    assert u_boundary > 3.0, (
        f"domain too small for closed-boundary effects to be negligible "
        f"(u_boundary={u_boundary:.3g})"
    )

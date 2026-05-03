"""Offline tests for the RFP benchmark deck builder.

These run on the VPS without Waiwera; they validate deck shape and the
analytical comparison machinery, leaving the actual numerical-vs-Theis
assertion for the Kaggle notebook.
"""

from __future__ import annotations

import math

from simulation.rfp import (
    N_R,
    R_INNER_M,
    R_OUTER_M,
    RFP_DURATION_S,
    RFP_PRESSURE_PA,
    SAMPLE_RADII_TARGET_M,
    build_rfp_deck_doc,
    compare_to_theis,
)


def test_deck_doc_basic_shape():
    doc = build_rfp_deck_doc()

    assert doc["eos"]["name"] == "w"
    assert doc["initial"]["region"] == 1
    assert len(doc["initial"]["primary"]) == N_R
    assert len(doc["rock"]["types"][0]["cells"]) == N_R
    assert doc["mesh"]["radial"] is True
    assert doc["time"]["stop"] == RFP_DURATION_S
    assert doc["output"]["checkpoint"]["time"] == [RFP_DURATION_S]


def test_deck_doc_single_central_source():
    doc = build_rfp_deck_doc()
    sources = doc["source"]
    assert len(sources) == 1
    src = sources[0]
    assert src["cell"] == 0  # innermost radial cell is the well
    assert src["rate"] < 0.0  # production
    assert src["component"] == "water"


def test_deck_doc_gravity_disabled():
    """Theis assumes no buoyancy; gravity must be 0 in the RFP deck."""
    assert build_rfp_deck_doc()["gravity"] == 0.0


def test_compare_to_theis_zero_error_at_analytical_pressure():
    """Feed the analytical pressure back in; rel_err must be ~0."""
    from solver.benchmarks.theis import theis_pressure_change
    from simulation.rfp import RFP_DURATION_S, build_rfp_deck

    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        try:
            deck = build_rfp_deck(pathlib.Path(td))
        except ImportError:
            return  # PyTOUGH not installed in this env; skip

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


def test_sample_radii_in_domain_and_unique():
    """Sample radii must lie within (R_INNER, R_OUTER), be strictly
    increasing, and map to distinct cells.
    """
    import tempfile, pathlib
    from simulation.rfp import build_rfp_deck

    with tempfile.TemporaryDirectory() as td:
        try:
            deck = build_rfp_deck(pathlib.Path(td))
        except ImportError:
            return

    radii = deck.sample_radii_m
    cells = deck.sample_cell_ids
    assert len(radii) == len(SAMPLE_RADII_TARGET_M)
    assert len(set(cells)) == len(cells), "duplicate sample cells"
    assert all(R_INNER_M < r < R_OUTER_M for r in radii)
    assert all(r0 < r1 for r0, r1 in zip(radii[:-1], radii[1:]))
    # Each resolved radius should be reasonably close to its target
    # (within one cell width — log spacing means near-target accuracy).
    for r, target in zip(radii, SAMPLE_RADII_TARGET_M):
        assert abs(r - target) / target < 0.10


def test_theis_window_safety_margins():
    """The Theis dimensionless time u at the farthest sample radius
    should be small enough for the well function to be evaluable, and
    boundary effects (u at the outer boundary) should be negligible.
    """
    from simulation.rfp import (
        RFP_PERMEABILITY_M2,
        RFP_POROSITY,
        RFP_TOTAL_COMPRESSIBILITY_1_PA,
        RFP_VISCOSITY_PA_S,
    )
    r_far = max(SAMPLE_RADII_TARGET_M)
    u_far = (
        RFP_POROSITY * RFP_VISCOSITY_PA_S * RFP_TOTAL_COMPRESSIBILITY_1_PA
        * r_far ** 2 / (4.0 * RFP_PERMEABILITY_M2 * RFP_DURATION_S)
    )
    assert u_far < 2.0, f"farthest sample is past the Theis window (u={u_far:.3g})"

    u_boundary = (
        RFP_POROSITY * RFP_VISCOSITY_PA_S * RFP_TOTAL_COMPRESSIBILITY_1_PA
        * R_OUTER_M ** 2 / (4.0 * RFP_PERMEABILITY_M2 * RFP_DURATION_S)
    )
    # W(3) ~ 0.013 — boundary contribution under 2% of nearest-sample signal.
    assert u_boundary > 3.0, (
        f"domain too small for closed-boundary effects to be negligible "
        f"(u_boundary={u_boundary:.3g})"
    )


def test_storativity_contract_matches_iapws_c_w():
    """The c_t fed to Theis must equal IAPWS isothermal water
    compressibility at the run state, since the rfp deck declares no
    rock pore-compressibility under EOS w.
    """
    try:
        from iapws import IAPWS97
    except ImportError:
        return  # iapws not installed in this env; skip

    from simulation.rfp import (
        RFP_PRESSURE_PA,
        RFP_TEMPERATURE_C,
        RFP_TOTAL_COMPRESSIBILITY_1_PA,
    )
    T_K = RFP_TEMPERATURE_C + 273.15
    P_MPa = RFP_PRESSURE_PA / 1.0e6
    dP = 0.01
    rho_lo = IAPWS97(T=T_K, P=P_MPa - dP).rho
    rho_hi = IAPWS97(T=T_K, P=P_MPa + dP).rho
    rho_0 = IAPWS97(T=T_K, P=P_MPa).rho
    c_w = (rho_hi - rho_lo) / (2.0 * dP * 1.0e6) / rho_0

    rel = abs(RFP_TOTAL_COMPRESSIBILITY_1_PA - c_w) / c_w
    assert rel < 0.05, (
        f"c_t = {RFP_TOTAL_COMPRESSIBILITY_1_PA:.3e} disagrees with IAPWS "
        f"c_w = {c_w:.3e} at ({RFP_TEMPERATURE_C} C, {P_MPa} MPa) "
        f"by {rel*100:.1f}% (>5%). Theis storativity will not match Waiwera."
    )


def test_eos_region_primary_variable_consistency():
    """Allowed (eos.name, initial.region, primary_variable_names) tuples."""
    doc = build_rfp_deck_doc()
    eos_name = doc["eos"]["name"]
    region = doc["initial"]["region"]
    pvars = tuple(doc["eos"]["primary_variable_names"])

    allowed = {
        ("w", 1): ("pressure",),
        ("we", 1): ("pressure", "temperature"),
        ("we", 4): ("pressure", "vapour_saturation"),
    }
    key = (eos_name, region)
    assert key in allowed, f"unrecognised eos+region combo: {key}"
    assert pvars == allowed[key], (
        f"primary_variable_names {pvars} not allowed for "
        f"eos={eos_name}, region={region}; expected {allowed[key]}"
    )


def test_radial_mesh_topology():
    """Loaded mesh must be a 1D radial column: N_R hex cells, single
    y-row, single z-layer. The deck must set mesh.radial = True so
    Waiwera computes annular cell volumes.
    """
    import tempfile, pathlib
    from simulation.rfp import build_rfp_deck

    with tempfile.TemporaryDirectory() as td:
        try:
            deck = build_rfp_deck(pathlib.Path(td))
        except ImportError:
            return

        try:
            import meshio
        except ImportError:
            return

        mesh = meshio.read(str(deck.mesh_path))
        hex_blocks = [c for c in mesh.cells if c.type == "hexahedron"]
        assert hex_blocks, "no hex cells found in mesh"
        n_cells = sum(b.data.shape[0] for b in hex_blocks)
        assert n_cells == N_R, f"expected {N_R} radial cells, got {n_cells}"

    doc = build_rfp_deck_doc()
    assert doc["mesh"].get("radial") is True, "mesh.radial flag missing"
    assert "thickness" not in doc["mesh"], (
        "mesh.thickness must not be set; the 3D radial mesh has its own dz"
    )

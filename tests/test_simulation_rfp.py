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

    assert doc["eos"]["name"] == "w"
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


def test_time_step_ceiling_below_cell_diffusion_time():
    """Backward-Euler under-resolves transient propagation if the time
    step is much larger than the cell diffusion time. Catches the v10
    bug where max_step = duration/4 left only ~5 implicit steps and
    numerical drawdown decayed too steeply with radius.
    """
    from simulation.rfp import (
        DX_RFP_M,
        RFP_MAX_STEP_S,
        RFP_PERMEABILITY_M2,
        RFP_POROSITY,
        RFP_TOTAL_COMPRESSIBILITY_1_PA,
        RFP_VISCOSITY_PA_S,
    )
    alpha = RFP_PERMEABILITY_M2 / (
        RFP_VISCOSITY_PA_S * RFP_POROSITY * RFP_TOTAL_COMPRESSIBILITY_1_PA
    )
    cell_diffusion_time = (DX_RFP_M / 2.0) ** 2 / alpha
    ratio = RFP_MAX_STEP_S / cell_diffusion_time
    assert ratio < 0.5, (
        f"max time step {RFP_MAX_STEP_S} s is too large vs cell "
        f"diffusion time {cell_diffusion_time:.1f} s (ratio {ratio:.2f}); "
        f"backward-Euler will under-resolve the transient"
    )


def test_storativity_contract_matches_iapws_c_w():
    """The c_t fed to Theis must equal IAPWS isothermal water
    compressibility at the run state, since the rfp deck declares no
    rock pore-compressibility under EOS w. Catches the v9 bug where
    c_t = 1.5e-10 was 3x too small.
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
    """Allowed (eos.name, initial.region, primary_variable_names) tuples
    per Waiwera's documented EOS schema. Catches schema bugs like the
    deck.py:170 mismatch (we + region 1 + [P, vapour_saturation]).
    """
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


def test_mesh_cell_volume_matches_dx_dy_dz():
    """Loaded ExodusII mesh must have cells of volume DX*DY*DZ, and the
    deck must NOT redundantly set mesh.thickness (we ship a real 3D
    mesh). Catches the v9 mesh.thickness double-count concern.
    """
    import tempfile, pathlib
    from simulation.rfp import build_rfp_deck, DZ_RFP_M

    with tempfile.TemporaryDirectory() as td:
        try:
            deck = build_rfp_deck(pathlib.Path(td))
        except ImportError:
            return  # PyTOUGH/meshio/netCDF4 not installed; skip

        try:
            import meshio
        except ImportError:
            return

        mesh = meshio.read(str(deck.mesh_path))
        # The exodus mesh writer emits hexahedral cells.
        hex_blocks = [c for c in mesh.cells if c.type == "hexahedron"]
        assert hex_blocks, "no hex cells found in mesh"
        n_cells = sum(b.data.shape[0] for b in hex_blocks)
        assert n_cells == NX_RFP * NY_RFP * NZ_RFP

        # Spot-check one cell's volume from its 8 corner points.
        block = hex_blocks[0]
        corners = mesh.points[block.data[0]]
        dx = corners[:, 0].max() - corners[:, 0].min()
        dy = corners[:, 1].max() - corners[:, 1].min()
        dz = corners[:, 2].max() - corners[:, 2].min()
        assert math.isclose(dx, DX_RFP_M, rel_tol=1e-6)
        assert math.isclose(dy, DX_RFP_M, rel_tol=1e-6)
        assert math.isclose(dz, DZ_RFP_M, rel_tol=1e-6)

    doc = build_rfp_deck_doc()
    assert "thickness" not in doc["mesh"], (
        "mesh.thickness must not be set on a 3D mesh (would double-count)"
    )

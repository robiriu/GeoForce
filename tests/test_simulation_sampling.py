"""Tests for simulation/sampling.py — LHS bounds, integer rounding, reproducibility."""

from __future__ import annotations

from simulation.sampling import load_spec, sample


def test_sample_count_and_ids_unique() -> None:
    s = sample(20, seed=0)
    assert len(s) == 20
    assert len({x.scenario_id for x in s}) == 20


def test_bounds_respected() -> None:
    spec = load_spec()
    dims = spec["dimensions"]
    s = sample(64, seed=1)
    for x in s:
        assert dims["base_temperature_C"]["min"] <= x.base_temperature_C <= dims["base_temperature_C"]["max"]
        assert dims["log10_permeability_m2"]["min"] <= x.log10_permeability_m2 <= dims["log10_permeability_m2"]["max"]
        assert dims["porosity"]["min"] <= x.porosity <= dims["porosity"]["max"]
        assert 1 <= x.n_production_wells <= 8
        assert 0 <= x.n_injection_wells <= 4


def test_integer_dims_rounded() -> None:
    s = sample(32, seed=2)
    for x in s:
        assert isinstance(x.n_production_wells, int)
        assert isinstance(x.n_injection_wells, int)


def test_reservoir_props_derived_correctly() -> None:
    s = sample(4, seed=3)
    for x in s:
        rp = x.reservoir_props
        assert rp.permeability_m2 == 10.0 ** x.log10_permeability_m2
        assert rp.porosity == x.porosity
        assert rp.thermal_conductivity_W_mK == x.rock_thermal_conductivity_W_mK


def test_injection_temp_below_reservoir() -> None:
    s = sample(8, seed=4)
    for x in s:
        # injection temp must be at least 100 C below reservoir target,
        # except when clipped at the 40 C floor for very cool reservoirs
        assert x.injection_temp_C <= x.base_temperature_C - 100.0 + 1e-6 or x.injection_temp_C == 40.0


def test_reproducible() -> None:
    a = sample(8, seed=99)
    b = sample(8, seed=99)
    assert all(
        x.base_temperature_C == y.base_temperature_C
        for x, y in zip(a, b)
    )


def test_lhs_coverage_over_unit_cube() -> None:
    """LHS over many samples should well-cover each marginal."""
    s = sample(200, seed=7)
    perms = [x.log10_permeability_m2 for x in s]
    # Spread should reach close to both ends
    assert min(perms) < -15.5
    assert max(perms) > -12.5

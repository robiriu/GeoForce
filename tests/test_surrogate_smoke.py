"""Smoke test for GeoForce v1.1 surrogate port.

Asserts:
    1. Weights load without error.
    2. Parameter count = 57,802 (matches v1.1 metadata).
    3. Inference on a canonical Ulubelu-like scenario runs.
    4. Output shape is (5, 32, 32) per field.
    5. Temperature stays in [25, 350] C and pressure in [1e5, 5e7] Pa.
    6. Inference completes in < 50 ms on CPU (generous bound vs. 3.2 ms target).
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from surrogate import load_model, predict
from surrogate.encoding import GRID_SIZE, NORMALIZATION


@pytest.fixture(scope="module")
def model():
    return load_model()


def _ulubelu_like_scenario() -> dict:
    """Canonical single-producer liquid-dominated scenario."""
    depth = 1800.0
    base_temperature_c = 250.0
    # Hydrostatic-ish gradient for initial temperature: warm at base, cooler up.
    z_grad = np.linspace(base_temperature_c, base_temperature_c - 40.0, GRID_SIZE)
    initial_temperature = np.broadcast_to(
        z_grad.reshape(-1, 1), (GRID_SIZE, GRID_SIZE)
    ).astype(np.float32).copy()
    return {
        "initial_temperature": initial_temperature,
        "log_permeability": -13.5,
        "well_locations": [(16, 16)],
        "base_pressure": 1.5e7,  # 15 MPa
        "porosity": 0.08,
        "depth": depth,
    }


def test_model_parameter_count(model):
    assert model.count_parameters() == 57_802


def test_model_input_channels(model):
    assert model.in_channels == 6


def test_prediction_shape_and_range(model):
    scenario = _ulubelu_like_scenario()
    result = predict(**scenario, model=model)

    assert set(result.keys()) == {"temperature", "pressure"}
    assert result["temperature"].shape == (5, GRID_SIZE, GRID_SIZE)
    assert result["pressure"].shape == (5, GRID_SIZE, GRID_SIZE)

    t = result["temperature"]
    p = result["pressure"]
    assert NORMALIZATION["T_MIN"] - 0.1 <= t.min()
    assert t.max() <= NORMALIZATION["T_MAX"] + 0.1
    assert NORMALIZATION["P_MIN"] - 1.0 <= p.min()
    assert p.max() <= NORMALIZATION["P_MAX"] + 1.0


def test_inference_latency(model):
    scenario = _ulubelu_like_scenario()
    # Warm-up run first (first inference pays init cost).
    predict(**scenario, model=model)

    t0 = time.perf_counter()
    for _ in range(5):
        predict(**scenario, model=model)
    elapsed_ms = (time.perf_counter() - t0) * 1000 / 5
    assert elapsed_ms < 50, f"inference {elapsed_ms:.1f} ms exceeds 50 ms budget"


def test_cache_is_idempotent():
    m1 = load_model()
    m2 = load_model()
    assert m1 is m2

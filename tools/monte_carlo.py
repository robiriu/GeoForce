"""Monte Carlo ensemble over reservoir parameter distributions.

Wraps :func:`tools.predict_surrogate.predict` (default) or
:func:`tools.predict_solver.predict` and returns P10/P50/P90 fields +
per-sample scalars.

Only single-draw-per-parameter distributions are supported. The caller
provides a plain dict like:

    distributions = {
        "porosity":         {"dist": "uniform", "low": 0.08, "high": 0.18},
        "log_permeability": {"dist": "uniform", "low": -12.8, "high": -11.8},
        "T_initial":        {"dist": "normal",  "mean": 220.0, "std": 10.0},
    }

plus a base ``scenario`` dict. For each draw, the distribution values
overwrite the corresponding scenario keys, then predict() is called.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np

from tools.predict_solver import predict as _solver_predict
from tools.predict_surrogate import predict as _surrogate_predict

ENGINES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "solver": _solver_predict,
    "surrogate": _surrogate_predict,
}


def _sample(rng: np.random.Generator, spec: dict[str, Any]) -> float:
    dist = spec.get("dist", "uniform").lower()
    if dist == "uniform":
        return float(rng.uniform(spec["low"], spec["high"]))
    if dist == "normal":
        return float(rng.normal(spec["mean"], spec["std"]))
    if dist == "lognormal":
        return float(rng.lognormal(spec["mean"], spec["sigma"]))
    if dist == "triangular":
        return float(rng.triangular(spec["low"], spec["mode"], spec["high"]))
    msg = f"Unsupported distribution: {dist}"
    raise ValueError(msg)


def run(
    scenario: dict[str, Any],
    distributions: dict[str, dict[str, Any]],
    *,
    n_samples: int = 200,
    engine: str = "surrogate",
    seed: int | None = 0,
) -> dict[str, Any]:
    """Run a Monte Carlo ensemble.

    Args:
        scenario: base scenario dict (keys not in ``distributions`` stay fixed).
        distributions: name → spec dict. Each spec has ``dist`` plus its params.
        n_samples: number of ensemble members.
        engine: ``"surrogate"`` (fast, recommended) or ``"solver"``.
        seed: RNG seed for reproducibility.

    Returns:
        Dict with:
            - ``p10``, ``p50``, ``p90``: (nx, ny) temperature percentile fields
            - ``p10_pressure_MPa``, ``p50_pressure_MPa``, ``p90_pressure_MPa``
            - ``samples``: list of drawn parameter dicts (length n_samples)
            - ``scalar_summary``: per-quantity min/p10/p50/p90/max/mean
            - ``engine``: engine name used
            - ``elapsed_seconds``: wall clock for the full ensemble
    """
    if engine not in ENGINES:
        msg = f"Unknown engine {engine!r}; choose from {sorted(ENGINES)}"
        raise ValueError(msg)
    predict_fn = ENGINES[engine]
    rng = np.random.default_rng(seed)

    t_stack: list[np.ndarray] = []
    p_stack: list[np.ndarray] = []
    draws: list[dict[str, float]] = []
    t_means: list[float] = []
    t_mins: list[float] = []
    t_maxs: list[float] = []

    start = time.perf_counter()
    for _ in range(n_samples):
        draw = {name: _sample(rng, spec) for name, spec in distributions.items()}
        local = {**scenario, **draw}
        result = predict_fn(local)
        t = np.asarray(result["temperature"])
        p = np.asarray(result["pressure"])
        t_stack.append(t)
        p_stack.append(p)
        draws.append(draw)
        t_means.append(float(t.mean()))
        t_mins.append(float(t.min()))
        t_maxs.append(float(t.max()))
    elapsed = time.perf_counter() - start

    t_arr = np.stack(t_stack, axis=0)
    p_arr = np.stack(p_stack, axis=0)

    t10, t50, t90 = np.percentile(t_arr, [10, 50, 90], axis=0)
    p10, p50, p90 = np.percentile(p_arr, [10, 50, 90], axis=0) / 1.0e6  # MPa

    def _stats(values: list[float]) -> dict[str, float]:
        a = np.asarray(values)
        q = np.percentile(a, [10, 50, 90])
        return {
            "min": float(a.min()),
            "p10": float(q[0]),
            "p50": float(q[1]),
            "p90": float(q[2]),
            "max": float(a.max()),
            "mean": float(a.mean()),
        }

    return {
        "p10": t10,
        "p50": t50,
        "p90": t90,
        "p10_pressure_MPa": p10,
        "p50_pressure_MPa": p50,
        "p90_pressure_MPa": p90,
        "samples": draws,
        "scalar_summary": {
            "mean_temperature_C": _stats(t_means),
            "min_temperature_C": _stats(t_mins),
            "max_temperature_C": _stats(t_maxs),
        },
        "engine": engine,
        "n_samples": n_samples,
        "elapsed_seconds": elapsed,
    }

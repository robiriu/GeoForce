"""One-at-a-time (OAT) sensitivity analysis for scenario parameters.

For each parameter in ``params``, sweep it across [low, high] with
``n_points`` evenly-spaced values (holding the others at their base
scenario values), call the engine's ``predict()``, and summarize how a
probe metric responds.

Default probe metric is the temperature at cell (i,j) corresponding to
``probe_x_m``/``probe_y_m``, but callers can also ask for reservoir mean
temperature.
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


def _cell_index(grid: dict[str, Any], x_m: float, y_m: float) -> tuple[int, int]:
    i = int(round(x_m / grid["dx"] - 0.5))
    j = int(round(y_m / grid["dy"] - 0.5))
    i = int(np.clip(i, 0, grid["nx"] - 1))
    j = int(np.clip(j, 0, grid["ny"] - 1))
    return i, j


def _metric(result: dict[str, Any], metric: str, probe: tuple[int, int] | None) -> float:
    t = np.asarray(result["temperature"])
    p = np.asarray(result["pressure"])
    if metric == "probe_temperature_C":
        if probe is None:
            msg = "probe_temperature_C requires probe_x_m/probe_y_m"
            raise ValueError(msg)
        return float(t[probe])
    if metric == "mean_temperature_C":
        return float(t.mean())
    if metric == "min_temperature_C":
        return float(t.min())
    if metric == "max_temperature_C":
        return float(t.max())
    if metric == "mean_pressure_MPa":
        return float(p.mean()) / 1.0e6
    msg = f"Unknown metric {metric!r}"
    raise ValueError(msg)


def run(
    scenario: dict[str, Any],
    params: dict[str, dict[str, float]],
    *,
    engine: str = "surrogate",
    n_points: int = 5,
    metric: str = "probe_temperature_C",
    probe_x_m: float | None = None,
    probe_y_m: float | None = None,
) -> dict[str, Any]:
    """Run OAT sensitivity.

    Args:
        scenario: base scenario dict.
        params: name → {"low": ..., "high": ...} sweep range per parameter.
        engine: ``"surrogate"`` or ``"solver"``.
        n_points: samples per parameter (linspace).
        metric: which scalar to track. One of
            ``probe_temperature_C``, ``mean_temperature_C``, ``min_temperature_C``,
            ``max_temperature_C``, ``mean_pressure_MPa``.
        probe_x_m, probe_y_m: required when metric is ``probe_temperature_C``.

    Returns:
        Dict with per-parameter sweep curves plus a ranking by |Δmetric|.
    """
    if engine not in ENGINES:
        msg = f"Unknown engine {engine!r}; choose from {sorted(ENGINES)}"
        raise ValueError(msg)
    predict_fn = ENGINES[engine]

    # Evaluate baseline to resolve probe cell.
    base_result = predict_fn(scenario)
    probe: tuple[int, int] | None = None
    if probe_x_m is not None and probe_y_m is not None:
        probe = _cell_index(base_result["grid"], float(probe_x_m), float(probe_y_m))
    baseline_metric = _metric(base_result, metric, probe)

    curves: dict[str, dict[str, Any]] = {}
    rankings: list[dict[str, Any]] = []
    start = time.perf_counter()
    for name, spec in params.items():
        low = float(spec["low"])
        high = float(spec["high"])
        xs = np.linspace(low, high, int(n_points)).tolist()
        ys: list[float] = []
        for x in xs:
            local = {**scenario, name: x}
            r = predict_fn(local)
            ys.append(_metric(r, metric, probe))
        delta = max(ys) - min(ys)
        curves[name] = {
            "values": xs,
            "metric": ys,
            "delta": float(delta),
            "slope_per_unit": float((ys[-1] - ys[0]) / (xs[-1] - xs[0])) if xs[-1] != xs[0] else 0.0,
        }
        rankings.append({"param": name, "delta": float(delta)})
    elapsed = time.perf_counter() - start

    rankings.sort(key=lambda r: r["delta"], reverse=True)

    return {
        "baseline_metric": float(baseline_metric),
        "metric": metric,
        "engine": engine,
        "probe_cell": list(probe) if probe is not None else None,
        "curves": curves,
        "ranking": rankings,
        "elapsed_seconds": elapsed,
    }

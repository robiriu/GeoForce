"""Agent-side tool wrappers for the GeoForce v2.0 runtime.

These functions are exposed to the Gemini orchestrator via Google ADK's
`FunctionTool`. ADK introspects each function's signature and docstring to
build the Gemini `FunctionDeclaration` automatically — keep type hints and
docstrings precise.

Each wrapper calls the underlying physics/UQ implementation in `tools/`
and returns a JSON-serializable dict shaped for LLM consumption (no full
(nx, ny) field arrays — just summary stats + an 8x8 preview).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from tools.monte_carlo import run as _mc_run
from tools.predict_solver import predict as _solver_predict
from tools.predict_surrogate import predict as _surrogate_predict
from tools.sensitivity import run as _sens_run


def _serialize_scenario_result(result: dict[str, Any]) -> dict[str, Any]:
    t = np.asarray(result["temperature"])
    p = np.asarray(result["pressure"])
    grid = result["grid"]
    stride_x = max(1, t.shape[0] // 8)
    stride_y = max(1, t.shape[1] // 8)
    return {
        "engine": result["engine"],
        "elapsed_seconds": round(float(result["elapsed_seconds"]), 4),
        "grid": grid,
        "temperature_C": {
            "shape": list(t.shape),
            "min": float(t.min()),
            "max": float(t.max()),
            "mean": float(t.mean()),
            "preview_8x8": t[::stride_x, ::stride_y].round(2).tolist(),
        },
        "pressure_MPa": {
            "shape": list(p.shape),
            "min": float(p.min() / 1.0e6),
            "max": float(p.max() / 1.0e6),
            "mean": float(p.mean() / 1.0e6),
            "preview_8x8": (p[::stride_x, ::stride_y] / 1.0e6).round(3).tolist(),
        },
    }


def _cell_value(result: dict[str, Any], x_m: float, y_m: float) -> dict[str, Any]:
    grid = result["grid"]
    i = int(round(x_m / grid["dx"] - 0.5))
    j = int(round(y_m / grid["dy"] - 0.5))
    i = int(np.clip(i, 0, grid["nx"] - 1))
    j = int(np.clip(j, 0, grid["ny"] - 1))
    return {
        "i": i,
        "j": j,
        "x_cell_center_m": (i + 0.5) * grid["dx"],
        "y_cell_center_m": (j + 0.5) * grid["dy"],
        "temperature_C": float(result["temperature"][i, j]),
        "pressure_MPa": float(result["pressure"][i, j] / 1.0e6),
    }


def _serialize_mc_result(result: dict[str, Any]) -> dict[str, Any]:
    p10 = np.asarray(result["p10"])
    p50 = np.asarray(result["p50"])
    p90 = np.asarray(result["p90"])
    sx = max(1, p50.shape[0] // 8)
    sy = max(1, p50.shape[1] // 8)
    return {
        "engine": result["engine"],
        "n_samples": result["n_samples"],
        "elapsed_seconds": round(float(result["elapsed_seconds"]), 4),
        "temperature_C": {
            "shape": list(p50.shape),
            "p10_8x8": p10[::sx, ::sy].round(2).tolist(),
            "p50_8x8": p50[::sx, ::sy].round(2).tolist(),
            "p90_8x8": p90[::sx, ::sy].round(2).tolist(),
        },
        "scalar_summary": result["scalar_summary"],
    }


def predict_solver(
    scenario: dict[str, Any],
    probe_x_m: float | None = None,
    probe_y_m: float | None = None,
) -> dict[str, Any]:
    """Run the GeoForce-Solver (implicit Darcy + energy + upwind advection).

    Use this when the user wants a physics-grounded, benchmark-validated
    answer. Slower (seconds) than the surrogate but the numerics are
    trustworthy. Returns grid metadata, summary statistics, an 8x8 preview
    of the final temperature/pressure fields, and the wall-clock runtime.

    Args:
        scenario: Reservoir scenario dict. Common keys: nx, ny, dx, dy,
            porosity, log_permeability (or permeability), T_initial (degC),
            P_initial (Pa), dt (s), n_steps, wells (list of {i, j,
            mass_rate, injection_temperature}).
        probe_x_m: Optional x-coordinate (meters) of a drill/probe point.
            If provided with probe_y_m, the result includes a ``probe``
            entry with T and P at that cell.
        probe_y_m: Optional y-coordinate (meters) for the probe point.

    Returns:
        Dict with engine, elapsed_seconds, grid, temperature_C summary,
        pressure_MPa summary, and (optionally) probe.
    """
    result = _solver_predict(scenario or {})
    payload = _serialize_scenario_result(result)
    if probe_x_m is not None and probe_y_m is not None:
        payload["probe"] = _cell_value(result, float(probe_x_m), float(probe_y_m))
    return payload


def predict_surrogate(
    scenario: dict[str, Any],
    probe_x_m: float | None = None,
    probe_y_m: float | None = None,
) -> dict[str, Any]:
    """Run the v1.1 ReservoirCNN surrogate (32x32 grid, ~10–100 ms).

    Same return schema as predict_solver. Best for parameter sweeps,
    Monte Carlo, and any scenario where speed matters more than the last
    few percent of solver fidelity.

    Args:
        scenario: Reservoir scenario dict. Same keys as predict_solver
            (the surrogate uses base_pressure and depth in place of
            P_initial; both map to the same 32x32 input encoding).
        probe_x_m: Optional drill-site x-coordinate (meters).
        probe_y_m: Optional drill-site y-coordinate (meters).

    Returns:
        Dict with engine, elapsed_seconds, grid, temperature_C summary,
        pressure_MPa summary, and (optionally) probe.
    """
    result = _surrogate_predict(scenario or {})
    payload = _serialize_scenario_result(result)
    if probe_x_m is not None and probe_y_m is not None:
        payload["probe"] = _cell_value(result, float(probe_x_m), float(probe_y_m))
    return payload


def monte_carlo(
    scenario: dict[str, Any],
    distributions: dict[str, Any],
    n_samples: int = 200,
    engine: str = "surrogate",
    seed: int = 0,
) -> dict[str, Any]:
    """Monte Carlo ensemble over parameter distributions; returns P10/P50/P90.

    Use for "how confident", "what's the range", or any P10/P50/P90
    question. Defaults to the surrogate engine (fast); pass
    ``engine="solver"`` only if you need solver fidelity and accept
    minutes-scale runtime.

    Args:
        scenario: Base reservoir scenario dict.
        distributions: Mapping ``param_name -> {dist, ...}``. Supported
            dist values: ``uniform`` ({low, high}), ``normal`` ({mean,
            std}), ``lognormal`` ({mean, std}), ``triangular`` ({low,
            mode, high}).
        n_samples: Number of Monte Carlo draws (default 200).
        engine: ``"surrogate"`` (default) or ``"solver"``.
        seed: RNG seed (default 0).

    Returns:
        Dict with engine, n_samples, elapsed_seconds, temperature_C
        (8x8 P10/P50/P90 previews), and scalar_summary.
    """
    result = _mc_run(
        scenario or {},
        distributions or {},
        n_samples=int(n_samples),
        engine=str(engine),
        seed=int(seed),
    )
    return _serialize_mc_result(result)


def sensitivity_oat(
    scenario: dict[str, Any],
    params: dict[str, Any],
    n_points: int = 5,
    engine: str = "surrogate",
    metric: str = "probe_temperature_C",
    probe_x_m: float | None = None,
    probe_y_m: float | None = None,
) -> dict[str, Any]:
    """One-at-a-time sensitivity sweep; ranks parameters by |Δmetric|.

    Use for "which parameter matters most?" or well-placement questions
    where you want to know how the answer moves with porosity vs.
    permeability vs. injection rate.

    Args:
        scenario: Base reservoir scenario dict.
        params: Mapping ``param_name -> {low, high}`` to sweep.
        n_points: Sweep points per parameter (default 5).
        engine: ``"surrogate"`` (default) or ``"solver"``.
        metric: One of ``probe_temperature_C``, ``mean_temperature_C``,
            ``min_temperature_C``, ``max_temperature_C``,
            ``mean_pressure_MPa``.
        probe_x_m: Required if metric is ``probe_temperature_C``.
        probe_y_m: Required if metric is ``probe_temperature_C``.

    Returns:
        Dict with curves (per-parameter sweep), ranking, baseline_metric,
        and elapsed_seconds.
    """
    kwargs: dict[str, Any] = {
        "engine": str(engine),
        "n_points": int(n_points),
        "metric": str(metric),
    }
    if probe_x_m is not None:
        kwargs["probe_x_m"] = float(probe_x_m)
    if probe_y_m is not None:
        kwargs["probe_y_m"] = float(probe_y_m)
    result = _sens_run(scenario or {}, params or {}, **kwargs)
    for _name, curve in result["curves"].items():
        curve["values"] = [round(float(v), 6) for v in curve["values"]]
        curve["metric"] = [round(float(m), 4) for m in curve["metric"]]
        curve["delta"] = round(float(curve["delta"]), 4)
        curve["slope_per_unit"] = round(float(curve["slope_per_unit"]), 4)
    result["baseline_metric"] = round(float(result["baseline_metric"]), 4)
    result["elapsed_seconds"] = round(float(result["elapsed_seconds"]), 4)
    return result

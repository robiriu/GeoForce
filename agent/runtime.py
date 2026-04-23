"""Claude agent runtime for GeoForce-CCHackathon.

Wires the two physics engines — `tools.predict_solver` and
`tools.predict_surrogate` — into an in-process SDK MCP server, then runs
a `ClaudeSDKClient` session that can answer geothermal questions using
those tools.

Run directly to answer Q1:

    .venv/bin/python -m agent.runtime \\
        "If I drill at x=200m, y=100m, what reservoir temperature will I hit \\
         after 1 year of 0.5 kg/s cold water reinjection at x=50m, y=100m?"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)

from tools.predict_solver import predict as _solver_predict
from tools.predict_surrogate import predict as _surrogate_predict

DEFAULT_MODEL = "claude-opus-4-6"

SYSTEM_PROMPT = """You are GeoForce, an Indonesian geothermal reservoir engineering agent.

You have two tools, both callable with a single `scenario` dict argument:

  1. `predict_solver` — runs GeoForce-Solver, a from-scratch implicit
     backward-Euler Darcy + energy (conduction + upwind advection) solver.
     Use this when the user wants a physics-grounded, benchmark-validated
     answer. Slower (seconds), but the numerics are trustworthy.

  2. `predict_surrogate` — runs the v1.1 ReservoirCNN surrogate.
     Fast (tens of ms), best for sweeps and UQ. 32x32 grid only.

Scenario dict schema (keys are optional; sensible defaults exist):
  - nx, ny (int)         grid cell counts
  - dx, dy (float, m)    cell size
  - porosity (float)
  - permeability (float, m^2)   OR  log_permeability (float, log10 m^2)
  - rho_rock, cp_rock, lam_rock  (floats, SI)
  - T_initial (float, degC)
  - P_initial (float, Pa)   [solver]   /   base_pressure (float, Pa) [surrogate]
  - depth (float, m) [surrogate]
  - dt (float, s), n_steps (int) [solver only]
  - wells: list of {i:int, j:int, mass_rate:float (kg/s, +inj, -prod),
                    injection_temperature: float (degC, required if mass_rate>0)}

When answering "if I drill at (x,y), what temperature will I hit?":
  1. Translate the user's (x, y) meters to grid cell (i, j) using dx/dy.
  2. Build a scenario dict and call `predict_solver`.
  3. Read `result["temperature"][i, j]` to get the temperature at the drill
     location after the simulated elapsed time (dt * n_steps seconds).
  4. Report the temperature, the elapsed simulated time, and any wells that
     influenced the field.

Always cite which engine you used and the elapsed wall-clock seconds.
Keep your final answer to ≤ 4 sentences unless more detail is asked for.
"""


def _serialize_scenario_result(result: dict[str, Any]) -> dict[str, Any]:
    """Turn a predict() result into a JSON-serializable summary for the model.

    Returning the full (nx, ny) array is too heavy for an LLM tool response,
    so we return grid metadata + summary statistics + a down-sampled preview.
    """
    t = np.asarray(result["temperature"])
    p = np.asarray(result["pressure"])
    grid = result["grid"]
    # 8x8 preview, bilinear-ish via slicing
    stride_x = max(1, t.shape[0] // 8)
    stride_y = max(1, t.shape[1] // 8)
    t_preview = t[::stride_x, ::stride_y].round(2).tolist()
    p_preview = (p[::stride_x, ::stride_y] / 1.0e6).round(3).tolist()  # MPa
    return {
        "engine": result["engine"],
        "elapsed_seconds": round(float(result["elapsed_seconds"]), 4),
        "grid": grid,
        "temperature_C": {
            "shape": list(t.shape),
            "min": float(t.min()),
            "max": float(t.max()),
            "mean": float(t.mean()),
            "preview_8x8": t_preview,
        },
        "pressure_MPa": {
            "shape": list(p.shape),
            "min": float(p.min() / 1.0e6),
            "max": float(p.max() / 1.0e6),
            "mean": float(p.mean() / 1.0e6),
            "preview_8x8": p_preview,
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


@tool(
    "predict_solver",
    "Run the GeoForce-Solver (implicit Darcy + energy + upwind advection) on "
    "a scenario dict. Returns grid metadata, summary stats, an 8x8 preview of "
    "the final temperature/pressure fields, and the wall-clock runtime. For a "
    "drill-site question, also pass `probe_x_m` and `probe_y_m` to get the "
    "temperature + pressure at that location.",
    {
        "scenario": dict,
        "probe_x_m": float,
        "probe_y_m": float,
    },
)
async def predict_solver_tool(args: dict[str, Any]) -> dict[str, Any]:
    scenario = args.get("scenario") or {}
    result = _solver_predict(scenario)
    payload = _serialize_scenario_result(result)
    if "probe_x_m" in args and "probe_y_m" in args:
        payload["probe"] = _cell_value(
            result, float(args["probe_x_m"]), float(args["probe_y_m"])
        )
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


@tool(
    "predict_surrogate",
    "Run the v1.1 ReservoirCNN surrogate on a scenario dict. 32x32 grid, "
    "fast (~10-100ms). Returns the same schema as predict_solver. For a "
    "drill-site question, pass `probe_x_m` and `probe_y_m`.",
    {
        "scenario": dict,
        "probe_x_m": float,
        "probe_y_m": float,
    },
)
async def predict_surrogate_tool(args: dict[str, Any]) -> dict[str, Any]:
    scenario = args.get("scenario") or {}
    result = _surrogate_predict(scenario)
    payload = _serialize_scenario_result(result)
    if "probe_x_m" in args and "probe_y_m" in args:
        payload["probe"] = _cell_value(
            result, float(args["probe_x_m"]), float(args["probe_y_m"])
        )
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def _load_env() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(repo_root / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.stderr.write("ANTHROPIC_API_KEY missing (expected in .env)\n")
        sys.exit(2)


def build_options() -> ClaudeAgentOptions:
    mcp_server = create_sdk_mcp_server(
        name="geoforce-tools",
        tools=[predict_solver_tool, predict_surrogate_tool],
    )
    return ClaudeAgentOptions(
        model=DEFAULT_MODEL,
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"geoforce": mcp_server},
        allowed_tools=[
            "mcp__geoforce__predict_solver",
            "mcp__geoforce__predict_surrogate",
        ],
        max_turns=10,
    )


async def answer(query: str, *, verbose: bool = True) -> str:
    """Run one query end-to-end and return the final assistant text."""
    _load_env()
    options = build_options()
    final_text_parts: list[str] = []

    async with ClaudeSDKClient(options=options) as client:
        await client.query(query)
        async for message in client.receive_response():
            if verbose and isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)
                    elif isinstance(block, ToolUseBlock):
                        print(f"\n[tool: {block.name}]", flush=True)
            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        final_text_parts.append(block.text)
            if isinstance(message, ResultMessage):
                if verbose:
                    print("", flush=True)
                if not final_text_parts and message.result:
                    final_text_parts.append(message.result)
                break

    return "".join(final_text_parts) if final_text_parts else ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Answer a geothermal question with the GeoForce agent.")
    parser.add_argument("query", nargs="+", help="Natural-language question.")
    parser.add_argument("--quiet", action="store_true", help="Suppress streaming output.")
    args = parser.parse_args()
    q = " ".join(args.query)
    asyncio.run(answer(q, verbose=not args.quiet))


if __name__ == "__main__":
    main()

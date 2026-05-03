"""Vertex AI Gemini agent runtime for GeoForce v2.0.

Built on Google's Agent Development Kit (ADK). The runtime exposes the
four GeoForce tools (predict_solver, predict_surrogate, monte_carlo,
sensitivity_oat) to a Gemini orchestrator running on Vertex AI under the
GenAI App Builder credit (project ``forcex-studio``).

The 8-subagent decomposition described in `.claude/agents/*.md` is
preserved as authoritative role definitions, but Phase 0 instantiates a
single root agent (planner) with the 4 tools attached directly. Splitting
into 8 live LlmAgents multiplies LLM calls per query and is deferred to
Phase 6 once the v2.0 stack is fully validated.

Run a one-off query:

    .venv/bin/python -m agent.runtime \
        "If I drill at x=200m, y=100m, what reservoir temperature will I hit \
         after 1 year of 0.5 kg/s cold water reinjection at x=50m, y=100m?"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from agent import tools as geoforce_tools

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_LOCATION = "asia-southeast1"
DEFAULT_PROJECT = "forcex-studio"

APP_NAME = "geoforce"
DEFAULT_USER_ID = "geoforce-cli"

SYSTEM_INSTRUCTION = """You are GeoForce, an Indonesian geothermal reservoir engineering agent.

You orchestrate four tools to answer drilling, sustainability, and well-placement questions:

  1. predict_solver — implicit Darcy + energy + upwind advection solver.
     Physics-grounded, benchmark-validated. Slower (seconds). Use when the
     user wants a trustworthy numerical answer.

  2. predict_surrogate — v1.1 ReservoirCNN surrogate. 32x32 grid, ~10-100 ms.
     Use for sweeps, UQ, and speed-sensitive answers.

  3. monte_carlo — ensemble over parameter distributions. Returns P10/P50/P90
     fields and per-draw scalar summaries. Defaults to the surrogate engine.
     Use for "how confident", "P10/P50/P90", or "what's the range".

  4. sensitivity_oat — one-at-a-time parameter sweep. Ranks parameters by
     how much they move a chosen metric. Use for "which parameter matters
     most?" and well-placement questions.

Scenario dict schema (keys are optional; defaults exist):
  - nx, ny (int): grid cell counts
  - dx, dy (float, m): cell size
  - porosity (float)
  - permeability (float, m^2) OR log_permeability (float, log10 m^2)
  - rho_rock, cp_rock, lam_rock (floats, SI)
  - T_initial (float, degC)
  - P_initial (float, Pa)  [solver]  or  base_pressure (float, Pa) and
    depth (float, m)  [surrogate]
  - dt (float, s), n_steps (int)  [solver only]
  - wells: list of {i:int, j:int, mass_rate:float (kg/s, +inj/-prod),
                    injection_temperature:float (degC, required if injecting)}

When answering "if I drill at (x, y), what temperature will I hit?":
  1. Translate (x, y) meters to grid cell (i, j) using dx/dy.
  2. Build a scenario dict and call predict_solver with probe_x_m and
     probe_y_m.
  3. Read result["probe"]["temperature_C"] for the answer.
  4. Cite which engine you used and the elapsed wall-clock seconds.

Keep your final answer to ≤ 4 sentences unless more detail is asked.
"""


def _load_env() -> None:
    """Load .env, validate Vertex credentials, and export ADK env vars."""
    load_dotenv(REPO_ROOT / ".env")

    sa_key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not sa_key or not Path(sa_key).is_file():
        sys.stderr.write(
            "GOOGLE_APPLICATION_CREDENTIALS missing or file not found "
            "(expected in .env, pointing at the Vertex SA key).\n"
        )
        sys.exit(2)

    project = os.environ.get("GCP_PROJECT", DEFAULT_PROJECT)
    location = os.environ.get("GCP_LOCATION", DEFAULT_LOCATION)

    # ADK / google-genai pick up Vertex routing from these three env vars.
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    os.environ["GOOGLE_CLOUD_LOCATION"] = location


def build_agent():
    """Construct the root LlmAgent with the four GeoForce tools attached.

    Returns the ADK LlmAgent. Imported lazily so module import doesn't
    require ADK to be installed (e.g., for unit tests of helpers).
    """
    from google.adk.agents import LlmAgent

    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    return LlmAgent(
        name="planner",
        model=model,
        description=(
            "GeoForce orchestrator — answers Indonesian geothermal "
            "reservoir engineering questions using physics solver, "
            "ML surrogate, Monte Carlo, and sensitivity tools."
        ),
        instruction=SYSTEM_INSTRUCTION,
        tools=[
            geoforce_tools.predict_solver,
            geoforce_tools.predict_surrogate,
            geoforce_tools.monte_carlo,
            geoforce_tools.sensitivity_oat,
        ],
    )


def build_runner():
    """Build an ADK Runner with an in-memory session service."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    return Runner(
        agent=build_agent(),
        app_name=APP_NAME,
        session_service=InMemorySessionService(),
    )


async def answer(query: str, *, verbose: bool = True) -> str:
    """Run one query end-to-end and return the final assistant text.

    Creates a fresh ADK session per call. For multi-turn use, see
    agent.api which keeps sessions alive across HTTP requests.
    """
    from google.genai import types as genai_types

    _load_env()
    runner = build_runner()
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=DEFAULT_USER_ID
    )
    user_message = genai_types.Content(
        role="user", parts=[genai_types.Part(text=query)]
    )

    final_text_parts: list[str] = []
    async for event in runner.run_async(
        user_id=DEFAULT_USER_ID,
        session_id=session.id,
        new_message=user_message,
    ):
        if not event.content or not event.content.parts:
            continue
        is_final = event.is_final_response()
        for part in event.content.parts:
            if getattr(part, "text", None):
                if verbose:
                    print(part.text, end="", flush=True)
                if is_final:
                    final_text_parts.append(part.text)
            if getattr(part, "function_call", None) and verbose:
                print(f"\n[tool: {part.function_call.name}]", flush=True)

    if verbose:
        print("", flush=True)
    return "".join(final_text_parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Answer a geothermal question with the GeoForce agent.",
    )
    parser.add_argument("query", nargs="+", help="Natural-language question.")
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress streaming output."
    )
    args = parser.parse_args()
    text = asyncio.run(answer(" ".join(args.query), verbose=not args.quiet))
    if args.quiet:
        print(text)


if __name__ == "__main__":
    main()

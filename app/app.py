"""Streamlit fallback UI for GeoForce.

Run with:

    .venv/bin/streamlit run app/app.py

Shape:
  - Sidebar: scenario picker loaded from demo/scenarios.yaml.
  - Main pane: agent query box + live agent trace + side-by-side
    solver/surrogate heatmaps for the chosen scenario.

Kept intentionally terse (<200 lines). The primary UI is the React
dashboard; this is the always-working escape hatch.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np
import streamlit as st
import yaml
from matplotlib import pyplot as plt

from tools.predict_solver import predict as solver_predict
from tools.predict_surrogate import predict as surrogate_predict

REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_PATH = REPO_ROOT / "demo" / "scenarios.yaml"

st.set_page_config(page_title="GeoForce Agent", layout="wide")
st.title("GeoForce — dual-engine geothermal agent")
st.caption(
    "Opus 4.7 agent orchestrating GeoForce-Solver (implicit Darcy + energy) "
    "and the v1.1 ReservoirCNN surrogate."
)


@st.cache_data
def _load_scenarios() -> list[dict]:
    if not SCENARIOS_PATH.exists():
        return []
    with SCENARIOS_PATH.open() as f:
        data = yaml.safe_load(f) or {}
    return data.get("scenarios", [])


scenarios = _load_scenarios()
scenario_ids = [s["id"] for s in scenarios]

with st.sidebar:
    st.header("Scenario")
    sel_id = st.selectbox("Pick a demo scenario", scenario_ids, index=0)
    chosen = next(s for s in scenarios if s["id"] == sel_id)
    st.markdown(f"**Question**: {chosen['question']}")
    engine_choice = st.radio(
        "Engine",
        options=["both", "solver", "surrogate"],
        index=0,
        help="Run one or both engines.",
    )
    run_btn = st.button("Run scenario", type="primary")

    st.divider()
    st.header("Agent")
    free_query = st.text_area(
        "Or ask the agent directly",
        value=chosen["question"],
        height=120,
    )
    agent_btn = st.button("Ask agent")


def _plot_field(ax, field: np.ndarray, grid: dict, title: str, cmap: str) -> None:
    nx, ny = grid["nx"], grid["ny"]
    dx, dy = grid["dx"], grid["dy"]
    im = ax.imshow(
        field.T,
        origin="lower",
        extent=[0, nx * dx, 0, ny * dy],
        cmap=cmap,
        aspect="equal",
    )
    ax.set_title(title)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    plt.colorbar(im, ax=ax, shrink=0.85)


if run_btn:
    scenario_dict = chosen["scenario"]
    cols = st.columns(2)
    with st.spinner("Running engines…"):
        if engine_choice in ("both", "solver"):
            sol = solver_predict(scenario_dict)
            with cols[0]:
                st.subheader(f"Solver ({sol['elapsed_seconds']:.2f}s)")
                fig, ax = plt.subplots(figsize=(5, 3.5))
                _plot_field(ax, np.asarray(sol["temperature"]), sol["grid"], "T (°C)", "inferno")
                st.pyplot(fig, use_container_width=True)
                st.caption(
                    f"T range: {sol['temperature'].min():.1f}–{sol['temperature'].max():.1f} °C | "
                    f"P range: {sol['pressure'].min()/1e6:.2f}–{sol['pressure'].max()/1e6:.2f} MPa"
                )
        if engine_choice in ("both", "surrogate"):
            sur = surrogate_predict(scenario_dict)
            with cols[1 if engine_choice == "both" else 0]:
                st.subheader(f"Surrogate ({sur['elapsed_seconds']:.2f}s)")
                fig, ax = plt.subplots(figsize=(5, 3.5))
                _plot_field(ax, np.asarray(sur["temperature"]), sur["grid"], "T (°C)", "inferno")
                st.pyplot(fig, use_container_width=True)
                st.caption(
                    f"T range: {sur['temperature'].min():.1f}–{sur['temperature'].max():.1f} °C"
                )


if agent_btn:
    st.subheader("Agent trace")
    trace_box = st.empty()
    text_buf: list[str] = []
    tool_log: list[str] = []

    async def _run_agent(query: str) -> None:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeSDKClient,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
        )

        from agent.runtime import _load_env, build_options

        _load_env()
        options = build_options()
        async with ClaudeSDKClient(options=options) as client:
            await client.query(query)
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            text_buf.append(block.text)
                        elif isinstance(block, ToolUseBlock):
                            tool_log.append(f"→ {block.name}")
                    trace_box.markdown(
                        "\n\n".join(
                            [
                                "**Tools called:**  " + (" ".join(tool_log) if tool_log else "(none yet)"),
                                "**Assistant:**\n\n" + "".join(text_buf),
                            ]
                        )
                    )
                elif isinstance(msg, ResultMessage):
                    break

    with st.spinner("Agent thinking…"):
        try:
            asyncio.run(_run_agent(free_query))
        except Exception as exc:  # noqa: BLE001
            st.error(f"Agent error: {exc}")

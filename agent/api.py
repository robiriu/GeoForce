"""FastAPI + SSE backend for the GeoForce dashboard / Streamlit fallback.

Endpoints:

  GET  /health                 → { "ok": true }
  GET  /scenarios              → demo/scenarios.yaml entries
  POST /predict                → runs solver and/or surrogate, returns fields
  POST /query                  → streams Server-Sent Events from the agent:
                                   event: text     data: {"text": "..."}
                                   event: tool     data: {"name": "...", "input": {...}}
                                   event: result   data: {"final_text": "...", "stop_reason": "..."}
                                   event: error    data: {"message": "..."}

Run with:

    .venv/bin/uvicorn agent.api:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Literal
from uuid import uuid4

import numpy as np
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from agent.runtime import _load_env, build_options
from tools.predict_solver import predict as solver_predict
from tools.predict_surrogate import predict as surrogate_predict

REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_PATH = REPO_ROOT / "demo" / "scenarios.yaml"

app = FastAPI(title="GeoForce Agent API", version="0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    scenario_id: str | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True}


@app.get("/scenarios")
def scenarios() -> dict[str, Any]:
    if not SCENARIOS_PATH.exists():
        return {"scenarios": []}
    with SCENARIOS_PATH.open() as f:
        data = yaml.safe_load(f) or {}
    return data


async def _stream_agent(query: str) -> AsyncGenerator[dict[str, str], None]:
    _load_env()
    options = build_options()
    final_parts: list[str] = []
    final_stop: str | None = None

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(query)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            final_parts.append(block.text)
                            yield {
                                "event": "text",
                                "data": json.dumps({"text": block.text}),
                            }
                        elif isinstance(block, ToolUseBlock):
                            yield {
                                "event": "tool",
                                "data": json.dumps(
                                    {"name": block.name, "input": block.input}
                                ),
                            }
                elif isinstance(message, ResultMessage):
                    final_stop = getattr(message, "stop_reason", None)
                    if not final_parts and message.result:
                        final_parts.append(message.result)
                    break
    except Exception as exc:  # noqa: BLE001
        yield {"event": "error", "data": json.dumps({"message": str(exc)})}
        return

    yield {
        "event": "result",
        "data": json.dumps(
            {"final_text": "".join(final_parts), "stop_reason": final_stop}
        ),
    }


class PredictRequest(BaseModel):
    scenario_id: str | None = None
    scenario: dict[str, Any] | None = None
    engine: Literal["both", "solver", "surrogate"] = "both"


def _serialize_field(result: dict[str, Any]) -> dict[str, Any]:
    t = np.asarray(result["temperature"])
    p = np.asarray(result["pressure"])
    return {
        "grid": result["grid"],
        "temperature": t.tolist(),
        "pressure": p.tolist(),
        "t_min": float(t.min()),
        "t_max": float(t.max()),
        "p_min_MPa": float(p.min()) / 1.0e6,
        "p_max_MPa": float(p.max()) / 1.0e6,
        "elapsed_seconds": float(result.get("elapsed_seconds", 0.0)),
    }


@app.post("/predict")
def predict(req: PredictRequest) -> dict[str, Any]:
    """Run one or both engines on a scenario and return field arrays.

    Accepts either ``scenario_id`` (pulled from demo/scenarios.yaml) or
    an inline ``scenario`` dict. Returns solver and/or surrogate results
    with temperature/pressure arrays suitable for client-side heatmaps.
    """
    scenario: dict[str, Any] | None = req.scenario
    if scenario is None and req.scenario_id:
        data = scenarios()
        match = next(
            (s for s in data.get("scenarios", []) if s.get("id") == req.scenario_id),
            None,
        )
        if not match:
            raise HTTPException(404, f"scenario_id {req.scenario_id!r} not found")
        scenario = match.get("scenario")
    if not scenario:
        raise HTTPException(400, "scenario or scenario_id required")

    out: dict[str, Any] = {"engine": req.engine}
    if req.engine in ("both", "solver"):
        out["solver"] = _serialize_field(solver_predict(scenario))
    if req.engine in ("both", "surrogate"):
        out["surrogate"] = _serialize_field(surrogate_predict(scenario))
    return out


@app.post("/query")
async def query(req: QueryRequest) -> EventSourceResponse:
    """Stream the agent response as SSE.

    If ``scenario_id`` is provided, we prepend the matching question from
    demo/scenarios.yaml so the Streamlit/React client can fire-and-forget
    a preset scenario card.
    """
    prompt = req.query
    if req.scenario_id:
        data = scenarios()
        match = next(
            (s for s in data.get("scenarios", []) if s.get("id") == req.scenario_id),
            None,
        )
        if match and match.get("question"):
            prompt = f"{match['question']}\n\nUser override: {req.query}" if req.query else match["question"]

    return EventSourceResponse(_stream_agent(prompt))


# ---- Multi-turn sessions ----------------------------------------------------
# A "session" holds one long-lived ClaudeSDKClient so the dashboard can have a
# real chat with the agent — the model sees prior turns + tool results. Each
# session has a per-session asyncio.Lock so two concurrent /query calls don't
# interleave on the same transport. Sessions idle > TTL are reaped.

SESSION_TTL_SEC = 600  # 10 min idle
SESSION_CAP = 32  # evict oldest when full


@dataclass
class _Session:
    client: ClaudeSDKClient
    stack: AsyncExitStack
    last_used: float
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


SESSIONS: dict[str, _Session] = {}


async def _open_session() -> str:
    _load_env()
    stack = AsyncExitStack()
    try:
        client = await stack.enter_async_context(ClaudeSDKClient(options=build_options()))
    except Exception:
        await stack.aclose()
        raise
    sid = uuid4().hex[:16]
    SESSIONS[sid] = _Session(client=client, stack=stack, last_used=time.time())
    return sid


async def _close_session(sid: str) -> None:
    sess = SESSIONS.pop(sid, None)
    if sess is None:
        return
    try:
        await sess.stack.aclose()
    except Exception:  # noqa: BLE001 — best-effort teardown
        pass


async def _reap_sessions() -> None:
    while True:
        try:
            now = time.time()
            stale = [sid for sid, s in list(SESSIONS.items()) if now - s.last_used > SESSION_TTL_SEC]
            for sid in stale:
                await _close_session(sid)
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(60)


@app.on_event("startup")
async def _startup() -> None:
    app.state._reaper = asyncio.create_task(_reap_sessions())


@app.post("/sessions")
async def create_session() -> dict[str, str]:
    """Open a multi-turn session. Returns a session_id the client uses
    for subsequent /sessions/{id}/query calls."""
    if len(SESSIONS) >= SESSION_CAP:
        oldest = min(SESSIONS, key=lambda k: SESSIONS[k].last_used)
        await _close_session(oldest)
    try:
        sid = await _open_session()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"failed to open session: {exc}") from exc
    return {"session_id": sid}


@app.delete("/sessions/{sid}")
async def drop_session(sid: str) -> dict[str, bool]:
    await _close_session(sid)
    return {"ok": True}


async def _stream_session(
    sess: _Session, prompt: str
) -> AsyncGenerator[dict[str, str], None]:
    # Serialize queries on the same session; SDK transport isn't safe for
    # concurrent .query() calls.
    async with sess.lock:
        sess.last_used = time.time()
        final_parts: list[str] = []
        final_stop: str | None = None
        try:
            await sess.client.query(prompt)
            async for message in sess.client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            final_parts.append(block.text)
                            yield {
                                "event": "text",
                                "data": json.dumps({"text": block.text}),
                            }
                        elif isinstance(block, ToolUseBlock):
                            yield {
                                "event": "tool",
                                "data": json.dumps(
                                    {"name": block.name, "input": block.input}
                                ),
                            }
                elif isinstance(message, ResultMessage):
                    final_stop = getattr(message, "stop_reason", None)
                    if not final_parts and message.result:
                        final_parts.append(message.result)
                    break
        except Exception as exc:  # noqa: BLE001
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}
            return
        sess.last_used = time.time()
        yield {
            "event": "result",
            "data": json.dumps(
                {"final_text": "".join(final_parts), "stop_reason": final_stop}
            ),
        }


@app.post("/sessions/{sid}/query")
async def session_query(sid: str, req: QueryRequest) -> EventSourceResponse:
    """Stream a turn in an existing multi-turn session as SSE."""
    sess = SESSIONS.get(sid)
    if sess is None:
        raise HTTPException(404, f"session {sid!r} not found or expired")
    prompt = req.query
    if req.scenario_id:
        data = scenarios()
        match = next(
            (s for s in data.get("scenarios", []) if s.get("id") == req.scenario_id),
            None,
        )
        if match and match.get("question"):
            prompt = (
                f"{match['question']}\n\nUser override: {req.query}"
                if req.query
                else match["question"]
            )
    return EventSourceResponse(_stream_session(sess, prompt))


# ---- Serve built React dashboard (if present) -------------------------------
# In dev, the dashboard runs on Vite (http://localhost:5173) and proxies /api
# to us. In docker/prod we bake `dashboard/dist/` into the image and serve it
# at the same origin so there's only one port to expose.
_DIST = REPO_ROOT / "dashboard" / "dist"
if _DIST.is_dir():
    app.mount(
        "/assets", StaticFiles(directory=_DIST / "assets"), name="assets"
    )

    @app.get("/")
    def _spa_index() -> FileResponse:
        return FileResponse(_DIST / "index.html")

"""FastAPI + SSE backend for the GeoForce dashboard / Streamlit fallback.

Endpoints:

  GET    /health                 → { "ok": true }
  GET    /scenarios              → demo/scenarios.yaml entries
  POST   /predict                → runs solver and/or surrogate, returns fields
  POST   /query                  → streams Server-Sent Events from the agent:
                                     event: text     data: {"text": "..."}
                                     event: tool     data: {"name": "...", "input": {...}}
                                     event: result   data: {"final_text": "...", "stop_reason": "..."}
                                     event: error    data: {"message": "..."}
  POST   /sessions               → open a multi-turn session (returns session_id)
  DELETE /sessions/{sid}         → close a session
  POST   /sessions/{sid}/query   → stream a turn in an existing session

The SSE event shape is stable across LLM-provider migrations (CLAUDE.md §2,
AGENTS.md principle #6). The dashboard depends on it.

Run with:

    .venv/bin/uvicorn agent.api:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import json
import time
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
from google.genai import types as genai_types
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent.runtime import APP_NAME, _load_env, build_runner
from tools.predict_solver import predict as solver_predict
from tools.predict_surrogate import predict as surrogate_predict

REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_PATH = REPO_ROOT / "demo" / "scenarios.yaml"

ANON_USER_ID = "geoforce-anon"

app = FastAPI(title="GeoForce Agent API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Single ADK Runner shared across the process — built lazily on first use so
# import-time test code (and the no-LLM /predict endpoint) doesn't require
# Vertex credentials.
_RUNNER = None


def _runner():
    global _RUNNER
    if _RUNNER is None:
        _load_env()
        _RUNNER = build_runner()
    return _RUNNER


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


def _user_message(text: str) -> genai_types.Content:
    return genai_types.Content(role="user", parts=[genai_types.Part(text=text)])


async def _stream_events(
    user_id: str, session_id: str, prompt: str
) -> AsyncGenerator[dict[str, str], None]:
    """Run one agent turn and yield SSE-shaped dicts.

    Translates ADK Event stream into the v0.2 SSE event names so the
    dashboard doesn't need to change.
    """
    final_parts: list[str] = []
    final_stop: str | None = None

    try:
        runner = _runner()
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=_user_message(prompt),
        ):
            if not event.content or not event.content.parts:
                continue
            is_final = event.is_final_response()
            for part in event.content.parts:
                text = getattr(part, "text", None)
                if text:
                    if is_final:
                        final_parts.append(text)
                    yield {
                        "event": "text",
                        "data": json.dumps({"text": text}),
                    }
                fc = getattr(part, "function_call", None)
                if fc and fc.name:
                    args = dict(fc.args) if fc.args else {}
                    yield {
                        "event": "tool",
                        "data": json.dumps({"name": fc.name, "input": args}),
                    }
            if is_final:
                final_stop = "stop"
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


def _resolve_prompt(query: str, scenario_id: str | None) -> str:
    if not scenario_id:
        return query
    data = scenarios()
    match = next(
        (s for s in data.get("scenarios", []) if s.get("id") == scenario_id),
        None,
    )
    if match and match.get("question"):
        if query:
            return f"{match['question']}\n\nUser override: {query}"
        return match["question"]
    return query


@app.post("/query")
async def query(req: QueryRequest) -> EventSourceResponse:
    """Stream a single-turn agent response as SSE."""
    prompt = _resolve_prompt(req.query, req.scenario_id)
    runner = _runner()
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=ANON_USER_ID
    )
    return EventSourceResponse(
        _stream_events(ANON_USER_ID, session.id, prompt)
    )


# ---- Multi-turn sessions ----------------------------------------------------
# A "session" is an ADK conversation: the planner agent sees prior turns and
# tool results within the session. We keep a thin _Session wrapper so we can
# hold a per-session asyncio.Lock (preventing interleaved /query calls) and a
# TTL reaper. ADK's InMemorySessionService stores the actual chat history.

SESSION_TTL_SEC = 600
SESSION_CAP = 32


@dataclass
class _Session:
    adk_session_id: str
    user_id: str
    last_used: float
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


SESSIONS: dict[str, _Session] = {}


async def _open_session() -> str:
    runner = _runner()
    user_id = uuid4().hex[:12]
    adk_session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=user_id
    )
    sid = uuid4().hex[:16]
    SESSIONS[sid] = _Session(
        adk_session_id=adk_session.id,
        user_id=user_id,
        last_used=time.time(),
    )
    return sid


async def _close_session(sid: str) -> None:
    sess = SESSIONS.pop(sid, None)
    if sess is None:
        return
    runner = _runner()
    try:
        await runner.session_service.delete_session(
            app_name=APP_NAME,
            user_id=sess.user_id,
            session_id=sess.adk_session_id,
        )
    except Exception:  # noqa: BLE001 — best-effort teardown
        pass


async def _reap_sessions() -> None:
    while True:
        try:
            now = time.time()
            stale = [
                sid
                for sid, s in list(SESSIONS.items())
                if now - s.last_used > SESSION_TTL_SEC
            ]
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
    async with sess.lock:
        sess.last_used = time.time()
        async for event in _stream_events(sess.user_id, sess.adk_session_id, prompt):
            yield event
        sess.last_used = time.time()


@app.post("/sessions/{sid}/query")
async def session_query(sid: str, req: QueryRequest) -> EventSourceResponse:
    sess = SESSIONS.get(sid)
    if sess is None:
        raise HTTPException(404, f"session {sid!r} not found or expired")
    prompt = _resolve_prompt(req.query, req.scenario_id)
    return EventSourceResponse(_stream_session(sess, prompt))


# ---- Serve built React dashboard (if present) -------------------------------
_DIST = REPO_ROOT / "dashboard" / "dist"
if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/")
    def _spa_index() -> FileResponse:
        return FileResponse(_DIST / "index.html")

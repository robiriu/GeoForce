# GeoForce — Project Plan

**Author:** Robi Dany Riupassa (ForceX AI)
**Repo:** https://github.com/robiriu/GeoForce

---

## 1. Thesis

> *"A minimal, open-source geothermal solver built from scratch — gravity-aware, single-phase, IAPWS-IF97 water properties, validated against analytical benchmarks. This is step 1 toward removing the TOUGH3 license barrier for Indonesian researchers. We acknowledge it is not TOUGH3. It is a transparent blueprint that a small team — or a team of agents — can extend."*

Two orchestrated engines:

| Engine | Role |
|---|---|
| **GeoForce-Solver** (new) | Ground-truth-ish single-phase solver, built by agents |
| **GeoForce v1.1 CNN** (existing) | Fast surrogate for Monte Carlo + sensitivity, deployed in ForceX-AI |

A team of Claude subagents orchestrates both tools to answer real geothermal engineering questions.

## 2. Scope — In / Out

### IN

1. **GeoForce-Solver** (NEW, Python)
   - 2D vertical section (e.g., 50×30 cells), gravity-aware
   - Single-phase water with **IAPWS-IF97** for ρ(T,P), μ(T), h(T,P)
   - Implicit backward-Euler, coupled Darcy + energy conservation
   - Well source terms (injection, production)
   - Validated against **Theis** (pressure) and **1D conduction** (temperature) analytical solutions

2. **GeoForce v1.1 surrogate** (PORTED)
   - `ReservoirCNN` + `geoforce_cnn_v1.1.pt` copied from ForceX-AI
   - Inference ≤5 ms, normalization constants + 6-channel encoding preserved

3. **Multi-agent system** (`.claude/agents/` + `claude-agent-sdk` runtime)
   - 7 subagents: planner, geologist, solver-engineer, surrogate-operator, uq-specialist, visualizer, reviewer
   - Parallel execution via async sdk calls where independent
   - Full Claude Code tooling: CLAUDE.md, AGENTS.md, skills, slash commands, hooks

4. **Answer 3 engineering questions** (from `initial/REAL-ENGINEERING-QUESTIONS.md`, exploration phase)
   - Q1: "If I drill at (x, y), what temperature will I hit?"
   - Q2: "How many MW can this reservoir sustain for 20 years?"
   - Q3: "Where should I place the next 3 production wells?"

5. **Dual-surface demo UI** — primary: React dashboard styled with Anthropic's visual design language (warm paper bg, serif headings, Clay accent, live agent-trace stream via SSE, dual-engine plot cards, UQ overlay). Fallback: Streamlit single-page app. Dashboard deployed to HuggingFace Spaces as a Dockerfile space.

6. **Validation cameo** — NREL Brady Hot Springs open dataset comparison

7. **README + `v0.1` tag**

### OUT (explicitly cut)

- **Two-phase physics (steam + liquid).** A minimal STUB (saturation variable plumbing, no flash logic) is permitted only if the Phase 1 solver is green and a v0.1 release has been tagged. Real two-phase is post-v0.1.
- 3D grids — vertical-section 2D only
- TOUGH3 / TOUGH2 / Waiwera — any live external simulator install
- Retraining the CNN
- 3D visualization (three.js, deck.gl)
- PostgreSQL / auth / billing / multi-tenant
- Q4–Q9 engineering questions — require production-state tracking not yet implemented

## 3. Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Streamlit UI  (app/app.py)                                      │
│  - Query box (natural language)                                  │
│  - Agent trace panel (live)                                      │
│  - Side-by-side: Solver field plot │ Surrogate field plot        │
│  - UQ band overlay (P10/P50/P90)                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PLANNER AGENT  (.claude/agents/planner.md)                      │
│  Decomposes query → dispatches to specialists (parallel when     │
│  independent) → aggregates → returns structured answer           │
└──────────────────────────┬──────────────────────────────────────┘
        ┌─────────────┬────┴────┬──────────────┬────────────────┐
        ▼             ▼         ▼              ▼                ▼
   ┌─────────┐  ┌─────────┐ ┌──────────┐  ┌────────────┐  ┌──────────┐
   │GEOLOGIST│  │SOLVER-  │ │SURROGATE-│  │UQ-         │  │VISUALIZER│
   │         │  │ENGINEER │ │OPERATOR  │  │SPECIALIST  │  │          │
   │validate │  │GeoForce-Solver│ │v1.1 CNN  │  │Monte Carlo │  │matplotlib│
   │params   │  │builds & │ │inference │  │+ sensitivity│ │heatmaps  │
   │         │  │runs     │ │wrapper   │  │            │  │+ uq bands│
   └─────────┘  └─────────┘ └──────────┘  └────────────┘  └──────────┘
                                          │
                                          ▼
                                    ┌──────────┐
                                    │ REVIEWER │
                                    │          │
                                    │physics   │
                                    │sanity    │
                                    │check     │
                                    └──────────┘
```

### Project layout

```
GeoForce/
├── CLAUDE.md                       # project-wide Claude Code instructions
├── AGENTS.md                       # visible map of agents + skills + flows
├── PROJECT-PLAN.md                 # this file
├── PROGRESS.md                     # live task tracking
├── README.md
├── pyproject.toml                  # deps
├── .env.example
├── .mcp.json                       # (optional) MCP server exposing tools
├── initial/                        # seed docs — frozen
├── .claude/
│   ├── settings.json               # permissions, model, hooks
│   ├── agents/
│   │   ├── planner.md
│   │   ├── geologist.md
│   │   ├── solver-engineer.md
│   │   ├── surrogate-operator.md
│   │   ├── uq-specialist.md
│   │   ├── visualizer.md
│   │   └── reviewer.md
│   ├── skills/
│   │   ├── iapws97-water/SKILL.md
│   │   ├── monte-carlo-uq/SKILL.md
│   │   ├── field-visualization/SKILL.md
│   │   └── analytical-benchmarks/SKILL.md
│   ├── commands/
│   │   ├── query.md
│   │   ├── validate-solver.md
│   │   ├── parallel-mc.md
│   │   └── demo.md
│   └── hooks/
│       └── post_write_pytest.sh    # auto-run tests after edits to solver/
├── solver/                         # GeoForce-Solver
│   ├── __init__.py
│   ├── grid.py                     # 2D vertical section mesh
│   ├── properties.py               # IAPWS-IF97 wrappers
│   ├── darcy.py                    # pressure solver
│   ├── energy.py                   # heat solver
│   ├── coupled.py                  # implicit coupled step
│   ├── wells.py                    # source terms
│   └── benchmarks/
│       ├── theis.py                # analytical
│       └── conduction_1d.py        # analytical
├── surrogate/                      # v1.1 CNN ported from ForceX-AI
│   ├── reservoir_cnn.py
│   ├── encoding.py
│   └── weights/geoforce_cnn_v1.1.pt
├── tools/                          # shared tools callable by agents
│   ├── predict_solver.py
│   ├── predict_surrogate.py
│   ├── monte_carlo.py
│   ├── sensitivity.py
│   └── visualize.py
├── agent/                          # runtime agent orchestration
│   ├── runtime.py                  # claude-agent-sdk entry
│   ├── subagents.py                # programmatic subagent loader
│   └── prompts.py
├── app/
│   └── app.py                      # Streamlit fallback (<200 lines)
├── dashboard/                      # React + Vite + TS, Claude design
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── styles/tokens.css       # Claude design tokens
│       ├── styles/global.css
│       ├── components/
│       │   ├── Header.tsx
│       │   ├── QueryInput.tsx
│       │   ├── AgentTrace.tsx
│       │   ├── FieldPlot.tsx
│       │   ├── UQOverlay.tsx
│       │   ├── ScenarioPicker.tsx
│       │   └── AnswerPanel.tsx
│       └── api/client.ts           # SSE consumer
├── Dockerfile                      # multi-stage: Node build + Python runtime
├── tests/
│   ├── test_solver_theis.py
│   ├── test_solver_conduction.py
│   ├── test_surrogate_smoke.py
│   └── test_agent_smoke.py
└── demo/
    ├── scenarios.yaml
    ├── screencast.mp4              # 90s demo
    └── brady_validation.ipynb      # validation cameo
```

## 4. Development Phases

### Phase 1 — Engine Build

**Surrogate port + Claude scaffolding**
- [ ] Copy v1.1 weights + `ReservoirCNN` class + encoding into `surrogate/`
- [ ] `tests/test_surrogate_smoke.py` — load + predict + shape assert
- [ ] Confirm `.claude/` scaffolding loads correctly (subagents discovered)
- [ ] `pyproject.toml` installs clean in a fresh venv

**GeoForce-Solver — built by agent team**
- [ ] Orchestrate solver-engineer + geologist + reviewer agents
- [ ] `solver/properties.py` — IAPWS-IF97 wrappers (use `iapws` PyPI package)
- [ ] `solver/grid.py` — 2D vertical section, structured grid
- [ ] `solver/darcy.py` + `solver/energy.py` — single-equation solvers first
- [ ] `solver/coupled.py` — implicit backward-Euler coupled step
- [ ] `solver/wells.py` — source/sink terms
- [ ] `solver/benchmarks/theis.py` + `conduction_1d.py`
- [ ] `tests/test_solver_theis.py` + `test_solver_conduction.py` pass

**Solver validation + agent wiring**
- [ ] Both Theis and 1D conduction tests green (fallback: drop solver, ship surrogate-only — see §5)
- [ ] `tools/predict_solver.py` + `tools/predict_surrogate.py` unified interface
- [ ] `agent/runtime.py` — `claude-agent-sdk` boot; answer Q1 from CLI
- [ ] Commit + tag: **milestone: both engines working, agent answers Q1**

### Phase 2 — Integration

**Backend + Streamlit fallback + demo scenarios**
- [ ] `agent/api.py` — FastAPI wrapping `agent/runtime.py`, SSE for agent-trace stream, CORS
- [ ] `app/app.py` Streamlit fallback (<200 lines, polls `/query`)
- [ ] `demo/scenarios.yaml` — 3 hand-tuned demo queries (Q1, Q2, Q3)
- [ ] `tools/monte_carlo.py` + `tools/sensitivity.py` wired into Q2/Q3

**React dashboard**
- [ ] `dashboard/` scaffolded with Vite+TS; `tokens.css` from `claude-design-system` skill
- [ ] Components: Header, QueryInput, ScenarioPicker, AgentTrace (SSE), FieldPlot, UQOverlay, AnswerPanel
- [ ] `dashboard/src/api/client.ts` — SSE consumer, zustand store
- [ ] matplotlib rc params updated to match Claude palette
- [ ] Dry-run 3 demo scenarios end-to-end through dashboard
- [ ] `Dockerfile` multi-stage (Node build + Python runtime)

### Phase 3 — Polish & Deploy

- [ ] Deploy to HuggingFace Spaces (Dockerfile space)
- [ ] `README.md` — problem, architecture diagram, install/run, example queries, honest limitations
- [ ] Record 90s demo video against the React dashboard
- [ ] `demo/brady_validation.ipynb` — Brady load + side-by-side plot
- [ ] Tag `v0.1`, push

### Stretch goals (only if all above shipped)
- [ ] Add `.mcp.json` exposing GeoForce-Solver as an MCP server
- [ ] **Two-phase stub** (optional): add a saturation-variable placeholder (`S_g` field, clamped to 0) and IAPWS-IF97 saturation-curve lookup in `solver/properties.py`. No flash logic. Signals that the architecture extends to two-phase without claiming it works.
- [ ] Polish README with architecture diagrams + Mermaid graphs

### Priority cut order if behind
1. Drop HuggingFace deploy (demo video shot locally instead)
2. Drop React dashboard — record demo against Streamlit fallback
3. Drop Q3 (well-placement) — keep Q1, Q2
4. Drop sensitivity tool — keep predict + Monte Carlo
5. (Phase 1 fallback): drop solver entirely → surrogate-only

## 5. Deliverables Checklist

- [ ] Agent team answers Q1, Q2, Q3 from real user queries
- [ ] Both engines callable; dual-engine Streamlit view works
- [ ] `tests/test_solver_theis.py` passes within <5% of analytical
- [ ] `tests/test_solver_conduction.py` passes within <5% of analytical
- [ ] Monte Carlo UQ produces P10/P50/P90 for at least one query
- [ ] Brady validation notebook renders side-by-side plot
- [ ] README with architecture + honest limitations
- [ ] 90-second demo video
- [ ] Git tag `v0.1`

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Solver fails to converge / NaN** | High | Blocks Phase 3 demo | Start explicit forward-Euler fallback; if Theis fails at end of Phase 1, drop solver (see §4 fallback) |
| **Gravity-coupled numerics unstable** | Medium | Solver unusable | Use Boussinesq (incompressible) approximation first; iterate only if stable |
| **IAPWS-IF97 package slow/buggy** | Low | Property calcs stall | `iapws` PyPI is mature; fall back to polynomial fits over 50–350°C |
| **Agents generate buggy numerical code** | High | Solver doesn't work | Reviewer agent enforces analytical-benchmark tests as the gate |
| **v1.1 weights don't load (torch skew)** | Medium | Surrogate broken | Smoke test is first task in Phase 1; if broken, retrain a tiny scratch CNN |
| **Claude Agent SDK flaky on complex queries** | Medium | Agent loops fail | Keep tool schemas minimal, ≤3 tools per turn, timeout wrappers |
| **Streamlit async/sync mismatch** | Low | UI stalls | Run agent synchronously, stream via `st.write_stream` |
| **React dashboard build fails on HF Spaces** | Medium | No hosted demo | Dockerfile falls through to Streamlit CMD; record video locally |
| **SSE streaming flakes in the browser** | Medium | Agent trace doesn't appear live | Dashboard polls `/query` every 500ms as fallback |
| **Custom Claude design tokens clash with Plotly defaults** | Low | Ugly plot cards | Override Plotly theme with `plotly_white` + custom colorway using design tokens |

### Phase 1 Solver Fallback Trigger (non-negotiable)

If either `test_solver_theis.py` or `test_solver_conduction.py` is **not green** by end of Phase 1:
- Drop all `solver/*` code from the critical path
- Revert to surrogate-only plan
- Reframe pitch: *"Claude agent orchestration over a deployed physics-informed surrogate"*
- Phase 2 and Phase 3 plans remain unchanged; keep Streamlit, Brady validation, demo video

## 7. Environment Setup

- [ ] `ANTHROPIC_API_KEY` exported in shell
- [ ] Fresh `.venv` in repo root with Python 3.11+
- [ ] `iapws` PyPI package available (pin version in pyproject)
- [ ] Source files reachable at `/home/ubuntu/ForceX-AI/products/` (v1.1 weights source)

## 8. Open Decisions (resolved)

1. **Scope:** Solver + Surrogate dual-tool — confirmed
2. **Solver name:** **GeoForce-Solver** (provisional; 1 find/replace to rename)
3. **Phase:** single-phase water; two-phase cut as out-of-scope
4. **Agent runtime:** `claude-agent-sdk` + `ANTHROPIC_API_KEY`
5. **Demo framing:** **Ulubelu-inspired synthetic** — use the Ulubelu field name for on-brand Indonesian narrative, but parameters chosen so the single-phase, liquid-dominated assumption is honest (Ulubelu is 200–240°C, liquid-dominated). Avoids over-claiming vs real Pertamina data.
6. **Demo UI:** React dashboard (primary) + Streamlit (fallback). React uses Anthropic visual design language via the `claude-design-system` skill. Deployed to HuggingFace Spaces via Dockerfile space.
7. **Python env:** fresh `.venv` in repo root

---

**Status:** active development.

---

## 9. Feature Updates

### v0.2 — Engineer-grade chat (post-v0.1)

The initial v0.1 release shipped a single-shot `/query` that fires a fresh
`ClaudeSDKClient` per question. This update adds a conversational follow-up
pattern so engineers can iterate on a question within a session, while keeping
the three demo scenario cards as the first impression.

**Scope change (in):**

- `/sessions` POST opens a long-lived `ClaudeSDKClient`, kept in an
  in-process dict; `/sessions/{id}/query` streams further turns. A
  per-session `asyncio.Lock` prevents two concurrent queries on the
  same session from interleaving on the transport. Reaper task
  evicts sessions idle > 10 min; LRU eviction past 32 sessions.
- Dashboard switches to a chat bubble layout (`ChatThread.tsx`).
  `AgentTrace.tsx` and `AnswerPanel.tsx` are deleted; their behaviour
  is folded into per-message bubbles. A persistent composer below
  the thread submits against the current session. The scenario
  cards + side-by-side canvas remain as the top-row hero.
- Canvas continues to update live on each `predict_solver` /
  `predict_surrogate` tool call, across every turn of the chat, via
  the inline `/predict` pathway added in v0.1.

**Scope change (out):**

- No persisted history — sessions live in memory only, cleared on
  Space restart. The 10-min TTL is sufficient for any single evaluation
  session.
- No per-session auth — the HF Space is public; the `/sessions`
  endpoint is open. Acceptable because the server-side rate limit
  is the 32-session cap and the agent itself enforces
  `max_turns=12` per turn.

**Cost discipline:** each follow-up turn is one model call with
context growing linearly (compressed 8×8 tool previews, not full
arrays). ~$0.30–0.80 per 3-turn follow-up.

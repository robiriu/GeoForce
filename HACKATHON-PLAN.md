# GeoForce — Claude Code Opus 4.7 Hackathon Plan (v2)

**Deadline:** 2 days from 2026-04-23
**Hackathon:** Built with Opus 4.7: a Claude Code Hackathon (Cerebral Valley + Anthropic)
**Event window:** 2026-04-21 4:00 PM → 2026-04-27 12:00 AM (America/Detroit)
**Our target:** submit inside 2 days (ship by 2026-04-25 EOD)
**Author:** Robi Dany Riupassa (built with Claude Code Opus 4.7)
**Repo:** https://github.com/robiriu/GeoForce-CCHackathon

---

## 1. Thesis

> *"Opus 4.7 agents built a minimal, open-source geothermal solver from scratch in 48 hours — gravity-aware, single-phase, IAPWS-IF97 water properties, validated against analytical benchmarks. This is step 1 toward removing the TOUGH3 license barrier for Indonesian researchers. We acknowledge it is not TOUGH3. It is a transparent blueprint that a small team — or a team of agents — can extend."*

Two orchestrated engines:

| Engine | Role | Built when |
|---|---|---|
| **GeoForce-Solver** (new) | Ground-truth-ish single-phase solver, built by agents during the hackathon | Day 1 afternoon |
| **GeoForce v1.1 CNN** (existing) | Fast surrogate for Monte Carlo + sensitivity | Already deployed in ForceX-AI |

A team of Claude Opus 4.7 subagents orchestrates both tools to answer real geothermal engineering questions.

## 2. Prize Strategy

**Primary target:** 1st place ($50K API credits)
**Safety net:** "Best use of Claude Managed Agents" ($5K) — our multi-agent architecture qualifies by construction
**Precedent:** Opus 4.6 winner (CrossBeam) used parallel sub-agents — same pattern

## 3. Scope — In / Out

### IN

1. **GeoForce-Solver solver** (NEW, Python)
   - 2D vertical section (e.g., 50×30 cells), gravity-aware
   - Single-phase water with **IAPWS-IF97** for ρ(T,P), μ(T), h(T,P)
   - Implicit backward-Euler, coupled Darcy + energy conservation
   - Well source terms (injection, production)
   - Built *live* by a multi-agent team during the hackathon
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

5. **Streamlit demo UI** — query box, agent trace panel, side-by-side engine output (Solver vs Surrogate)

6. **Validation cameo** — NREL Brady Hot Springs open dataset comparison (3h slot)

7. **README + 90s demo video + `v0.1-hackathon` tag**

### OUT (explicitly cut)

- **Two-phase physics (steam + liquid) — fatal in 2 days, confirmed 2026-04-23.** A minimal Day-2-evening STUB (saturation variable plumbing, no flash logic) is permitted only if Day 1 solver is green and submission is already filed. Real two-phase is post-hackathon.
- 3D grids — vertical-section 2D only
- TOUGH3 / TOUGH2 / Waiwera — any live external simulator install
- Retraining the CNN
- 3D visualization (three.js, deck.gl)
- PostgreSQL / auth / billing / multi-tenant
- HuggingFace publication (only if Day 2 evening is clean)
- Q4–Q9 engineering questions — require production-state tracking we don't have

## 4. Technical Architecture

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
GeoForce-CCHackathon/
├── CLAUDE.md                       # project-wide Claude Code instructions
├── AGENTS.md                       # visible map of agents + skills + flows
├── HACKATHON-PLAN.md               # this file
├── PROGRESS.md                     # live task tracking
├── README.md                       # (Day 2 write-up)
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
├── solver/                         # GeoForce-Solver (built during hackathon)
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
│   └── app.py                      # Streamlit entry
├── tests/
│   ├── test_solver_theis.py
│   ├── test_solver_conduction.py
│   ├── test_surrogate_smoke.py
│   └── test_agent_smoke.py
└── demo/
    ├── scenarios.yaml
    ├── screencast.mp4              # 90s demo
    └── brady_validation.ipynb      # Day 2 validation cameo
```

## 5. Two-Day Schedule

### Day 1 — Build both engines + wire up agent team

**Morning (3h) — Surrogate port + Claude scaffolding verified**
- [ ] Copy v1.1 weights + `ReservoirCNN` class + encoding into `surrogate/`
- [ ] `tests/test_surrogate_smoke.py` — load + predict + shape assert
- [ ] Confirm `.claude/` scaffolding loads correctly (subagents discovered)
- [ ] `pyproject.toml` installs clean in a fresh venv

**Afternoon (4h) — GeoForce-Solver built by agent team**
- [ ] Orchestrate solver-engineer + geologist + reviewer agents
- [ ] `solver/properties.py` — IAPWS-IF97 wrappers (use `iapws` PyPI package)
- [ ] `solver/grid.py` — 2D vertical section, structured grid
- [ ] `solver/darcy.py` + `solver/energy.py` — single-equation solvers first
- [ ] `solver/coupled.py` — implicit backward-Euler coupled step
- [ ] `solver/wells.py` — source/sink terms
- [ ] `solver/benchmarks/theis.py` + `conduction_1d.py`
- [ ] `tests/test_solver_theis.py` + `test_solver_conduction.py` pass

**Evening (2h) — GO / NO-GO checkpoint + agent wiring**
- [ ] **CHECKPOINT:** both Theis and 1D conduction tests green → proceed. Red → drop solver, ship surrogate-only (see §7 fallback).
- [ ] `tools/predict_solver.py` + `tools/predict_surrogate.py` unified interface
- [ ] `agent/runtime.py` — `claude-agent-sdk` boot; answer Q1 from CLI
- [ ] Commit + push: **milestone: both engines working, agent answers Q1**

### Day 2 — Polish, demo, ship

**Morning (3h) — UI + demo scenarios**
- [ ] `app/app.py` Streamlit: query box, agent trace, dual-engine plots, UQ band
- [ ] `demo/scenarios.yaml` — 3 hand-tuned demo queries (Q1, Q2, Q3)
- [ ] Dry-run each through full agent pipeline; tune prompts
- [ ] `tools/monte_carlo.py` + `tools/sensitivity.py` used in Q2 and Q3 respectively

**Afternoon (3h) — Brady validation + docs + video**
- [ ] `demo/brady_validation.ipynb` — load Brady Hot Springs OSR scenario, run surrogate, plot side-by-side
- [ ] `README.md` — problem, architecture diagram, install/run, example queries, **honest limitations**
- [ ] Record 90-second demo video (OBS/Loom)
- [ ] Tag `v0.1-hackathon`, push, update repo description
- [ ] **Hard stop here if behind schedule**

**Evening (2h) — stretch goals (only if on schedule)**
- [ ] Deploy Streamlit to HuggingFace Spaces or Fly.io
- [ ] Add `.mcp.json` exposing GeoForce-Solver as an MCP server
- [ ] Submit via Cerebral Valley portal
- [ ] **Two-phase stub** (optional): add a saturation-variable placeholder (`S_g` field, clamped to 0) and IAPWS-IF97 saturation-curve lookup in `solver/properties.py`. No flash logic. Signals to judges that the architecture extends to two-phase without claiming it works. Condition: only if Day 1 solver is green AND demo video is recorded AND submission is filed.

### Buffer / cut order if behind
1. Drop HuggingFace deploy
2. Drop Q3 (well-placement) — keep Q1, Q2
3. Drop sensitivity tool — keep predict + Monte Carlo
4. (Day 1 evening checkpoint): drop solver entirely → surrogate-only fallback

## 6. Deliverables Checklist

- [ ] Agent team answers Q1, Q2, Q3 from real user queries
- [ ] Both engines callable; dual-engine Streamlit view works
- [ ] `tests/test_solver_theis.py` passes within <5% of analytical
- [ ] `tests/test_solver_conduction.py` passes within <5% of analytical
- [ ] Monte Carlo UQ produces P10/P50/P90 for at least one query
- [ ] Brady validation notebook renders side-by-side plot
- [ ] README with architecture + honest limitations
- [ ] 90-second demo video
- [ ] Git tag `v0.1-hackathon` + Cerebral Valley submission

## 7. Risks & Mitigations (updated)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Solver fails to converge / NaN** | High | Blocks Day 2 demo | Start explicit forward-Euler fallback; if Theis fails EOD Day 1, drop solver (see fallback) |
| **Gravity-coupled numerics unstable** | Medium | Solver unusable | Use Boussinesq (incompressible) approximation first; iterate only if stable |
| **IAPWS-IF97 package slow/buggy** | Low | Property calcs stall | `iapws` PyPI is mature; fall back to polynomial fits over 50–350°C |
| **Agents generate buggy numerical code** | High | Solver doesn't work | Reviewer agent enforces analytical-benchmark tests as the gate |
| **v1.1 weights don't load (torch skew)** | Medium | Surrogate broken | Smoke test is first task Day 1; if broken, retrain a tiny scratch CNN (backup plan) |
| **Claude Agent SDK flaky on complex queries** | Medium | Agent loops fail | Keep tool schemas minimal, ≤3 tools per turn, timeout wrappers |
| **Streamlit async/sync mismatch** | Low | UI stalls | Run agent synchronously, stream via `st.write_stream` |
| **Day 2 compresses into 1 day** | Medium | Cut demo scope | Buffer cut order in §5 |
| **API quota burns during recording** | Low | Demo aborted | Record before HF deploy; $500 participant credits should be sufficient |
| **Submission portal issues** | Low | Missed deadline | Submit at noon Day 2, not evening |

### Day 1 Evening Fallback Trigger (non-negotiable)

If either `test_solver_theis.py` or `test_solver_conduction.py` is **not green** by end of Day 1:
- Drop all `solver/*` code from the critical path
- Revert to surrogate-only plan (v1 of this doc)
- Reframe pitch: *"Claude Opus 4.7 agent orchestration over a deployed physics-informed surrogate"*
- Still viable for "Best use of Claude Managed Agents" $5K prize
- Day 2 plan unchanged; we keep Streamlit, Brady validation, video

## 8. Pre-flight Checklist (before Day 1 starts)

- [ ] Confirm registration accepted for the Cerebral Valley hackathon (acceptance email)
- [ ] Locate Discord invite (in acceptance email)
- [ ] `ANTHROPIC_API_KEY` exported in shell
- [ ] $500 participant credits confirmed in Anthropic console
- [ ] Fresh `.venv` in repo root with Python 3.11+
- [ ] `iapws` PyPI package available (pin version in pyproject)
- [ ] Source files reachable at `/home/ubuntu/ForceX-AI/products/` (already verified)

## 9. Open Decisions (answered)

1. **Scope:** Solver + Surrogate dual-tool — **APPROVED 2026-04-23**
2. **Solver name:** **GeoForce-Solver** (provisional; 1 find/replace to rename)
3. **Phase:** single-phase water; two-phase cut as out-of-scope
4. **Agent runtime:** `claude-agent-sdk` + `ANTHROPIC_API_KEY`
5. **Demo framing:** **Ulubelu-inspired synthetic** — use the Ulubelu field name for on-brand Indonesian narrative, but parameters chosen so the single-phase, liquid-dominated assumption is honest (Ulubelu is 200–240°C, liquid-dominated). Avoids over-claiming vs real Pertamina data.
6. **Python env:** fresh `.venv` in repo root
7. **Primary prize:** 1st place ($50K); Managed Agents ($5K) as safety net

---

**Status:** scaffolding in progress. GeoForce-Solver and agent work begin Day 1 morning.

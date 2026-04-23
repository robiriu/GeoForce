# PROGRESS — Hackathon Task State

Live task tracking. Updated at the end of every work block. Source of truth = this file.

**Started:** 2026-04-23
**Target submission:** 2026-04-25 EOD (2-day sprint)

---

## Pre-flight

- [x] Repo created (`GeoForce-CCHackathon`) + pushed
- [x] `initial/` seeded from ForceX-AI v2-real-transform planning docs
- [x] Hackathon research complete (rules, prizes, Discord, prior winners)
- [x] HACKATHON-PLAN.md v2 (dual-tool pivot) committed
- [x] CLAUDE.md, AGENTS.md, PROGRESS.md scaffolded
- [x] `.claude/` subagents defined (8)
- [x] `.claude/` skills defined (6)
- [x] `.claude/` commands defined (4)
- [x] `.claude/settings.json` — model pinned to `claude-opus-4-7`
- [x] Fresh `.venv` + `pyproject.toml`
- [x] `ANTHROPIC_API_KEY` in `.env` (gitignored) + round-trip tested
- [x] `.gitignore` protects secrets
- [~] Registration + Discord acceptance email — deferred per user (2026-04-23)

## Day 1 — Build both engines

### Morning (3h) — COMPLETE 2026-04-23
- [x] Copy `geoforce_cnn_v1.1.pt` to `surrogate/weights/` (248,595 bytes, from ForceX-AI/products/model_registry)
- [x] Port `ReservoirCNN` class + encoding to `surrogate/` (model.py, encoding.py, predict.py)
- [x] `tests/test_surrogate_smoke.py` green — 5/5 pass, 1.7s total
- [x] Claude scaffolding discoverable (subagents + skills load; `surrogate-operator.md` corrected to match real v1.1 encoding)

### Afternoon (4h) — Agent team builds GeoForce-Solver
- [ ] `solver/properties.py` — IAPWS-IF97 wrappers
- [ ] `solver/grid.py` — 2D vertical section structured grid
- [ ] `solver/darcy.py` — pressure solver
- [ ] `solver/energy.py` — heat solver
- [ ] `solver/wells.py` — source terms
- [ ] `solver/coupled.py` — implicit backward-Euler
- [ ] `solver/benchmarks/theis.py` — analytical pressure
- [ ] `solver/benchmarks/conduction_1d.py` — analytical temperature
- [ ] `tests/test_solver_theis.py` passes (<5% error)
- [ ] `tests/test_solver_conduction.py` passes (<5% error)

### Evening (2h) — CHECKPOINT + wiring
- [ ] **GO/NO-GO checkpoint:** both analytical tests green?
- [ ] `tools/predict_solver.py` + `tools/predict_surrogate.py`
- [ ] `agent/runtime.py` — claude-agent-sdk boot
- [ ] CLI answers Q1 end-to-end
- [ ] Commit + push — **milestone: both engines live**

## Day 2 — Polish + demo + ship

### Morning (3h) — Backend + Streamlit fallback
- [ ] `agent/api.py` — FastAPI + SSE
- [ ] `app/app.py` — Streamlit fallback (<200 lines)
- [ ] `demo/scenarios.yaml` — Q1, Q2, Q3
- [ ] `tools/monte_carlo.py` + `tools/sensitivity.py`

### Afternoon (4h) — React dashboard
- [ ] `dashboard/` scaffold (Vite+TS)
- [ ] `tokens.css` from claude-design-system skill
- [ ] Components: Header, QueryInput, ScenarioPicker, AgentTrace, FieldPlot, UQOverlay, AnswerPanel
- [ ] `api/client.ts` SSE consumer
- [ ] matplotlib rc params aligned with Claude palette
- [ ] Dry-run 3 scenarios through dashboard
- [ ] `Dockerfile` multi-stage

### Evening (3h) — Ship
- [ ] Deploy to HF Spaces (Dockerfile space)
- [ ] `README.md` + architecture diagram
- [ ] 90s demo video (recorded against React dashboard)
- [ ] `demo/brady_validation.ipynb` (compressed)
- [ ] Tag `v0.1-hackathon` + submit via Cerebral Valley portal

### Stretch (only if all above shipped)
- [ ] `.mcp.json` exposing GeoForce-Solver via MCP
- [ ] Two-phase stub (saturation variable plumbing, no flash)

---

## Fallback Plan (if Day 1 Evening checkpoint fails)

If either analytical-benchmark test fails:
- [ ] Drop `solver/` from critical path
- [ ] Reframe as "Claude Opus 4.7 agent orchestration over deployed surrogate"
- [ ] Keep all Day 2 deliverables intact
- [ ] Still viable for "Best use of Claude Managed Agents" $5K

---

## Decisions Log

| Date | Decision | Source |
|---|---|---|
| 2026-04-23 | 1st-place target, Managed Agents as safety net | user |
| 2026-04-23 | Solver + Surrogate dual-tool | user |
| 2026-04-23 | Solver name = GeoForce-Solver (provisional) | claude |
| 2026-04-23 | Single-phase water (not two-phase) | user approval of pitch |
| 2026-04-23 | NREL Brady for validation cameo | claude proposal |
| 2026-04-23 | Day 1 evening GO/NO-GO trigger | claude proposal |
| 2026-04-23 | Solver renamed TinyTOUGH → GeoForce-Solver | user |
| 2026-04-23 | Two-phase: single-phase for Day 1; optional stub Day 2 evening only if solver green + submitted | user |
| 2026-04-23 | Demo framing: Ulubelu-inspired synthetic (liquid-dominated, on-brand) | user approved claude recommendation |
| 2026-04-23 | Demo UI: React dashboard (primary) + Streamlit (fallback), Claude design language, HF Spaces Dockerfile deploy | user |
| 2026-04-23 | Added 8th subagent: ui-engineer | claude (per user request) |
| 2026-04-23 | Added 5th skill: claude-design-system | claude (per user request) |
| 2026-04-23 | Added 6th skill: tough-reference (deep TOUGH family knowledge from LBNL manuals) | claude (per user request) |

---

## Blocker Log

_(empty — populate as blockers arise)_

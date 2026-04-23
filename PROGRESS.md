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
- [x] `.claude/` subagents defined (7)
- [x] `.claude/` skills defined (4)
- [x] `.claude/` commands defined (4)
- [x] `.claude/settings.json` — model pinned to `claude-opus-4-7`
- [ ] Fresh `.venv` + `pyproject.toml`
- [ ] `ANTHROPIC_API_KEY` verified in shell
- [ ] Registration + Discord acceptance email found

## Day 1 — Build both engines

### Morning (3h)
- [ ] Copy `geoforce_cnn_v1.1.pt` to `surrogate/weights/`
- [ ] Port `ReservoirCNN` class + encoding to `surrogate/`
- [ ] `tests/test_surrogate_smoke.py` green
- [ ] Claude scaffolding discoverable (subagents load)

### Afternoon (4h) — Agent team builds TinyTOUGH
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

### Morning (3h)
- [ ] `app/app.py` — Streamlit UI
- [ ] `demo/scenarios.yaml` — Q1, Q2, Q3 scenarios
- [ ] Tune agent prompts for crisp answers
- [ ] `tools/monte_carlo.py` + `tools/sensitivity.py`

### Afternoon (3h)
- [ ] `demo/brady_validation.ipynb` — NREL Brady side-by-side
- [ ] `README.md` — full write-up
- [ ] 90s demo video
- [ ] Tag `v0.1-hackathon`
- [ ] Submit via Cerebral Valley portal

### Evening (2h stretch)
- [ ] Deploy Streamlit (HF Spaces / Fly.io)
- [ ] `.mcp.json` for MCP-exposed TinyTOUGH

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
| 2026-04-23 | Solver name = TinyTOUGH (provisional) | claude |
| 2026-04-23 | Single-phase water (not two-phase) | user approval of pitch |
| 2026-04-23 | NREL Brady for validation cameo | claude proposal |
| 2026-04-23 | Day 1 evening GO/NO-GO trigger | claude proposal |

---

## Blocker Log

_(empty — populate as blockers arise)_

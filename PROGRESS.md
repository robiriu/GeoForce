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

### Afternoon (4h) — Agent team builds GeoForce-Solver — COMPLETE 2026-04-23
- [x] `solver/properties.py` — IAPWS-IF97 wrappers
- [x] `solver/grid.py` — 2D vertical section structured grid
- [x] `solver/darcy.py` — pressure solver
- [x] `solver/energy.py` — heat solver
- [x] `solver/wells.py` — source terms
- [x] `solver/coupled.py` — implicit backward-Euler
- [x] `solver/benchmarks/theis.py` — analytical pressure
- [x] `solver/benchmarks/conduction_1d.py` — analytical temperature
- [x] `tests/test_solver_theis.py` passes (<5% error)
- [x] `tests/test_solver_conduction.py` passes (<5% error)

### Evening (2h) — CHECKPOINT + wiring — COMPLETE 2026-04-23
- [x] **GO/NO-GO checkpoint:** both analytical tests green → GO
- [x] `tools/predict_solver.py` + `tools/predict_surrogate.py`
- [x] `agent/runtime.py` — claude-agent-sdk boot
- [x] CLI answers Q1 end-to-end
- [x] Commit + push — **milestone: both engines live**

## Day 2 — Polish + demo + ship

### Morning (3h) — Backend + Streamlit fallback — COMPLETE 2026-04-23
- [x] `agent/api.py` — FastAPI + SSE (+ `/predict`, + SPA static mount)
- [x] `app/app.py` — Streamlit fallback
- [x] `demo/scenarios.yaml` — Q1, Q2, Q3
- [x] `tools/monte_carlo.py` + `tools/sensitivity.py`

### Afternoon (4h) — React dashboard — COMPLETE 2026-04-23
- [x] `dashboard/` scaffold (Vite+TS+zustand)
- [x] `tokens.css` from claude-design-system skill
- [x] Components: Header, QueryInput, ScenarioPicker, AgentTrace, AnswerPanel, FieldPlot, FieldPanel
- [x] `api/client.ts` SSE consumer + `predictFields` helper
- [x] Canvas-based magma heatmap (no plotly — bundle stays <160 kB)
- [x] Dry-run 3 scenarios through `/predict` + SSE smoke of `/query`
- [x] `Dockerfile` multi-stage (node build → python runtime, CPU-only torch)

### Evening (3h) — Ship — IN PROGRESS 2026-04-23
- [x] Deploy to HF Spaces (Dockerfile space)
  - live at https://huggingface.co/spaces/robiriu/geoforce (runtime: RUNNING)
  - weights tracked via LFS on the `hf-deploy` branch; main stays clean
  - user must set `ANTHROPIC_API_KEY` as a Space secret for `/query`
- [x] Root `README.md` + ASCII architecture diagram (+ HF Spaces frontmatter)
- [ ] 90s demo video (recorded against React dashboard) — user-only task
- [x] `demo/validation.ipynb` (replaces Brady — Theis 0.38%, conduction 0.18%,
       solver↔surrogate Δ Tmax for all 3 scenarios)
- [x] Tag `v0.1-hackathon` (local; push when ready)
- [ ] Submit via Cerebral Valley portal — user-only task

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

- **2026-04-23 — RESOLVED** — Solver pressure anomalies on q1/q3 traced
  to scenarios having injection with no matching outlet (closed domain
  + compressibility storage → P accumulates). Fixed by adding a
  far-field producer to q1 and a baseline producer to q3 in
  `demo/scenarios.yaml`. Re-ran all 3: temperature bounded by
  [T_inj, T_initial], pressure in ±1 MPa of base. Validation notebook
  confirms Theis and conduction gates still pass (0.38% / 0.18%).
- **2026-04-24 — RESOLVED** — HF Space `/predict?engine=surrogate`
  returned 500 after initial deploy. Root cause: HF Spaces Docker SDK
  does not materialise LFS content in the build context, so the 248 kB
  `.pt` file arrived as a text pointer stub. Added a Dockerfile RUN
  step that detects the stub (`head -c 64 | grep '^version https://git-lfs'`)
  and curls the real binary from the Space's own `/resolve/main/` URL.
  Rebuild succeeded; all three endpoints (`/health`, solver, surrogate)
  return 200 on the live Space.

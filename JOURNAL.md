# JOURNAL.md — Build Process Documentation

Complete narrative of how GeoForce-CCHackathon was conceived, scoped, and scaffolded. This document explains the **why** behind every decision. It is separate from:

- **`HACKATHON-PLAN.md`** — the forward-looking contract (what we're going to build)
- **`PROGRESS.md`** — live task state with checkboxes (where we are right now)
- **`CLAUDE.md`** + **`AGENTS.md`** — project instructions and runtime architecture (how Claude Code operates in this repo)

If you want to know the current state, read `PROGRESS.md`. If you want to know the plan, read `HACKATHON-PLAN.md`. If you want to know why we made each choice, read this file.

---

## 1. Overview

**GeoForce-CCHackathon** is Robi Dany Riupassa's submission for "**Built with Opus 4.7 — Claude Code Hackathon**" (Cerebral Valley + Anthropic, 2026-04-21 to 2026-04-27). Personal time budget: 2 days starting 2026-04-23.

**Prize targets:**
1. **Primary:** 1st place — $50K API credits
2. **Secondary (safety net):** "Best use of Claude Managed Agents" — $5K API credits

**One-line thesis:**
> Opus 4.7 agents orchestrate two engines — a newly-built open-source geothermal solver (**GeoForce-Solver**) and a deployed physics-informed CNN surrogate (v1.1) — to answer real Indonesian geothermal engineering questions in 48 hours.

The project deliberately showcases two things at once:
1. A substantive engineering artifact (MIT-licensed geothermal solver + deployed surrogate).
2. A disciplined multi-agent architecture (8 specialized Opus 4.7 subagents with explicit parallel/sequential DAG).

---

## 2. Origin & Prior Work

### 2.1 ForceX AI background

Robi is the founder of **ForceX AI** (Bandung, Indonesia; ITB petroleum engineering / SHARC lab). Prior to the hackathon, the `ForceX-AI` repo contained a full product called **GeoForce**: an AI-assisted geothermal reservoir analysis platform. Two generations of work exist:

- `products/geoforce/` (v1) — first-generation surrogate + notebooks + validation
- `products/geoforce/v2-real-transform/` — **v2 re-planning** that acknowledged v1 was a smoke-and-mirrors demo and defined the path to a real, credible engineering tool

The v2 planning docs (`PLAN.md`, `PROGRESS.md`, `REAL-ENGINEERING-QUESTIONS.md`) became the seed for this hackathon project and live at `initial/` (frozen, read-only).

### 2.2 What already exists (leveraged, not rebuilt)

From the v1/v2 GeoForce work:
- **`geoforce_cnn_v1.1.pt`** — trained physics-informed CNN surrogate
  - 57,802 parameters
  - R²_T = 0.994, R²_P = 0.997
  - 3.2 ms inference
  - 6-channel input (log_k, porosity, depth, well mask, base_T, base_P) on 32×32 grid
  - 10-channel output (T and P at 5 timesteps)
  - **Frozen.** Never retrain during the hackathon.

### 2.3 Why a hackathon project (not just continuing ForceX AI)

The hackathon forces a **crisp, defensible 48-hour deliverable**. Continuing ForceX AI work would bleed into v2's broader multi-quarter scope. Framing this as a separate repo (`GeoForce-CCHackathon`) keeps the hackathon submission self-contained and judge-friendly.

---

## 3. Hackathon Research Synthesis

Before writing a single line of code, I researched the hackathon itself: Cerebral Valley's event page, rules, Discord, and prior winners of the Opus 4.6 edition. Findings that shaped the plan:

### 3.1 What wins

Past winners (e.g., CrossBeam from the Opus 4.6 edition) shared three traits:
1. **Real engineering substance**, not just a demo skin.
2. **Visible multi-agent orchestration** with parallel execution.
3. **Polished demo surface** (video + deployed app + clean README).

### 3.2 Prize fit

- **1st place ($50K)** demands technical weight *and* a winning demo.
- **Managed Agents ($5K)** is awarded for clean agent architecture — this is our fallback if the solver doesn't converge in time.

Stacking both targets means: build an architecture that *already* satisfies the Managed Agents criterion, then add the solver narrative on top to reach for 1st.

### 3.3 Constraints found in the rules

- Must be built primarily with Claude Code + Opus 4.7 during the hackathon window.
- Must be submitted via the Cerebral Valley portal before the deadline.
- Projects that only use Opus 4.7 as a wrapper over existing code are explicitly discouraged.

---

## 4. Thesis Evolution (The Key Decisions)

The project's framing changed three times before settling. Each change is recorded here with date, trigger, and rationale.

### 4.1 v0 — "Deploy the v1.1 surrogate behind a chat UI"
**Date:** early planning, 2026-04-23 morning

**What it was:** take the existing v1.1 CNN, wrap it in Streamlit, let Claude answer questions by calling it.

**Why rejected:** thin. A CNN + a chat UI is a weekend tutorial, not a 1st-place hackathon entry. It doesn't demonstrate Opus 4.7's unique capabilities (multi-agent orchestration, parallel task dispatch, live code authoring).

### 4.2 v1 — "Dual-tool: newly-built solver + deployed surrogate"
**Date:** 2026-04-23 midday

**What it is:** Opus 4.7 agents build a minimal, open-source geothermal solver (`GeoForce-Solver`) *during the hackathon itself*, paired with the already-deployed v1.1 CNN surrogate. The planner agent chooses which engine to call per query.

**Why it won out:**
- **Engineering substance** — writing a reservoir solver from scratch in 48h is a real feat and directly inspired by TOUGH's architecture.
- **Narrative** — "agents built a solver that a grad student can legally use today" sidesteps TOUGH's proprietary licensing in a principled way.
- **Demonstrable parallelism** — solver-engineer and surrogate-operator can run in the same message.

**The TOUGH question:** can we use TOUGH3? No — it's proprietary, requires license request, and `build-upon` framing is stronger than `wrap-existing`. So we build a small solver in the TOUGH tradition and cite TOUGH explicitly.

### 4.3 Single-phase vs. two-phase (brief detour, corrected immediately)
**Date:** 2026-04-23 afternoon

**What happened:** user initially asked for two-phase physics. I pushed back: two-phase means phase transitions, saturation as a primary variable, IAPWS steam tables, primary-variable switching, and a stiff nonlinear system. That breaks the 48-hour budget with near-certainty.

**Resolution:** user accepted the recommendation. Scope is **single-phase liquid water** for Day 1. Two-phase appears only as a *Day 2 evening stretch stub* (plumbing a saturation variable with no real flash logic) and only if Day 1 ends green with time to spare.

**Why this is the right call:** two-phase is the single largest risk factor in any reservoir solver build. Single-phase keeps the math tractable (Darcy is linear in P under Boussinesq), still covers most of Indonesia's liquid-dominated fields, and leaves room for a clean benchmark pass.

### 4.4 Solver name: TinyTOUGH → GeoForce-Solver
**Date:** 2026-04-23 afternoon

**Why:** user preferred brand consistency with the `GeoForce` product name. "TinyTOUGH" signals the inspiration but competes with our own identity. Renamed across 9 files via bulk replace.

### 4.5 UI: React dashboard + Streamlit fallback
**Date:** 2026-04-23 afternoon

**Why React at all:** judges see the demo through the UI. A polished React+Vite+TS dashboard with Anthropic's visual design language is a stronger demo surface than Streamlit.

**Why Streamlit as fallback:** if the dashboard build runs over, a <200-line Streamlit app still gets the demo out the door. The cut order is explicit in the plan: drop the React dashboard before dropping the solver.

**Design language:** Anthropic's visual tokens (warm paper background `#F5F4EE`, Clay accent `#CC785C`, Source Serif 4 headings, Inter body). Captured in the `claude-design-system` skill so every styling decision is token-driven, not ad hoc.

### 4.6 Deployment: HuggingFace Spaces via Dockerfile
**Date:** 2026-04-23 afternoon

**Why HF Spaces:** free, always-on, judge-friendly URL, supports Dockerfile spaces (multi-stage Node+Python builds). Familiar to the AI community.

### 4.7 Demo framing: Ulubelu-inspired synthetic
**Date:** 2026-04-23 afternoon

**What it is:** demo scenarios use synthetic reservoir parameters inspired by **Ulubelu** (a real liquid-dominated Indonesian geothermal field, Lampung province) — not real Ulubelu data.

**Why synthetic:** real Ulubelu data is proprietary; synthetic keeps us unencumbered. Using the *name* of a real field signals credibility and domain authority without misrepresenting data provenance.

**Why Ulubelu specifically (not Kamojang or Darajat):** Kamojang and Darajat are vapor-dominated — they violate the single-phase-*liquid* assumption. Ulubelu, Salak, and Lahendong are liquid-dominated, so they're fair game. The `geologist` subagent enforces this.

### 4.8 Day 1 evening GO/NO-GO checkpoint
**Date:** 2026-04-23 (decision made at plan time)

**The gate:** at the end of Day 1, both analytical benchmarks (Theis pressure, 1D conduction) must pass within 5% relative error. If either fails:

- **Drop the solver entirely.**
- **Reframe as:** "Opus 4.7 agent orchestration over a deployed surrogate."
- Keep all Day 2 deliverables intact.
- Still eligible for "Best use of Claude Managed Agents" ($5K).

**Why an explicit checkpoint:** hackathons kill good teams by letting them sink 20 hours into unworkable code. A fixed trigger with a pre-committed fallback is cheap insurance.

---

## 5. Architecture

### 5.1 Multi-agent pattern

The project has **8 subagents** (not 7, not 9 — more on that below). Each is a `.md` file with YAML frontmatter under `.claude/agents/`. The planner is the entry point; everyone else specializes.

| # | Subagent | Role |
|---|---|---|
| 1 | `planner` | Decomposes query → DAG, dispatches in parallel |
| 2 | `geologist` | Validates reservoir params against Indonesian field ranges |
| 3 | `solver-engineer` | Builds + runs GeoForce-Solver |
| 4 | `surrogate-operator` | Wraps v1.1 CNN inference |
| 5 | `uq-specialist` | Monte Carlo + sensitivity |
| 6 | `visualizer` | 2D heatmaps + UQ band overlays |
| 7 | `reviewer` | Physics sanity gate (always last) |
| 8 | `ui-engineer` | React dashboard + Streamlit fallback + FastAPI SSE |

**Why 8, not 7:** the user asked whether UI work should be another subagent. Yes — building the dashboard is a separable, specialized job with its own skill (`claude-design-system`) and its own tool set (React+Vite+TS). Folding it into another agent would muddy responsibilities.

**Why not more (e.g., a dedicated test-writer, a dedicated git-pusher):** fewer sharper agents beat more fragmented ones. Every extra agent adds coordination cost. Tests belong to whoever writes the code; git belongs to the human.

**The parallel/sequential DAG** is documented in `AGENTS.md` with Q1/Q2/Q3 flow diagrams. The key insight: `solver-engineer` and `surrogate-operator` run **simultaneously** in a single Claude message (two parallel `Agent` tool calls). The visualizer only runs after both return. The reviewer is always last.

### 5.2 Skills

6 skills under `.claude/skills/<name>/SKILL.md`. Skills are the **reusable tooling layer** — agents call them via natural-language reference.

| Skill | Purpose |
|---|---|
| `iapws97-water` | IAPWS-IF97 water properties (ρ, μ, h, cp) via the `iapws` PyPI package |
| `monte-carlo-uq` | Parameter sampling + P10/P50/P90 aggregation |
| `field-visualization` | matplotlib 2D heatmaps with magma (T) / viridis (P) / UQ bands |
| `analytical-benchmarks` | Theis + 1D conduction reference solutions (acceptance gates) |
| `claude-design-system` | Anthropic visual tokens (colors, typography, spacing) + matplotlib rcParams |
| `tough-reference` | Deep knowledge of the TOUGH family (LBNL): architecture, EOS, numerics, licensing |

**Why `tough-reference` is a skill, not a doc:** it's consulted *during* agent work (solver-engineer reads it before choosing a flux form), not just at project setup. Skills are the right home for consulted knowledge.

**Why `claude-design-system` is a skill:** same logic — UI-engineer needs token values during build, not just at kickoff.

### 5.3 Slash commands

4 commands under `.claude/commands/`. These are the human-invocable shortcuts:

- `/query <question>` — wraps the planner for any natural-language question
- `/validate-solver` — runs Theis + 1D conduction pytest (the GO/NO-GO gate)
- `/parallel-mc <scenario>` — MC ensemble via uq-specialist
- `/demo` — runs the 3 hand-tuned demo scenarios end-to-end

### 5.4 Settings & hooks

`.claude/settings.json`:
- `"model": "claude-opus-4-7"` — pins Opus 4.7 for every Claude Code session in this repo
- Allowlist: Read, Write, Edit, Bash (pytest, python, streamlit), git add/commit/status/diff/log
- Denylist: `rm -rf`, `git push --force`, service-account keys
- `PostToolUse` hook on `Edit|Write` → `.claude/hooks/post_write_pytest.sh`

`.claude/hooks/post_write_pytest.sh`:
- Detects edits under `solver/`, `surrogate/`, `tools/`, `agent/`
- Runs `python -m pytest tests/ -x --tb=short -q` automatically after each edit
- Non-blocking — failures are surfaced but don't stop the session

**Why a post-write hook:** tests-that-never-run are worse than no tests. Auto-running pytest after solver edits catches regressions the moment they're introduced.

---

## 6. Scope Boundaries (The "No" List)

A project this tight is defined more by what it *doesn't* do than what it does.

| Rejected | Why |
|---|---|
| Full TOUGH3 clone | ~10 person-years; infeasible in 48h |
| Installing TOUGH3 / Waiwera at runtime | License friction; deployment bloat |
| Two-phase physics (Day 1) | Breaks the 48h budget with high probability |
| Retraining the CNN | v1.1 is already validated; retraining burns time with no upside |
| 3D grids | 2D vertical section covers the demo scenarios |
| Unstructured meshes | Structured 32×32 matches the CNN's assumption |
| Reactive geochemistry | Not relevant to the core value prop |
| Real Ulubelu field data | Proprietary; synthetic is cleaner |
| React component libraries (Material, Chakra, Ant, shadcn, Tailwind) | The design system is the differentiator; libraries fight it |
| Force-push to main | Destructive; never without explicit user ask |
| Emoji in code, docs, commits | Unless user asks |

---

## 7. Relationship to TOUGH (LBNL)

TOUGH (Transport Of Unsaturated Groundwater and Heat) is the 40-year industry-standard geothermal reservoir simulator family from LBNL. GeoForce-Solver is **not** a TOUGH clone — it is a deliberately minimal single-phase solver that borrows TOUGH's numerical philosophy:

| Concept | TOUGH | GeoForce-Solver |
|---|---|---|
| Conservation form | Integral Finite Difference | Finite-volume on structured 2D (a degenerate case) |
| Time integration | Fully-implicit backward-Euler | Same |
| Nonlinear solve | Newton-Raphson + primary-variable switching | Newton on energy only (no switching — single-phase) |
| Linear solve | MA28 / PETSc | `scipy.sparse.linalg.spsolve` |
| EOS | 10+ modules (EOS1, ECO2N, EWASG, ...) | EOS1 liquid-only (IAPWS-IF97 Region 1) |
| Wells | 4 complexity levels (incl. T2Well) | Specified-rate (level 1), optional Peaceman |
| V&V | Decades of benchmarks | Theis + 1D conduction |
| **Licensing** | **Proprietary (~$400 academic, ~$4000 commercial)** | **MIT / Apache-2.0** |

**The licensing point is the point.** A graduate student today cannot run TOUGH without waiting for a license email. GeoForce-Solver is `pip install`-able, hackable, and reproducible. That's a real contribution, not a toy.

Full reference inventory (~50 TOUGH manuals, prioritized Tier 1/2/3) lives in the `tough-reference` skill.

---

## 8. UI Strategy

Two surfaces, explicit fallback order:

1. **Primary: `dashboard/`** — React 18 + Vite + TypeScript + plain CSS modules using `claude-design-system` tokens.
   - Components: Header, QueryInput, ScenarioPicker, AgentTrace (live SSE stream of subagent events), FieldPlot, UQOverlay, AnswerPanel
   - Backend: FastAPI at `agent/api.py` with Server-Sent Events
   - Allowed libraries: `zod`, `zustand`, `plotly.js`
   - **No** Material, Chakra, Ant, shadcn, or Tailwind — the design system is the differentiator

2. **Fallback: `app/app.py`** — <200-line Streamlit app that hits the same FastAPI backend.

**Cut order if time runs out:** drop React dashboard → keep Streamlit. Drop Streamlit → CLI demo. Never drop the solver (it's the 1st-place narrative).

**Deployment:** HuggingFace Spaces, Dockerfile space (multi-stage Node+Python).

---

## 9. Deliverables (the judge-visible output)

By 2026-04-25 EOD:

1. **GitHub repo** — `robiriu/GeoForce-CCHackathon` (public, MIT-licensed)
2. **Live demo URL** — HF Spaces Dockerfile deployment
3. **README.md** — architecture diagram + quickstart
4. **90-second demo video** — recorded against React dashboard
5. **`demo/brady_validation.ipynb`** — NREL Brady Hot Springs validation cameo
6. **Tag `v0.1-hackathon`** — submitted via Cerebral Valley portal

**Stretch (only if all above shipped):**
- `.mcp.json` exposing GeoForce-Solver via MCP (Model Context Protocol)
- Two-phase saturation-variable plumbing stub (no real flash)

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Solver fails analytical benchmarks by Day 1 EOD | Medium | High | GO/NO-GO checkpoint → surrogate-only fallback keeps $5K prize viable |
| React dashboard build runs over | Medium | Medium | Streamlit fallback already scoped (<200 LOC) |
| HF Spaces deployment fails at submission time | Low | High | Test deploy on Day 2 afternoon, not evening |
| API key / Discord access not verified | Low | Low | Pre-flight checklist in `PROGRESS.md` |
| Scope creep during Day 2 | Medium | High | CLAUDE.md §2 priority rules override any in-flight temptation |
| v1.1 CNN port reveals silent bug | Low | High | Smoke test first 30 minutes of Day 1 morning |

---

## 11. File Inventory (as of scaffolding complete)

```
GeoForce-CCHackathon/
├── CLAUDE.md                  # Project instructions (loaded every session)
├── AGENTS.md                  # Multi-agent runtime architecture
├── HACKATHON-PLAN.md          # 2-day plan (the contract)
├── PROGRESS.md                # Live task state
├── JOURNAL.md                 # This file — build narrative
├── .claude/
│   ├── settings.json          # Model pin + permissions + hooks
│   ├── hooks/
│   │   └── post_write_pytest.sh
│   ├── agents/                # 8 subagents
│   │   ├── planner.md
│   │   ├── geologist.md
│   │   ├── solver-engineer.md
│   │   ├── surrogate-operator.md
│   │   ├── uq-specialist.md
│   │   ├── visualizer.md
│   │   ├── reviewer.md
│   │   └── ui-engineer.md
│   ├── skills/                # 6 skills
│   │   ├── iapws97-water/SKILL.md
│   │   ├── monte-carlo-uq/SKILL.md
│   │   ├── field-visualization/SKILL.md
│   │   ├── analytical-benchmarks/SKILL.md
│   │   ├── claude-design-system/SKILL.md
│   │   └── tough-reference/SKILL.md
│   └── commands/              # 4 slash commands
│       ├── query.md
│       ├── validate-solver.md
│       ├── parallel-mc.md
│       └── demo.md
├── initial/                   # Seed docs from ForceX-AI v2 (frozen, read-only)
│   ├── PLAN.md
│   ├── PROGRESS.md
│   └── REAL-ENGINEERING-QUESTIONS.md
└── docs/                      # Misc

(Day 1 will add: surrogate/, solver/, solver/benchmarks/, tests/, tools/, agent/)
(Day 2 will add: dashboard/, app/, demo/, Dockerfile, README.md)
```

---

## 12. Where Current Completion Status Lives

**This file does not track task status.** For that, see:

- **`PROGRESS.md`** — master checklist with every task organized by Day 1 Morning / Afternoon / Evening and Day 2 Morning / Afternoon / Evening, plus decisions log and blocker log.
- **`HACKATHON-PLAN.md`** §5–§7 — the original time-boxed plan and the fallback triggers.

The separation is deliberate: `JOURNAL.md` is the narrative explanation (rarely updated); `PROGRESS.md` is the live task tracker (updated every work block).

---

## 13. Key Dates

| Date | Event |
|---|---|
| 2026-04-21 | Hackathon begins (Cerebral Valley) |
| 2026-04-23 | Robi's sprint begins; repo created; planning + scaffolding complete; TOUGH skill added |
| 2026-04-24 | **Day 1 execution:** surrogate port (morning), solver build (afternoon), GO/NO-GO (evening) |
| 2026-04-25 | **Day 2 execution:** dashboard + Streamlit + deploy + demo video + submission |
| 2026-04-27 | Hackathon ends |

---

## 14. Lineage & Attribution

- **Prior art:** ForceX-AI `products/geoforce/` (v1 surrogate, training notebooks, validation) — author: Robi Dany Riupassa
- **v1.1 CNN weights:** `geoforce_cnn_v1.1.pt` (training in `ForceX-AI/products/geoforce/training/`)
- **TOUGH inspiration:** Karsten Pruess et al., LBNL — https://tough.lbl.gov/
- **IAPWS-IF97 formulation:** via the `iapws` PyPI package (Juanes & Lerman port)
- **Theis analytical solution:** Theis, C.V. (1935)
- **Design tokens:** Anthropic visual design language, as interpreted in the `claude-design-system` skill
- **Agent orchestration pattern:** inspired by CrossBeam (Opus 4.6 hackathon winner)
- **Multi-agent execution:** Claude Code's `Agent` tool with parallel dispatch
- **Runtime (Day 1 evening):** `claude-agent-sdk` (Python) pinned to `claude-opus-4-7`

All original code in this repo is MIT-licensed. Citations are in code comments where TOUGH concepts are adopted.

---

*Last updated: 2026-04-23 — end of scaffolding phase, before Day 1 execution begins.*

---

## 15. Day-2 Build Log — 2026-04-23

### 15.1 UQ tools

`tools/monte_carlo.py` and `tools/sensitivity.py` landed early on Day 2.
The Monte-Carlo tool draws `n_samples` from per-parameter distributions
declared in `demo/scenarios.yaml`, runs the surrogate in a tight loop
(each call is ~200 ms → 200 samples in ~40 s), and returns P10/P50/P90
per metric. The sensitivity tool does classical one-at-a-time sweeps
around a base scenario so the agent can report "permeability dominates
reservoir-mean T, porosity is noise."

Both tools are exposed to the agent as `mcp__geoforce__monte_carlo` and
`mcp__geoforce__sensitivity_oat`, so the planner chooses between them
based on whether the user asks *how confident* (MC) or *what matters
most* (OAT).

### 15.2 FastAPI + SSE backend

`agent/api.py` wraps the `claude-agent-sdk` client in an
`EventSourceResponse` and emits four SSE event kinds — `text`, `tool`,
`result`, `error`. The shape of those events is documented in the file
header so the React client has a schema to code against.

Why SSE and not WebSockets: the agent stream is one-way, browsers
auto-reconnect SSE for free, and the native `EventSource` API would
have been ideal — except it only supports `GET`. We POST the body, so
the client uses `fetch` + `ReadableStream.getReader()` + a manual SSE
parser (`parseSSEChunk` in `dashboard/src/api/client.ts`).

Added a `/predict` endpoint that runs solver and/or surrogate
synchronously and returns the full temperature and pressure arrays as
JSON. The UI uses this to render the side-by-side heatmap; the agent
can also call it indirectly through its MCP tools.

### 15.3 React dashboard

The visual differentiator for a hackathon with ~200 submissions is
almost always the UI. Given the "Built with Opus 4.7" framing, the
dashboard deliberately looks like a Claude artifact — warm
`#F5F4EE` paper, Clay `#CC785C` accent, Source Serif 4 headings with
italic captions, Inter body, JetBrains Mono for the tool-call preview.
No component library, no Tailwind: plain CSS variables in
`src/styles/tokens.css`, then utility classes in `global.css`.

State lives in a single zustand store. The agent trace coalesces
adjacent `text` events into one rendered block so the streamed prose
reads continuously instead of flickering per-token. Tool calls render
as a Clay-bordered card showing the stripped tool name
(`predict_solver`, not `mcp__geoforce__predict_solver`) and a truncated
JSON preview.

For the temperature-field visualization I chose a canvas-based 12-stop
magma colormap in `src/viz/magma.ts` rather than pulling in plotly
(~600 kB). It renders the 32×32 or 40×20 grid at ~1 ms per paint and
keeps the total bundle at ~155 kB JS / 3.5 kB CSS. The solver and
surrogate plots share a `tMin`/`tMax` computed from both arrays so the
color comparison is honest, and a mono chip shows `Δ Tmax` as a
headline disagreement metric.

### 15.4 Docker

Multi-stage `Dockerfile`: `node:20-bookworm-slim` builds the Vite
bundle, then `python:3.11-slim-bookworm` installs CPU-only torch from
the PyTorch wheel index (much smaller than the default CUDA wheel) and
the rest of the FastAPI/agent dependencies by explicit pin rather than
`pip install -e .` (so the layer caches cleanly). The built dashboard
is copied into `/app/dashboard/dist` and `agent.api` auto-detects it
and mounts `/assets` + `/` for SPA serving. Single port, single
container, `HEALTHCHECK` on `/health`.

### 15.5 Dry-run — 2026-04-23

Backend restarted on `:8765`. `/predict` roundtrips all three
scenarios:

| scenario | solver T range | surrogate T range | solver elapsed | surrogate elapsed |
| --- | --- | --- | --- | --- |
| q1_drill_temperature | 60.1–277.5 °C | 188.7–205.1 °C | 3.56 s | 0.22 s |
| q2_sustainable_mw | 70.0–220.0 °C | 213.0–229.7 °C | 4.07 s | 0.004 s |
| q3_well_placement | 70.1–610.5 °C | 221.8–241.0 °C | 4.58 s | 0.15 s |

Surrogate is two to three orders of magnitude faster, which is exactly
why the agent should fan MC sweeps through it and only invoke the
solver for the authoritative field.

Two physics concerns surfaced (logged in `PROGRESS.md` blocker log):

- Solver pressure output for q1/q3 is ~10² MPa after unit conversion —
  suggests either a unit mismatch in `solver.coupled`'s output dict or a
  boundary-condition issue that lets pressure blow up. Must be fixed
  before the demo video.
- q3 solver T tops 610 °C, well above `T_initial = 220 °C`. That's
  non-physical for a producer-only extraction and suggests the well
  source term is over-applied. Also pre-demo.

SSE end-to-end confirmed by POSTing a short natural-language query and
seeing `event: text` / `event: result` stream back as expected.

### 15.6 Discipline notes

What we deliberately did **not** build:

- A third engine. The thesis is solver + surrogate; adding anything
  else dilutes it.
- A component library. Every card, chip, and button is a `<div>` with a
  CSS class.
- Plotly / chart.js / d3. Canvas + 40 lines of TypeScript did the job.
- Two-phase flow. Out of scope per `CLAUDE.md` §2.

---

## 16. Day-2 Evening — Ship — 2026-04-23

### 16.1 Physics blocker resolved

Afternoon dry-run surfaced two anomalies: solver pressure on q1 /
q3 reading ~10² MPa (physically absurd — reservoir should stay around
15 MPa) and a 610 °C temperature excursion on q3 (above T_initial). I
thought it was a unit or boundary-condition bug. It wasn't.

Root cause: both scenarios had injection wells with no matching
outlet, inside a closed-boundary domain. The Darcy solver conserves
mass via compressibility storage (`V·φ·c_t·dP/dt`), so injected mass
can only be absorbed by raising pressure — indefinitely, since
`c_t ≈ 1e-9 1/Pa` gives tiny volumetric capacity. Integrating
q_mass / (ρ·V·φ·c_t) over the run time reproduces the observed ~10²
MPa. The 610 °C on q3 was the same pathology once-removed: huge
pressure gradients drove implausible face fluxes, and the implicit
upwind advection did the best it could with an unphysical mass
balance.

Fix was in the YAML, not the code — add a far-field producer to q1
and a baseline producer to q3 so the net mass flux into the domain is
zero. Re-dry-run gave clean numbers:

| scenario | solver T | surrogate T | ΔTmax | solver P (MPa) |
| --- | --- | --- | --- | --- |
| q1 | 60.0–200.0 °C | 188.7–205.1 °C | 5.1 °C | 14.81–15.19 |
| q2 | 70.0–220.0 °C | 213.0–229.7 °C | 9.8 °C | 13.86–16.11 |
| q3 | 70.0–230.0 °C | 221.8–241.0 °C | 11.0 °C | 14.19–15.78 |

Every T stays inside `[T_inj, T_initial]` (max principle holds),
every P stays inside ±1 MPa of the base. The analytical benchmarks
were never wrong; the scenarios were just ill-posed.

Lesson for the JOURNAL: the dual-engine dashboard design paid off
instantly. The Δ-Tmax chip made the q1 / q3 anomaly visually
obvious, which is exactly what the two-engine thesis was supposed to
enable. If this had been solver-only I would have shipped wrong
numbers without noticing.

### 16.2 Validation notebook

Original plan was a "Brady validation cameo". No Brady dataset was
actually available in the ForceX-AI archive — the reference in
HACKATHON-PLAN.md was aspirational. Rather than fabricate something,
I pivoted to an honest in-repo validation: `demo/validation.ipynb`
re-runs the two analytical gates (Theis 0.38 %, 1-D conduction
0.18 %) and the solver↔surrogate ΔT table above, each from first
principles in a single notebook. Whole notebook executes in under a
minute on CPU.

### 16.3 Hugging Face Spaces deploy

Target space: `robiriu/geoforce`, Docker SDK, port 8765 via
`app_port` in the README frontmatter. First push was rejected for two
reasons in sequence:

1. `surrogate/weights/geoforce_cnn_v1.1.pt` (244 kB binary) — HF
   requires binaries via Xet / LFS.
2. `short_description` > 60 characters.

Rather than rewrite the main branch's history, I created a
throw-away `hf-deploy` branch and ran
`git lfs migrate import --include="*.pt" --include-ref=refs/heads/hf-deploy`
on it. Main stays a clean fast-forward ancestor of origin/main;
the LFS-rewritten commits live only on `hf-deploy` and are pushed to
the Space's `main`. Second push succeeded. Space built on the first
try (Docker layer cache and all) — runtime stage `RUNNING` within a
few minutes.

The build still needs an `ANTHROPIC_API_KEY` Space secret for
`/query` — that's a user-only step (I do not handle their keys).

### 16.4 Tag + submission

Tagged `v0.1-hackathon` locally with a manifest of what's included
(benchmarks, subagents, dashboard, SSE, HF URL). Not pushed yet —
intentionally leaving the GitHub push and the Cerebral Valley
submission as user-gated actions.

### 16.5 What I'd do with a Day 3

- A real field cameo. NREL's EGS Collab datasets are public and
  would actually exercise the solver.
- TVD / flux-limited advection. First-order upwind diffuses
  cold-fronts too much on low-porosity, low-permeability cases.
- Streamline ensembles for UQ instead of full-field Monte Carlo —
  10× faster and qualitatively as informative for P10 / P50 / P90.
- MCP-expose GeoForce-Solver and v1.1 surrogate so any Claude Code
  user can `/install` the engines directly.

### 16.6 Day-3 morning: LFS pointer stub in Docker build

Post-deploy, `/predict?engine=surrogate` returned 500 on the live Space
while `/health`, `/scenarios`, and `/predict?engine=solver` all worked.
Root cause: HF Spaces' Docker SDK does **not** materialise LFS content
into the build context. The Dockerfile's `COPY surrogate/ ./surrogate/`
copied a 131-byte text pointer stub (`version https://git-lfs.github.com/...`)
instead of the 248 kB binary — so `torch.load` failed at startup.

Fix (committed on both branches, cherry-picked to `hf-deploy`): detect
the pointer during the build and curl the real binary from the Space's
own public resolve URL, which the HF CDN serves correctly (redirects to
Xet storage):

```dockerfile
RUN f=surrogate/weights/geoforce_cnn_v1.1.pt && \
    if head -c 64 "$f" | grep -q '^version https://git-lfs'; then \
        curl -fsSL -o "$f" \
          "https://huggingface.co/spaces/robiriu/geoforce/resolve/main/surrogate/weights/geoforce_cnn_v1.1.pt"; \
    fi
```

Rebuild succeeded (~3 min). Live verification:

| endpoint | result |
|---|---|
| `/health` | `{"ok":true}` |
| `/predict solver` (q1) | shape (40,20), T∈[60,200]°C, 3.0s |
| `/predict surrogate` (q1) | shape (32,32), T∈[188.7,205.1]°C, 4ms |

**Lesson**: treat HF Spaces Docker SDK as "git-but-no-LFS" at build
time. Runtime code can fetch LFS artefacts via `resolve/` URLs, but
don't assume `COPY` will DTRT for binary blobs.

*Last updated: 2026-04-24 — Day 3 morning, live Space fully functional on both engines.*


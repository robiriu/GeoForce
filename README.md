---
title: GeoForce
emoji: 🌋
colorFrom: red
colorTo: gray
sdk: docker
app_port: 8765
pinned: true
license: mit
short_description: Agent-orchestrated geothermal solver + CNN surrogate.
---

# GeoForce

> **Opus 4.7 agents orchestrate two engines — a newly-built open-source
> geothermal solver (GeoForce-Solver) and a deployed physics-informed CNN
> surrogate — to answer real Indonesian geothermal engineering questions.**

Built for the **"Built with Opus 4.7" Claude Code Hackathon** (Cerebral
Valley × Anthropic, 2026-04-21 → 2026-04-27) by
[Robi Dany Riupassa](https://github.com/robidanyriupassa) (ForceX AI).

---

## Why two engines?

Geothermal decisions sit on a trade-off:

- **Numerical solvers** (TOUGH, Waiwera) are trustworthy but slow and
  heavy. You can't Monte-Carlo them interactively.
- **Neural surrogates** are instant but only as good as the distribution
  they were trained on, and they silently extrapolate.

A single agent that can choose between them — or run both and report the
gap — is strictly more useful than either alone. That is what GeoForce
does. When the solver and the surrogate disagree, the dashboard shows
the Δ; when they agree, you trust the surrogate for UQ sweeps and save
two orders of magnitude of compute.

## Architecture

```
                 +--------------------------+
 user query ---> |    Opus 4.7 orchestrator |  (claude-agent-sdk)
                 +-----------+--------------+
                             |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
   +-------------+    +--------------+    +-------------+
   |  solver-    |    | surrogate-   |    |  uq-        |
   |  engineer   |    | operator     |    |  specialist |
   +------+------+    +------+-------+    +------+------+
          |                  |                    |
          v                  v                    v
   +-------------+    +--------------+    +-------------+
   | GeoForce-   |    | ReservoirCNN |    | Monte Carlo |
   | Solver      |    | v1.1 weights |    | + OAT       |
   | (Darcy +    |    | (CPU, ~30ms) |    | sensitivity |
   |  energy,    |    |              |    |             |
   |  implicit)  |    |              |    |             |
   +------+------+    +------+-------+    +------+------+
          |                  |                    |
          +---------+--------+--------------------+
                    v
           +-------------------+
           |  reviewer agent   |  physics-plausibility gate
           +---------+---------+
                     v
           +-------------------+        SSE (text / tool / result)
           |  FastAPI /query   | -------------------------------->  React UI
           +-------------------+
```

Seven supporting subagents live under `.claude/agents/` (`planner`,
`geologist`, `solver-engineer`, `surrogate-operator`, `uq-specialist`,
`visualizer`, `reviewer`, `ui-engineer`). See `AGENTS.md`.

## Dashboard

Plain React 18 + Vite + TypeScript + zustand, styled entirely with the
Claude design tokens (warm paper background, Clay `#CC785C` accent,
Source Serif 4 headings, Inter body, JetBrains Mono for tool calls). No
component library. Canvas-based magma heatmaps for the temperature
fields so the bundle stays under 160 kB.

The UI streams the agent trace via Server-Sent Events and shows the
solver and surrogate fields side-by-side with a shared color scale, so
disagreement is visually obvious.

![dashboard](docs/dashboard.png)

## Demo scenarios

Three hand-tuned Indonesian geothermal questions in `demo/scenarios.yaml`:

1. **`q1_drill_temperature`** — "If I drill at (200 m, 100 m) what
   temperature will I hit after 1 year of 0.5 kg/s cold reinjection?"
   (solver-led, line-source-style drawdown in T.)
2. **`q2_sustainable_mw`** — "How many MW can this doublet sustain for
   20 years? Give P10/P50/P90." (surrogate-led, 200-sample Monte Carlo.)
3. **`q3_well_placement`** — "Where should I place 3 new producers in
   this 400 m × 400 m field?" (surrogate-led, OAT sensitivity.)

Run all three end-to-end:

```bash
.venv/bin/python -m agent.runtime /demo
```

## Install & run

### Native (dev)

```bash
# 1. Python side
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[agent,app,dev]"

# 2. Start the API
uvicorn agent.api:app --host 0.0.0.0 --port 8765

# 3. Dashboard (separate shell)
cd dashboard
npm install
npm run dev          # http://localhost:5173 (proxies /api -> :8765)
```

Requires an `ANTHROPIC_API_KEY` in `.env` at the repo root.

### Docker (single-container, prod-ish)

```bash
docker build -t geoforce .
docker run --rm -p 8765:8765 \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  geoforce
# open http://localhost:8765
```

The image serves the built React bundle and the FastAPI on the same
port — no reverse proxy needed.

## API surface

| Method | Path          | Purpose                                        |
| ------ | ------------- | ---------------------------------------------- |
| GET    | `/health`     | Liveness (`{"ok": true}`)                      |
| GET    | `/scenarios`  | Returns `demo/scenarios.yaml`                  |
| POST   | `/predict`    | Run solver / surrogate / both for a scenario   |
| POST   | `/query`      | Stream agent events as SSE                     |

## What's in scope vs. out

**In scope:** single-phase liquid water, 2-D rectangular grids,
geothermal temperatures `25–350 °C`, pressures `0.1–30 MPa`, per-cell
injector/producer sources, Monte-Carlo + OAT sensitivity.

**Out of scope (hackathon discipline, documented honestly):**

- Two-phase flow / flashing (steam). The solver does not and will not
  model this; `/query` refuses gracefully.
- Three-dimensional reservoirs.
- Fractures as discrete objects (we smear them into permeability).
- CO₂ or brine chemistry.
- Retraining the CNN surrogate — v1.1 weights are frozen.

If the Day-1-evening analytical-benchmark gate had failed (Theis /
1-D conduction > 5 % relative error) we would have dropped the solver
and shipped surrogate-only. It didn't; both engines ship.

## Credits

- Solver numerics inspired by the TOUGH family (LBNL) — single-phase
  subset only. See `.claude/skills/tough-reference/`.
- Magma colormap: matplotlib (Apache-2.0), 12-stop approximation.
- Source Serif 4, Inter, JetBrains Mono via Google Fonts.
- Built with **Claude Code** and **Opus 4.7**.

## License

MIT — see `LICENSE`. v1.1 surrogate weights are redistributed under the
same license; see `surrogate/weights/README.md` for provenance.

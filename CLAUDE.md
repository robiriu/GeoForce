# CLAUDE.md — Project Instructions for Claude Code

This file is loaded automatically at the start of every Claude Code session in this repo. Follow these instructions exactly.

---

## 1. Project Identity

**Name:** GeoForce-CCHackathon
**Event:** Built with Opus 4.7 — Claude Code Hackathon (Cerebral Valley + Anthropic, 2026-04-21 to 2026-04-27)
**Author:** Robi Dany Riupassa
**Time budget:** 2 days from 2026-04-23
**Primary prize target:** 1st place ($50K API credits)
**Secondary:** "Best use of Claude Managed Agents" ($5K)

**One-line thesis:**
> Opus 4.7 agents orchestrate two engines — a newly-built open-source geothermal solver (**GeoForce-Solver**) and a deployed physics-informed CNN surrogate — to answer real Indonesian geothermal engineering questions in 48 hours.

See `HACKATHON-PLAN.md` for full plan, `AGENTS.md` for runtime architecture.

---

## 2. Priority Rules (override everything else)

1. **Always read `HACKATHON-PLAN.md` before proposing scope changes.** The plan is the contract.
2. **Honor the Day-1-evening GO/NO-GO checkpoint.** If the solver fails analytical benchmarks, drop it immediately and fall back to surrogate-only. See HACKATHON-PLAN.md §7.
3. **Single-phase water only.** Two-phase physics is OUT OF SCOPE. If a user suggests two-phase, point at plan §3 and refuse politely.
4. **No live simulators** — no TOUGH3, no TOUGH2, no Waiwera installs. GeoForce-Solver is the only solver we ship.
5. **Never retrain the CNN.** Use `surrogate/weights/geoforce_cnn_v1.1.pt` as-is.

---

## 3. Multi-Agent Orchestration Pattern

This project is built around 8 subagents defined in `.claude/agents/`:

| Subagent | Purpose |
|---|---|
| `planner` | Decomposes user queries, dispatches in parallel |
| `geologist` | Validates physical plausibility of reservoir parameters |
| `solver-engineer` | Builds and maintains GeoForce-Solver numerical code |
| `surrogate-operator` | Wraps v1.1 CNN inference (normalization + decoding) |
| `uq-specialist` | Monte Carlo + sensitivity (via `monte-carlo-uq` skill) |
| `visualizer` | Renders T/P fields + UQ bands (via `field-visualization` skill) |
| `reviewer` | Physics sanity check; gates outputs |
| `ui-engineer` | React dashboard + Streamlit fallback (via `claude-design-system` skill) |

**When to invoke a subagent:**
- Subagents are invoked via the `Agent` tool, using their `subagent_type` name.
- Run **in parallel** (single message, multiple `Agent` tool calls) when work is independent: e.g., solver-engineer building `darcy.py` while surrogate-operator ports CNN code.
- Run **sequentially** only when the output of one is input to the next (e.g., uq-specialist ensemble → visualizer band overlay).
- The `planner` is the default entry point for any non-trivial user query.

See `AGENTS.md` for full flow diagrams and invocation examples.

---

## 4. Skills

Defined under `.claude/skills/`:

| Skill | Purpose | Auto-invoke when |
|---|---|---|
| `iapws97-water` | IAPWS-IF97 water property computations | Any ρ(T,P), μ(T), h(T,P) call |
| `monte-carlo-uq` | Sample parameter distributions and aggregate ensembles | User asks for uncertainty, P10/P50/P90, "how confident" |
| `field-visualization` | Render 2D heatmap with optional UQ bands | Plotting T or P field |
| `analytical-benchmarks` | Theis + 1D conduction solutions for solver validation | Verifying `solver/` correctness |
| `claude-design-system` | Anthropic visual design tokens + patterns for React dashboard | Any styling decision in `dashboard/` — colors, typography, spacing, components |

Skills are the **user-invocable tooling layer**. Agents call them through natural language references. Keep skills idempotent and side-effect-free wherever possible.

---

## 5. Slash Commands

Defined under `.claude/commands/`:

- `/query <natural-language question>` — full agent pipeline
- `/validate-solver` — runs Theis + conduction benchmarks
- `/parallel-mc <scenario>` — Monte Carlo ensemble via uq-specialist
- `/demo` — runs the 3 hand-tuned demo scenarios end-to-end

---

## 6. Code Conventions

- **Python 3.11+.** Type hints everywhere. `from __future__ import annotations` at top of new files.
- **NumPy/SciPy** for numerics. **PyTorch** only for surrogate inference.
- **Dashboard:** React 18 + Vite + TypeScript + plain CSS modules with the `claude-design-system` tokens. No Material/Chakra/Ant/shadcn/Tailwind unless already in a port. Allowed additions: `zod`, `zustand`, `plotly.js`.
- **Backend API** for dashboard: FastAPI in `agent/api.py`, SSE for streaming agent trace.
- **Tests first for `solver/`** — never merge solver code without an analytical-benchmark test.
- **Normalization constants for the surrogate are frozen** — see `surrogate/encoding.py`. Do not change; they must match the v1.1 training exactly.
- **Imports:** standard library → third-party → local. One blank line between groups.
- **No unsolicited refactors.** Minimal diffs. Don't "clean up" code you didn't need to touch.
- **No comments explaining what code does** — only *why* when non-obvious.
- **No emoji in code, docs, or commit messages** unless the user asks.

---

## 7. Testing

- `pytest tests/` must pass before any commit to `main`.
- `solver/` modules require **analytical-benchmark tests** (Theis, 1D conduction). A unit test alone is not sufficient.
- `surrogate/` requires a smoke test: load weights → predict on a canonical scenario → assert output shape `(10, 32, 32)` and temperature range `[25°C, 350°C]`.
- Agent smoke test: `agent/runtime.py` must answer a canned query end-to-end without raising.

A post-write hook auto-runs affected tests; see `.claude/hooks/post_write_pytest.sh`.

---

## 8. Git Conventions

- **Branch:** work directly on `main` for hackathon speed.
- **Commits:** one logical change per commit. Imperative subject (≤60 char).
- **Trailer:** every commit Claude co-authors includes:
  ```
  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
  ```
- **Never force-push** unless user explicitly asks.
- **Never commit** files matching: `*.key`, `*-sa-key.json`, `.env`, `weights/*.pt.bak`

---

## 9. References

- `HACKATHON-PLAN.md` — authoritative scope and schedule
- `AGENTS.md` — agent architecture and flows
- `PROGRESS.md` — live task state
- `initial/` — seed planning docs from ForceX-AI (frozen, read-only)
- **Prior work:** `/home/ubuntu/ForceX-AI/products/geoforce/` — source of v1.1 weights, training code, scenario definitions, documentation

---

## 10. When in Doubt

- If a decision affects scope → stop and ask, don't silently expand.
- If a decision affects numerics correctness → invoke the `reviewer` subagent.
- If a decision affects the timeline → check HACKATHON-PLAN.md §5 and §7 buffer rules.

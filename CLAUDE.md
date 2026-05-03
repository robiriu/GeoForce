# CLAUDE.md — Project Instructions for Claude Code (v2.0 transformation branch)

This file is loaded automatically at the start of every Claude Code session in this repo. Follow these instructions exactly.

This document was rewritten on **2026-05-03** when the v0.2 hackathon scope locks were lifted to begin the v2.0 transformation. For the historical hackathon-era version, see `archive/CLAUDE-v0.2.md`.

---

## 1. Project Identity

**Name:** GeoForce
**Author:** Robi Dany Riupassa
**Active branch:** `v2-transform`

**One-line thesis (v2.0):**
> Vertex AI Gemini agents orchestrate a multi-engine geothermal stack — Waiwera-trained 3D U-Net (vapor- and liquid-dominated, two-phase) plus the frozen v1.1 CNN — to answer real Indonesian geothermal engineering questions, validated against the NREL Brady benchmark and qualitatively against published Indonesian field data.

**Authoritative documents:**
- `PLAN-V2.md` — the live execution plan (read this before any scope discussion)
- `AGENTS.md` — runtime architecture
- `PROGRESS.md` — live task state, phase-gated
- `initial/PLAN.md` — the original aspirational scope (frozen, source for v2.0 success criteria)
- `archive/PROGRESS-v0.2.md` — hackathon record (frozen, do not modify)

---

## 2. Priority Rules (override everything else)

1. **Always read `PLAN-V2.md` before proposing scope changes.** It is the operational contract for v2.0.
2. **No phase begins until the prior phase's exit gate is green.** See `PLAN-V2.md` §2.
3. **Two-phase physics is REQUIRED.** v2.0 must handle vapor-dominated (Kamojang, Darajat) and liquid-dominated (Salak, Ulubelu, Lahendong) Indonesian fields.
4. **Waiwera is the executing simulator.** TOUGH3 license is requested for cross-validation only — never blocking.
5. **v1.1 CNN weights stay frozen** for archival/comparison. The new v2.0 model is a separately trained 3D U-Net (see `PLAN-V2.md` §2 Phase 4).
6. **Free compute only.** VPS + Kaggle for simulation; Kaggle T4/P100 for training; Vertex AI GenAI App Builder credit for orchestration. No paid services without explicit approval.
7. **v0.2 hackathon build stays deployed** at `robiriu/geoforce` (HF Space) and `platform.forcex-ai.com/geoforce-v2` until v2.0 is shipped and meets all success criteria. Do not modify that Space's behaviour from this branch.
8. **`main` branch is frozen at v0.2.** All v2.0 work happens on `v2-transform`.

---

## 3. Multi-Agent Orchestration Pattern

This project is built around 8 subagents defined in `.claude/agents/`. The subagent **set** is unchanged from v0.2 — the multi-agent pattern is one of the two project deliverables. Their **responsibilities expand** for v2.0 as noted below.

| Subagent | v2.0 Purpose |
|---|---|
| `planner` | Decomposes user queries, dispatches in parallel; selects between v1.1 CNN, 3D U-Net, or Waiwera direct call |
| `geologist` | Validates parameters against Indonesian field ranges including vapor-dominated and two-phase regimes |
| `solver-engineer` | Builds, runs, and validates Waiwera input decks; maintains analytical-benchmark gates |
| `surrogate-operator` | Wraps both surrogate models (v1.1 CNN for legacy comparison; 3D U-Net for v2.0 production) |
| `uq-specialist` | Monte Carlo + sensitivity over the 3D U-Net (cheap inference) |
| `visualizer` | Renders 2D slices, 3D voxel views, UQ bands, steam-saturation overlays |
| `reviewer` | Mass + energy conservation checks; steam-table consistency; saturation constraint enforcement |
| `ui-engineer` | React dashboard + 3D voxel viewer (three.js / deck.gl); FastAPI SSE backend |

**When to invoke a subagent:**
- Subagents run via the `Agent` tool with `subagent_type` matching the agent name.
- Run **in parallel** (single message, multiple `Agent` tool calls) when work is independent.
- Run **sequentially** only when the output of one is input to the next.
- The `planner` is the default entry point for any non-trivial user query.

See `AGENTS.md` for full flow diagrams and invocation examples.

---

## 4. Skills

Defined under `.claude/skills/`. The v0.2 skill set is preserved; v2.0 adds new skills as phases require.

| Skill | Purpose | Auto-invoke when |
|---|---|---|
| `iapws97-water` | IAPWS-IF97 water property computations (full Region 1+2+4 in v2.0) | Any ρ(T,P), μ(T), h(T,P) call, including phase transitions |
| `monte-carlo-uq` | Sample parameter distributions and aggregate ensembles | User asks for uncertainty, P10/P50/P90, "how confident" |
| `field-visualization` | 2D heatmap + 3D voxel rendering with UQ bands | Plotting any field |
| `analytical-benchmarks` | Theis + 1D conduction (legacy) + Avdonin radial heat advection (new) | Verifying any solver |
| `claude-design-system` | Anthropic visual design tokens for React dashboard | Any styling decision in `dashboard/` |
| `tough-reference` | Deep knowledge of TOUGH family + Waiwera + PyTOUGH | Any solver-engineer design or input-deck decision |

Skills are the **user-invocable tooling layer**. Agents call them through natural language references. Keep skills idempotent and side-effect-free wherever possible.

---

## 5. Slash Commands

Defined under `.claude/commands/`:

- `/query <natural-language question>` — full agent pipeline
- `/validate-solver` — runs Theis + conduction benchmarks (legacy gate, kept for v1.x)
- `/parallel-mc <scenario>` — Monte Carlo ensemble via uq-specialist
- `/demo` — runs the 3 hand-tuned demo scenarios end-to-end

New v2.0 commands are added as phases demand and recorded in `PROGRESS.md`.

---

## 6. Code Conventions

- **Python 3.11+.** Type hints everywhere. `from __future__ import annotations` at top of new files.
- **NumPy/SciPy** for numerics. **PyTorch** for surrogate inference and 3D U-Net training.
- **Waiwera** for forward simulation; **PyTOUGH** for input deck templating and output reading.
- **Dashboard:** React 18 + Vite + TypeScript + plain CSS modules with `claude-design-system` tokens. 3D voxel rendering via `three.js` (lazy-loaded). No Material/Chakra/Ant/shadcn/Tailwind unless already in a port. Allowed additions: `zod`, `zustand`, `plotly.js`, `three`.
- **Backend API** for dashboard: FastAPI in `agent/api.py`, SSE for streaming agent trace. SSE event format must remain stable across LLM provider migrations.
- **Tests first** for any new solver/training code — no merge without an accompanying test in `tests/`.
- **v1.1 normalization constants are frozen** — see `surrogate/encoding.py`. Never change.
- **v2.0 normalization** lives in `model/preprocessing.py` (Phase 4) and is also frozen post-training.
- **Imports:** standard library → third-party → local. One blank line between groups.
- **No unsolicited refactors.** Minimal diffs.
- **No comments explaining what code does** — only *why* when non-obvious.
- **No emoji in code, docs, or commit messages** unless the user asks.

---

## 7. Testing

- `pytest tests/` must pass before any commit to `v2-transform`.
- Numerical solver code requires **analytical-benchmark tests** (Theis, 1D conduction, Avdonin).
- Surrogate inference requires a smoke test (load weights → predict on canonical scenario → assert output shape and physical ranges).
- Agent smoke test: `agent/runtime.py` must answer a canned query end-to-end via Vertex Gemini without raising.
- Physics audit: mass + energy conservation < 1% violation, steam-table consistency on every model release.

A post-write hook auto-runs affected tests; see `.claude/hooks/post_write_pytest.sh`.

---

## 8. Git Conventions

- **Commits:** one logical change per commit. Imperative subject (≤60 char).
- **Trailer:** every commit Claude co-authors includes:
  ```
  Co-Authored-By: Claude <noreply@anthropic.com>
  ```
- **Never force-push** unless user explicitly asks.
- **Never commit** files matching: `*.key`, `*-sa-key.json`, `.env`, `weights/*.pt.bak`, service-account keys, GCP credentials.
- **`main` is frozen.** All v2.0 development happens on `v2-transform` (or feature branches off it).

---

## 9. References

- `PLAN-V2.md` — operational execution plan for v2.0 (the live contract)
- `initial/PLAN.md` — original aspirational scope (source for success criteria, frozen)
- `archive/PROGRESS-v0.2.md` — hackathon completion record (frozen)
- `AGENTS.md` — agent architecture and flows
- `PROGRESS.md` — live task state for v2.0
- `JOURNAL.md` — narrative build log, continuous
- **Prior work in `/home/ubuntu/ForceX-AI/products/geoforce/`** — source of v1.1 weights and original training code

---

## 10. When in Doubt

- If a decision affects scope → stop and ask, don't silently expand. Check `PLAN-V2.md` first.
- If a decision affects numerics correctness → invoke the `reviewer` subagent.
- If a decision risks breaking the deployed v0.2 build at `robiriu/geoforce` → stop and confirm with user.
- If a decision burns paid GCP credit (rather than the GenAI App Builder credit) → stop and confirm.

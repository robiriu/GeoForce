# AGENTS.md — Multi-Agent Architecture

This document is the **visible map** of the agent system. It is intentionally verbose for two audiences: (1) future-us navigating the repo mid-hackathon, (2) hackathon judges who want to understand how agents are managed.

---

## Mental Model

A user asks a natural-language engineering question. A team of Opus 4.7 subagents collaborates to answer it, with **parallel execution where independent** and **sequential pipelining where dependent**. Every query produces:

1. A structured numerical answer (temperature, pressure, MW, well locations)
2. Uncertainty quantification (P10/P50/P90 where relevant)
3. A visualization (field plot + UQ band)
4. A physics sanity review

The entry point is the **planner** subagent. It decomposes the query and fans out.

---

## The Team (7 Subagents)

```
                  ┌───────────────────────┐
                  │       PLANNER         │
                  │  (query decomposition)│
                  └───────────┬───────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
   ┌──────────┐         ┌──────────────┐     ┌────────────┐
   │GEOLOGIST │         │  SOLVER-     │     │ SURROGATE- │
   │(validate │         │  ENGINEER    │     │ OPERATOR   │
   │ inputs)  │         │ (GeoForce-Solver)  │     │  (v1.1 CNN)│
   └────┬─────┘         └──────┬───────┘     └──────┬─────┘
        │                      │                    │
        └──────────────┬───────┴────────────┬───────┘
                       ▼                    ▼
                ┌───────────────┐    ┌──────────────┐
                │ UQ-SPECIALIST │    │  VISUALIZER  │
                │ (Monte Carlo) │    │ (field plots)│
                └───────┬───────┘    └──────┬───────┘
                        │                   │
                        └─────────┬─────────┘
                                  ▼
                           ┌─────────────┐
                           │  REVIEWER   │
                           │ (physics    │
                           │  sanity)    │
                           └──────┬──────┘
                                  │
                                  ▼
                             FINAL ANSWER
```

### 1. planner
**File:** `.claude/agents/planner.md`
**When:** default entry point for any user query
**Responsibilities:**
- Parse natural-language question → structured task DAG
- Decide which engine to call (solver, surrogate, or both)
- Dispatch independent tasks in **parallel**
- Aggregate results, hand to reviewer
**Tools:** Agent (dispatch), Read (plan docs)

### 2. geologist
**File:** `.claude/agents/geologist.md`
**When:** every query — validates reservoir parameters before expensive work
**Responsibilities:**
- Check parameters against Indonesian field ranges (Kamojang, Darajat, Wayang Windu)
- Flag unphysical inputs (e.g., porosity > 0.3, T > 400°C)
- Translate user intent into solver/surrogate-compatible scenario dicts
**Tools:** Read

### 3. solver-engineer
**File:** `.claude/agents/solver-engineer.md`
**When:** building, extending, or running GeoForce-Solver
**Responsibilities:**
- Write numerical code (`solver/*.py`)
- Enforce implicit-Euler coupling, Boussinesq approximation
- Run solver for user scenarios
- Debug convergence issues against analytical benchmarks
**Tools:** Read, Write, Edit, Bash (for pytest)

### 4. surrogate-operator
**File:** `.claude/agents/surrogate-operator.md`
**When:** any query benefiting from fast inference (<5 ms)
**Responsibilities:**
- Load `geoforce_cnn_v1.1.pt` once, cache in memory
- Build the 6-channel input tensor (exact v1.1 normalization)
- Run inference, de-normalize outputs
- Enforce output shape `(10, 32, 32)` and physical ranges
**Tools:** Read, Bash (for python subprocess)

### 5. uq-specialist
**File:** `.claude/agents/uq-specialist.md`
**When:** user asks for uncertainty, P10/P50/P90, "how confident", "sensitivity"
**Responsibilities:**
- Sample parameter distributions (uniform, lognormal, truncnorm)
- Dispatch N surrogate runs (cheap: N=1000 ≈ 5s wall-clock)
- Aggregate P10/P50/P90 per cell per timestep
- Run one-at-a-time sensitivity analysis
**Skills used:** `monte-carlo-uq`

### 6. visualizer
**File:** `.claude/agents/visualizer.md`
**When:** any query producing a field result
**Responsibilities:**
- Render 2D heatmap (matplotlib)
- Overlay UQ bands if uq-specialist produced them
- Optional: side-by-side solver-vs-surrogate
**Skills used:** `field-visualization`

### 7. reviewer
**File:** `.claude/agents/reviewer.md`
**When:** final step of every query, after other agents finish
**Responsibilities:**
- Mass conservation check (within ±1%)
- Energy conservation check (within ±5%)
- Monotonicity checks (pressure declines near producers, rises near injectors)
- Flag physics violations explicitly in the answer
**Tools:** Read

---

## Parallel vs Sequential Execution

This is the **core multi-agent pattern** we're showcasing. For any query, the planner identifies independent work and fans out.

**Example — Q1: "What temperature at (16, 10) in a reservoir with log_k=-14, porosity=0.08, 1 producer?"**

```
t=0    planner decomposes
       │
t=1    ┌──────────────────┬─────────────────┐      ← PARALLEL
       ▼                  ▼                 ▼
       geologist          solver-engineer   surrogate-operator
       (validate params)  (run GeoForce-Solver)   (run v1.1 CNN)
       │                  │                 │
t=2    └─ params ok       └─ solver done    └─ surrogate done
                          ────────┬─────────
                                  ▼
t=3                            visualizer  ← SEQUENTIAL (needs both outputs)
                                  │
t=4                            reviewer    ← SEQUENTIAL (gate)
                                  │
t=5                            FINAL ANSWER
```

The solver and surrogate run **simultaneously** via two parallel `Agent` tool calls in a single message. Only when both are back does the visualizer step begin.

**Example — Q2: "How many MW can this reservoir sustain for 20 years (with UQ)?"**

```
t=0    planner decomposes
t=1    [geologist]                           ← validate base params
t=2    [uq-specialist ┬ visualizer]          ← PARALLEL:
                      │                         UQ runs 1000 surrogate calls;
                      │                         visualizer pre-builds plot scaffolding
t=3    uq-specialist collects P10/P50/P90
t=4    [solver-engineer]                     ← run deterministic solver on P50
t=5    [visualizer]                          ← final plot with bands
t=6    [reviewer]                            ← physics check
t=7    FINAL ANSWER
```

---

## Invocation Examples

### From Claude Code (interactive)

In this repo, type:
```
/query What temperature will I hit drilling at grid cell (16, 10) with log_k=-14?
```

The `.claude/commands/query.md` slash command wraps a call to the `planner` subagent with your question.

### From `claude-agent-sdk` (programmatic runtime)

Defined in `agent/runtime.py`. Example:
```python
from agent.runtime import answer

reply = answer(
    "Where should I place 3 production wells in a reservoir "
    "with log_k=-13, porosity=0.10, base_T=260C, base_P=15MPa?"
)
print(reply.answer)
print(reply.plot_path)
print(reply.uq_bands)
```

The SDK creates a `ClaudeAgentClient` pinned to `claude-opus-4-7`, loads subagent definitions from `.claude/agents/`, and runs the planner.

---

## Managed Agents (prize fit)

This architecture directly maps to the "**Best use of Claude Managed Agents**" prize criterion:

- **Agents are managed as first-class files** under `.claude/agents/`
- **Orchestration is explicit**, not emergent — the planner decomposes; the DAG is visible
- **Specialization** — each agent has a narrow, auditable responsibility
- **Composability** — swapping agents (e.g., solver-engineer → 3D-solver-engineer) is a one-file change
- **Parallel execution** is real (multiple `Agent` tool calls in one message), not simulated

Judges can inspect any single `.md` file to understand what that agent does, what tools it has, and how it's invoked.

---

## Adding a New Agent

1. Create `.claude/agents/<name>.md` with YAML frontmatter (`name`, `description`, `tools?`, `model?`).
2. Keep the description crisp — it's what the planner reads to decide when to invoke.
3. Update this file (AGENTS.md) — add a row in "The Team" and, if relevant, update the flow diagram.
4. Add a smoke test in `tests/` that invokes the agent on a canned input.

---

## Design Principles

1. **Fewer, sharper agents** — 7 is enough; splitting further adds coordination cost without value.
2. **Explicit parallelism** — if two calls can run in one message, they do.
3. **Reviewer is always last** — no answer leaves the system un-gated.
4. **Skills over prompts** — reusable logic (IAPWS, MC, viz) lives in `.claude/skills/`, not baked into agent prompts.
5. **Honest fallback** — if GeoForce-Solver fails analytical benchmarks by Day 1 EOD, we drop the solver and the planner falls back to surrogate-only. The architecture survives either way.

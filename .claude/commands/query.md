---
description: Run a natural-language engineering query through the full GeoForce agent pipeline (planner → specialists in parallel → reviewer). The argument is the question text.
argument-hint: <natural-language question>
---

# /query

You are executing the **GeoForce query pipeline** on the user's question.

**User's question:** $ARGUMENTS

## Steps

1. Delegate to the `planner` subagent via the `Agent` tool. Pass the raw user question as the planner's prompt.
2. The planner will dispatch specialists (geologist, solver-engineer, surrogate-operator, uq-specialist, visualizer, reviewer) as needed, in parallel where possible.
3. When the planner returns, present its structured answer to the user:
   - Direct answer (natural language)
   - Scenario used (validated dict)
   - Engines used (solver, surrogate, or both)
   - UQ bands if applicable
   - Plot paths
   - Reviewer findings

## Guardrails

- If the question is outside Q1–Q3 scope (see HACKATHON-PLAN.md §3), decline and explain.
- If the planner reports a reviewer reject, surface the rejection reason prominently.
- If the fallback is active (solver dropped), skip the solver-vs-surrogate comparison.

## Example questions this handles

- "What temperature will I hit drilling at cell (16, 10) with log_k=-14, porosity=0.08?"
- "How many MW can a reservoir at 250°C, 15 MPa, log_k=-13.5, porosity=0.10 sustain for 20 years? Include uncertainty."
- "Where should I place 3 production wells for maximum 20-year energy output?"

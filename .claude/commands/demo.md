---
description: Run the three hand-tuned hackathon demo scenarios (Q1, Q2, Q3) end-to-end through the agent pipeline. Used for demo video recording and final sanity check before submission.
---

# /demo

Execute the GeoForce demo reel — three hand-tuned scenarios designed for the 90-second demo video.

## Steps

1. Load `demo/scenarios.yaml` and verify all three scenarios (Q1, Q2, Q3) are defined.
2. For each scenario, invoke the `planner` subagent with the canonical question text.
3. Collect outputs in order:
   - **Q1 (Drilling target):** deterministic T prediction at target cell, via both engines if solver is live
   - **Q2 (Sustainability):** 20-year production with P10/P50/P90 uncertainty
   - **Q3 (Well placement):** 3 ranked candidate locations for new production wells
4. Verify all plots saved under `demo/figures/`.
5. Print a concise summary table to stdout (one row per scenario, with the answer, UQ band, wall-clock time).
6. Flag any reviewer warnings or rejections.

## Output target

At the end, the terminal should show three tidy blocks, one per question, each with:
- The question
- The direct answer
- Plot path(s)
- Reviewer status

The Streamlit app will consume the same data structure but render interactively.

## Preconditions

- `surrogate/weights/geoforce_cnn_v1.1.pt` exists and loads
- If solver is live: `pytest tests/test_solver_theis.py tests/test_solver_conduction.py` passes
- `demo/scenarios.yaml` populated
- `ANTHROPIC_API_KEY` in environment

## Failure modes

- Missing weights → stop, alert user
- Failed reviewer on any scenario → flag but don't block (demo continues, warning noted)
- Streamlit UI not needed for this command — it's CLI-only for recording prep

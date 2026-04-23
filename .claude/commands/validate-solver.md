---
description: Run the TinyTOUGH analytical benchmark suite (Theis pressure + 1D conduction temperature). The Day 1 GO/NO-GO checkpoint depends on this.
---

# /validate-solver

Run the full analytical-benchmark validation for TinyTOUGH.

## Steps

1. Run `pytest tests/test_solver_theis.py -v` via Bash.
2. Run `pytest tests/test_solver_conduction.py -v` via Bash.
3. Report:
   - Pass/fail for each
   - Max relative error vs analytical
   - Wall-clock runtime
4. If either fails: invoke the `solver-engineer` subagent with the failure details and ask for a diagnosis. Do **not** silently modify tests to pass.
5. Update `PROGRESS.md` with the result under the Day 1 checkpoint.

## Pass criteria (both required)

- `test_solver_theis.py` — max relative pressure error < 5%
- `test_solver_conduction.py` — max relative temperature error < 5% **and** max absolute error < 5°C

## On failure

This is a blocking event. Per HACKATHON-PLAN.md §7:
- First failure → attempt one targeted fix (smaller Δt, finer grid, BC check)
- Second failure → invoke the Day 1 fallback: drop `solver/` from critical path; the project continues surrogate-only

Report the fallback trigger explicitly to the user.

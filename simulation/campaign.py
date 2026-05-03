"""Campaign driver: ties LHS sampling -> queue -> deck rendering -> Waiwera.

Runs in two modes:

  * `enqueue` (VPS): sample N scenarios via LHS and insert as pending jobs.
  * `consume` (Kaggle): claim a job range, render decks, invoke Waiwera,
    mark each job done/failed. Waiwera invocation is gated on the
    `WAIWERA_AVAILABLE` env var so the same script is safe to import on
    the VPS without Waiwera installed.

This module deliberately keeps Waiwera *invocation* in one place (the
`_run_waiwera` helper). The deck rendering, queue access, and bookkeeping
are pure and unit-testable on the VPS.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from simulation import queue as job_queue
from simulation.deck import write_deck
from simulation.grid import LayerProps, build_grid
from simulation.sampling import Scenario, load_spec, sample
from simulation.wells import place_wells

WAIWERA_BIN = os.environ.get("WAIWERA_BIN", "waiwera")


def _waiwera_available() -> bool:
    """True when Waiwera is callable on $PATH (Kaggle session). Honors override."""
    if os.environ.get("WAIWERA_AVAILABLE", "").lower() in {"1", "true", "yes"}:
        return True
    if os.environ.get("WAIWERA_AVAILABLE", "").lower() in {"0", "false", "no"}:
        return False
    return shutil.which(WAIWERA_BIN) is not None


def enqueue_campaign(n: int, seed: int = 0, db_path: Path | None = None) -> int:
    """Sample `n` LHS scenarios and insert them as pending jobs. Returns count."""
    conn = job_queue.connect(db_path) if db_path else job_queue.connect()
    scenarios = sample(n, seed=seed)
    for s in scenarios:
        job_queue.enqueue(conn, s.scenario_id, asdict(s))
    return len(scenarios)


def _grid_for_scenario(scenario: Scenario):
    """Build a GridSpec from a scenario, with default caprock + basement."""
    spec = load_spec()
    cap = LayerProps(**spec["default_layers"]["caprock"])
    bas = LayerProps(**spec["default_layers"]["basement"])
    return build_grid(cap, scenario.reservoir_props, bas)


def render_job(scenario: Scenario, out_dir: Path):
    """Render a job's deck + mesh to `out_dir`. Pure I/O on filesystem."""
    grid = _grid_for_scenario(scenario)
    rng = np.random.default_rng(hash(scenario.scenario_id) & 0xFFFFFFFF)
    wells = place_wells(
        n_prod=scenario.n_production_wells,
        n_inj=scenario.n_injection_wells,
        prod_rate_kg_s=scenario.production_rate_kg_s,
        inj_rate_kg_s=scenario.injection_rate_kg_s,
        inj_temp_C=scenario.injection_temp_C,
        rng=rng,
    )
    return write_deck(scenario, grid, wells, out_dir)


def _run_waiwera(json_path: Path, work_dir: Path, timeout_s: int = 7200) -> subprocess.CompletedProcess:
    """Invoke the Waiwera CLI. Only called inside Kaggle (or wherever Waiwera lives)."""
    return subprocess.run(
        [WAIWERA_BIN, json_path.name],
        cwd=str(work_dir),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )


def consume(
    worker_id: str,
    work_root: Path,
    max_jobs: int = 1,
    db_path: Path | None = None,
) -> list[dict]:
    """Claim up to `max_jobs` pending jobs and run each through Waiwera.

    Returns a list of result dicts (one per job): scenario_id, status,
    runtime_s, output_path or error.
    """
    if not _waiwera_available():
        raise RuntimeError(
            f"WAIWERA not on PATH (looked for `{WAIWERA_BIN}`). "
            "Set WAIWERA_AVAILABLE=1 to override for testing."
        )
    conn = job_queue.connect(db_path) if db_path else job_queue.connect()
    work_root = Path(work_root)
    work_root.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    jobs = job_queue.claim(conn, worker_id=worker_id, n=max_jobs)
    for job in jobs:
        scenario = Scenario(**job.params)
        run_dir = work_root / scenario.scenario_id
        t0 = time.time()
        try:
            bundle = render_job(scenario, run_dir)
            cp = _run_waiwera(bundle.json_path, run_dir)
            elapsed = time.time() - t0
            if cp.returncode == 0:
                output_h5 = run_dir / f"{scenario.scenario_id}.h5"
                job_queue.mark_done(conn, scenario.scenario_id, str(output_h5), elapsed)
                results.append(
                    {"scenario_id": scenario.scenario_id, "status": "done", "runtime_s": elapsed,
                     "output_path": str(output_h5)}
                )
            else:
                err = (cp.stderr or cp.stdout)[-2048:]
                job_queue.mark_failed(conn, scenario.scenario_id, err)
                results.append({"scenario_id": scenario.scenario_id, "status": "failed", "error": err})
        except Exception as exc:  # noqa: BLE001 — we record any crash
            job_queue.mark_failed(conn, scenario.scenario_id, repr(exc))
            results.append({"scenario_id": scenario.scenario_id, "status": "failed", "error": repr(exc)})
    return results

# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # GeoForce v2.0 — Waiwera Simulation Burst (Kaggle)
#
# **Owner:** robidanyriu
# **Slug:** robidanyriu/forcex-ai-geoforce-sim-burst
#
# This notebook runs in a Kaggle CPU session (no GPU needed). It:
#
# 1. Pulls the Waiwera Docker image (or installs the conda fallback).
# 2. Runs the **TOUGH2 RFP analytical benchmark** — radial flow problem with a
#    closed-form solution. Block B exit gate: < 1% relative error.
# 3. Clones the GeoForce repo at the v2-transform branch.
# 4. Pulls the queued job range (passed via the `JOB_RANGE` Kaggle secret /
#    notebook parameter) from the SQLite queue.db that was uploaded as a
#    Kaggle Dataset attachment.
# 5. Runs each scenario through Waiwera, writes HDF5 outputs.
# 6. Pushes results to HuggingFace Dataset `ForceX-AI/geoforce-v2-data`.
#
# **Time budget:** 12-hour Kaggle session cap. Pilot 100 scenarios across
# 5 concurrent sessions = ~20 jobs/session. Resumable by job-range, so
# session timeouts are not catastrophic.

# %% [markdown]
# ## 0. Parameters (Kaggle "Add data" + secrets)

# %% tags=["parameters"]
# These get overridden by Papermill / Kaggle's notebook parameters.
GIT_REF = "v2-transform"
JOB_RANGE_START = 0
JOB_RANGE_END = 20  # exclusive; runs jobs in [start, end)
WORKER_ID = "kaggle-session-A"
WAIWERA_DOCKER_TAG = "waiwera/waiwera:latest"
HF_DATASET_REPO = "ForceX-AI/geoforce-v2-data"

# %% [markdown]
# ## 1. Environment

# %%
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

WORK_ROOT = Path("/kaggle/working")
REPO_DIR = WORK_ROOT / "GeoForce"
QUEUE_DB = WORK_ROOT / "queue.db"  # uploaded as Kaggle Dataset
OUTPUT_DIR = WORK_ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

print("Python:", sys.version.split()[0])
print("CPU count:", os.cpu_count())
subprocess.run(["free", "-h"], check=False)

# %% [markdown]
# ## 2. Install Waiwera (Docker preferred, conda fallback)
#
# Kaggle sessions support Docker for image-based environments but not
# inside a notebook. We instead install Waiwera via conda from the
# `waiwera` conda-forge channel, which builds with PETSc + MPI in
# ~5 minutes on Kaggle CPUs.

# %%
WAIWERA_INSTALLED = False
try:
    out = subprocess.run(["which", "waiwera"], capture_output=True, text=True)
    if out.stdout.strip():
        print("Waiwera already on PATH:", out.stdout.strip())
        WAIWERA_INSTALLED = True
except Exception as exc:
    print("which waiwera failed:", exc)

if not WAIWERA_INSTALLED:
    print("Installing Waiwera via conda-forge ...")
    cmd = [
        "conda", "install", "-y",
        "-c", "conda-forge",
        "waiwera",
    ]
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    print("conda stdout (tail):", (cp.stdout or "")[-2000:])
    print("conda stderr (tail):", (cp.stderr or "")[-2000:])
    cp = subprocess.run(["which", "waiwera"], capture_output=True, text=True)
    WAIWERA_INSTALLED = bool(cp.stdout.strip())

assert WAIWERA_INSTALLED, "Waiwera install failed — see logs above; fall back to TOUGH2 mock?"
print("Waiwera ready.")

# %% [markdown]
# ## 3. Clone GeoForce repo and install Python deps

# %%
if not REPO_DIR.exists():
    subprocess.run(
        ["git", "clone", "--depth=1", "--branch", GIT_REF,
         "https://github.com/robiriu/GeoForce.git", str(REPO_DIR)],
        check=True,
    )

os.chdir(REPO_DIR)
sys.path.insert(0, str(REPO_DIR))

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q",
     "pytough", "scipy", "pyyaml", "h5py", "huggingface_hub"],
    check=True,
)

# %% [markdown]
# ## 4. Validate: RFP (Radial Flow Problem) benchmark
#
# Single-phase liquid radial flow into a point sink — closed-form Theis
# solution for pressure drawdown. We use the same analytical helper that
# gates the in-repo solver tests (`solver.benchmarks.theis`).
#
# **Strategy:** the in-repo Theis benchmark already validates the v0.2
# Python solver against the analytical solution at <1%. For Block B we
# additionally need Waiwera itself to match. We:
#
#   1. Generate a 2D radial Waiwera deck (single point sink, no-flow
#      boundary far enough that the Theis window holds).
#   2. Run Waiwera, parse the H5 output for cell pressures.
#   3. Compare against `theis_pressure_change` at the same (r, t) points.
#   4. Assert max relative error < 1%.
#
# The deck-builder for the RFP geometry lives at `simulation/rfp.py` so
# it can be unit-tested on the VPS without Waiwera. **TODO:** ship that
# module in the next commit; the cell below will import it.

# %%
try:
    from simulation.rfp import build_rfp_deck, parse_rfp_output, run_waiwera_rfp
    from solver.benchmarks.theis import theis_pressure_change

    rfp_dir = WORK_ROOT / "rfp"
    rfp_dir.mkdir(exist_ok=True)
    deck = build_rfp_deck(rfp_dir)
    cp = run_waiwera_rfp(deck, work_dir=rfp_dir)
    assert cp.returncode == 0, f"Waiwera failed on RFP: {cp.stderr[-2000:]}"

    numerical = parse_rfp_output(rfp_dir / "rfp.h5")
    rel_errs = []
    for (r, t, p_num) in numerical:
        p_ana = theis_pressure_change(r=r, t=t, **deck.theis_params)
        rel_errs.append(abs(p_num - p_ana) / abs(p_ana))
    max_err = max(rel_errs)
    print(f"RFP max relative error vs Theis: {max_err*100:.3f}%")
    assert max_err < 0.01, "Block B exit gate failed: RFP > 1% off analytical"
    print("RFP benchmark passed within 1% — Block B exit gate green.")
except ImportError as exc:
    print(f"RFP benchmark module not yet in repo ({exc}).")
    print("Block B is partial — re-run after `simulation/rfp.py` lands.")
    raise SystemExit(0)

# %% [markdown]
# ## 5. Pull job range from SQLite queue and run each scenario

# %%
from simulation import queue as job_queue
from simulation.campaign import consume

assert QUEUE_DB.exists(), f"queue.db not attached at {QUEUE_DB} — add it as a Kaggle Dataset"
shutil.copy(QUEUE_DB, REPO_DIR / "simulation" / "queue.db")

t_start = time.time()
results = consume(
    worker_id=WORKER_ID,
    work_root=OUTPUT_DIR,
    max_jobs=(JOB_RANGE_END - JOB_RANGE_START),
)
elapsed = time.time() - t_start

print(f"Ran {len(results)} jobs in {elapsed:.0f}s "
      f"(avg {elapsed/max(len(results),1):.1f}s per scenario).")
print("Successes:", sum(1 for r in results if r.get("status") == "done"))
print("Failures: ", sum(1 for r in results if r.get("status") == "failed"))

# %% [markdown]
# ## 6. Push results to HuggingFace `ForceX-AI/geoforce-v2-data`

# %%
from huggingface_hub import HfApi

HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
assert HF_TOKEN, "Set HF_TOKEN as a Kaggle secret with write access to ForceX-AI org"

api = HfApi(token=HF_TOKEN)
api.upload_folder(
    folder_path=str(OUTPUT_DIR),
    repo_id=HF_DATASET_REPO,
    repo_type="dataset",
    path_in_repo=f"runs/{WORKER_ID}/{int(time.time())}",
    commit_message=f"Pilot batch from {WORKER_ID} ({len(results)} scenarios)",
)
print("Pushed to HF.")

# %% [markdown]
# ## 7. Push the updated queue.db back as a Kaggle Dataset version
#
# (Done outside the notebook by the orchestrator that owns the queue.)

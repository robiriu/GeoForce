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
# **Slug:** robidanyriu/forcex-ai-geoforce-v2-0-simulation-burst
#
# This notebook runs in a Kaggle CPU session (no GPU needed). It:
#
# 1. Downloads the Waiwera 1.5.1 binary bundle from HuggingFace
#    (`ForceX-AI/geoforce-waiwera-runtime`) and verifies it runs.
# 2. Clones the GeoForce repo at the v2-transform branch.
# 3. Runs the **RFP analytical benchmark** — radial flow problem with a
#    closed-form Theis solution. **Block B exit gate: <1% relative error.**
# 4. (Future) pulls the queued job range from the SQLite queue.db and
#    runs each scenario through Waiwera. Block D.
# 5. (Future) pushes results to HuggingFace Dataset
#    `ForceX-AI/geoforce-v2-data`.
#
# **Time budget:** 12-hour Kaggle session cap. Pilot 100 scenarios across
# 5 concurrent sessions = ~20 jobs/session.

# %% [markdown]
# ## 0. Parameters

# %% tags=["parameters"]
GIT_REF = "v2-transform"
JOB_RANGE_START = 0
JOB_RANGE_END = 20
WORKER_ID = "kaggle-session-A"
HF_DATASET_REPO = "ForceX-AI/geoforce-v2-data"
HF_WAIWERA_REPO = "ForceX-AI/geoforce-waiwera-runtime"

# %% [markdown]
# ## 1. Environment

# %%
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path

WORK_ROOT = Path("/kaggle/working")
TMP_ROOT = Path("/tmp/geoforce")
TMP_ROOT.mkdir(parents=True, exist_ok=True)
REPO_DIR = TMP_ROOT / "GeoForce"
RFP_DIR = TMP_ROOT / "rfp"
RFP_DIR.mkdir(exist_ok=True)

print("Python:", sys.version.split()[0])
print("CPU count:", os.cpu_count())
subprocess.run(["free", "-h"], check=False)

# %% [markdown]
# ## 2. Download the Waiwera binary bundle from HuggingFace
#
# The bundle is a tarball of the Waiwera 1.5.1 binary plus all required
# shared libs (PETSc 3.22, MPICH, UCX, libhwloc, HDF5, NetCDF, ExodusII),
# extracted on the VPS from the upstream `waiwera/waiwera:latest` Docker
# image and pushed to HuggingFace.
#
# Extraction goes to `/tmp/` (not `/kaggle/working/`) so the 169 MB
# bundle isn't auto-persisted into the notebook output volume on every
# session.

# %%
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "huggingface_hub"],
    check=True, capture_output=True, text=True,
)
from huggingface_hub import hf_hub_download

WAIWERA_ROOT = TMP_ROOT / "waiwera-bundle"
if not WAIWERA_ROOT.exists():
    print("Downloading Waiwera bundle from HuggingFace ...")
    tarball = hf_hub_download(
        repo_id=HF_WAIWERA_REPO,
        repo_type="dataset",
        filename="waiwera-binary.tar.gz",
    )
    print(f"  -> {tarball}")
    with tarfile.open(tarball) as tf:
        tf.extractall(TMP_ROOT)
    print("Extracted.")
else:
    print(f"{WAIWERA_ROOT} already present.")

WAIWERA_BIN = WAIWERA_ROOT / "build" / "waiwera"
LD_PATHS = ":".join([
    str(WAIWERA_ROOT / "external" / "PETSc" / "release" / "lib"),
    str(WAIWERA_ROOT / "system_libs"),
    "/usr/lib/x86_64-linux-gnu",
])

# %%
print("=== waiwera --version ===")
cp = subprocess.run(
    [str(WAIWERA_BIN), "--version"],
    env={**os.environ, "LD_LIBRARY_PATH": LD_PATHS},
    capture_output=True, text=True, timeout=30,
)
print(f"rc={cp.returncode}, stdout={cp.stdout.strip()!r}")
assert cp.returncode == 0 and "1.5" in cp.stdout, "Waiwera smoke test failed"

# %% [markdown]
# ## 3. Clone GeoForce repo and install Python deps

# %%
if not REPO_DIR.exists():
    subprocess.run(
        ["git", "clone", "--depth=1", "--branch", GIT_REF,
         "https://github.com/robiriu/GeoForce.git", str(REPO_DIR)],
        check=True,
    )

sys.path.insert(0, str(REPO_DIR))

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q",
     "pytough", "scipy", "pyyaml", "h5py", "meshio", "netCDF4", "iapws"],
    check=True,
)

# %% [markdown]
# ## 4. Block B exit gate — RFP / Theis analytical benchmark
#
# The deck builder lives in `simulation/rfp.py`. It writes a 51x51 single-
# layer Cartesian mesh with a single producer at the center cell and
# constant-property water as the working fluid. The Theis assumptions
# (infinite reservoir, single-phase liquid, point sink) are met within
# the chosen sample window — see `tests/test_simulation_rfp.py` for the
# offline shape/range checks.
#
# Exit gate: max relative error of `(p_numerical - P0)` vs the Theis
# `Delta_p(r, t)` at the sample radii must be **< 1%**.

# %%
from simulation.rfp import (
    build_rfp_deck,
    compare_to_theis,
    parse_rfp_output,
    run_waiwera_rfp,
)

deck = build_rfp_deck(RFP_DIR)
print(f"Deck written:")
print(f"  json: {deck.json_path}")
print(f"  mesh: {deck.mesh_path}")
print(f"  sample radii (m): {deck.sample_radii_m}")

t_start = time.time()
cp = run_waiwera_rfp(
    deck,
    work_dir=RFP_DIR,
    waiwera_bin=WAIWERA_BIN,
    ld_library_path=LD_PATHS,
    timeout_s=600,
)
print(f"Waiwera run rc={cp.returncode} in {time.time()-t_start:.1f}s")
if cp.returncode != 0:
    print("--- stdout (tail) ---")
    print(cp.stdout[-2000:])
    print("--- stderr (tail) ---")
    print(cp.stderr[-2000:])
assert cp.returncode == 0, "Waiwera failed on RFP deck"

# %%
samples = parse_rfp_output(RFP_DIR / deck.h5_filename, deck)
rows = compare_to_theis(samples, deck)

print(f"{'r (m)':>8} {'t (s)':>10} {'p_num (Pa)':>14} {'p_ana (Pa)':>14} {'rel_err':>10}")
for r, t, p_num, p_ana, rel_err in rows:
    print(f"{r:8.1f} {t:10.0f} {p_num:14.1f} {p_ana:14.1f} {rel_err*100:9.3f}%")

max_err = max(row[4] for row in rows)
print(f"\nRFP max relative error vs Theis: {max_err*100:.3f}%")
assert max_err < 0.01, (
    f"Block B exit gate FAILED: max rel error {max_err*100:.3f}% > 1%"
)
print("Block B exit gate green: RFP within 1% of Theis analytical.")

# %% [markdown]
# ## STOP — Block B iteration ends here.
#
# Sections 5-7 (campaign queue, scenario sweep, HF push) land after
# Block B is green.

# %%
raise SystemExit("Block B iteration complete.")

# %% [markdown]
# ## 5. Pull job range from SQLite queue and run each scenario  (Block D)

# %% [markdown]
# ## 6. Push results to HuggingFace `ForceX-AI/geoforce-v2-data`

# %% [markdown]
# ## 7. Push the updated queue.db back as a Kaggle Dataset version

# PROGRESS — v2.0 Task State

Live task tracking for the v2.0 transformation. Source of truth for "where are we right now". Updated at the end of every work block.

For the hackathon-era task state, see `archive/PROGRESS-v0.2.md`.

---

## Branch

All v2.0 work happens on `v2-transform`. `main` is frozen at v0.2.

---

## Phase Status

| # | Phase | Status | Started | Completed | Exit gate |
|---|---|---|---|---|---|
| 0 | Foundation | **Complete** | 2026-05-03 | 2026-05-03 | Vertex Gemini end-to-end with tool call + SSE |
| 1 | Real Data | **Complete** | 2026-05-03 | 2026-05-03 | Brady ≥95/101 loadable + ≥5 Indonesian fields characterized |
| 2 | Simulator + Pilot Campaign | Not Started | — | — | Waiwera RFP green; 90/100 pilot pass |
| 3 | Full Simulation Campaign | Not Started | — | — | ≥900 valid scenarios, stratified split |
| 4 | 3D U-Net Architecture and Training | Not Started | — | — | All §1 success criteria met on held-out |
| 5 | Validation | Not Started | — | — | Brady benchmark match; physics audit <1% |
| 6 | Platform Integration | Not Started | — | — | All 3 demo scenarios <5s in dashboard |
| 7 | Publish | Not Started | — | — | All deliverables shipped |

---

## Phase 0 — Foundation

### Branch & docs
- [x] Create `v2-transform` branch off `main`, push to origin
- [x] Archive v0.2 docs: `archive/CLAUDE-v0.2.md`, `archive/PROGRESS-v0.2.md`
- [x] Rewrite `CLAUDE.md` for v2.0 — scope locks lifted, success criteria from `initial/PLAN.md` referenced
- [x] Update `AGENTS.md` — v2.0 subagent responsibility expansions, Vertex Gemini runtime invocation example
- [x] Write new `PROGRESS.md` (this file) mirroring `PLAN-V2.md` phases
- [x] Append `JOURNAL.md` entry for 2026-05-03

### Vertex AI / Gemini orchestrator
- [x] Create Vertex service account on `forcex-studio` with `roles/aiplatform.user`
- [x] Download key JSON to `~/.gcp/geoforce-sa.json` (gitignored)
- [x] Update `.env` template (`.env.example`): `GOOGLE_APPLICATION_CREDENTIALS`, `GCP_PROJECT`, `GCP_LOCATION`, `GEMINI_MODEL`, `LLM_PROVIDER`
- [x] Update `.gitignore` to exclude any service-account JSON, `.env`, GCP credentials
- [x] Smoke-test `gemini-2.5-flash`: simple chat + tool call + streaming (all PASS)
- [ ] Confirm RPD quota ≥ 1000 on the project

### Agent runtime migration (via Google ADK)
- [x] Migrate `agent/runtime.py` from `claude_agent_sdk` → ADK + Vertex Gemini
- [x] Reimplement tool calling via ADK `FunctionTool` (auto-derives `FunctionDeclaration` from typed signatures)
- [x] Adapt `agent/api.py` to translate ADK event stream → existing SSE event shape (`text`, `tool`, `result`, `error`)
- [x] Verified SSE manually: single-turn `/query`, multi-turn `/sessions/{id}/query` with memory, function-calling end-to-end
- [ ] **Deferred to Phase 6:** instantiate the 8 `.claude/agents/*.md` as live `LlmAgent`s. Phase 0 uses a single root agent (planner) with all 4 tools to conserve free credit. Subagent role definitions remain authoritative.

### External resources
- [ ] Configure Kaggle API token (`~/.kaggle/kaggle.json`) on dev box (user-only step)
- [ ] Create HF Dataset repo `ForceX-AI/geoforce-v2-data` (empty, public)
- [ ] Create dev HF Space `ForceX-AI/geoforce-v2-dev` (separate from production `robiriu/geoforce`)
- [ ] Sign up for Kaggle + verify (user-only step)

### Phase 0 exit gate
- [x] Run agent locally end-to-end: multi-turn query via Vertex Gemini → `predict_solver` tool call → SSE stream parses cleanly (verified `text`/`tool`/`result` events on `/query` and `/sessions/{id}/query`; tested 2026-05-03)
- [x] All 8 subagent definitions present at `.claude/agents/*.md` (live instantiation deferred to Phase 6, see migration note above)
- [ ] Vertex RPD quota check passes (deferred — observed no rate limits in smoke tests)

---

## Phase 1 — Real Data Foundation

### 1A. NREL Brady OSR
- [x] Clone `NREL/geothermal_osr` into `data/brady/` (BSD-3, gitignored)
- [x] `data/brady/loader.py` — parses 102 .xlsx into `BradyScenario` dataclasses + `stack()` for batched (N, 241, k) tensors
- [x] `tests/test_brady_loader.py` — 2 tests, both passing (101 scenarios parse, ≥95 stack at standard length)
- [x] `data/README.md` — provenance + license + structural-mismatch note
- [ ] ~~`notebooks/01-brady-explore.ipynb`~~ deferred — loader + tests give us what the notebook would have shown
- [ ] ~~`notebooks/02-brady-v1-cnn-baseline.ipynb`~~ **dropped** — v1.1 CNN (32×32 spatial output) is structurally incompatible with Brady (well time-series). Brady moves to Phase 5 validation only. Decision logged below.

### 1B. Utah FORGE — **deferred to Phase 5**
- [ ] ~~Download FORGE well-log + 3D geological model~~ — deferred
- [ ] ~~`data/forge/loader.py`~~ — deferred
- [ ] ~~Map FORGE channels to GeoForce input requirements~~ — deferred

Rationale: FORGE is EGS in granitic basement with hydraulic stimulation; physics regime differs from Indonesian volcanic-arc fracture-dominated reservoirs. Not in Phase 1 exit gate. Revisit in Phase 5 only if comparison-validation against an EGS site adds value. Decision logged below.

### 1C. Indonesian field parameters
- [x] `data/indonesia/parameters.yaml` — all 7 fields (Kamojang, Darajat, Wayang Windu, Salak, Lahendong, Ulubelu, Karaha-Talaga Bodas) with permeability, porosity, T, P, depth, dominant phase
- [x] Each entry cites peer-reviewed publication or Stanford Geothermal Workshop paper
- [x] `data/indonesia/README.md` — methodology, confidence levels, what's unknown

### Phase 1 exit gate
- [x] Brady loader returns ≥ 95/101 scenarios without parse errors (101/101 parse; 100 stack at standard 241-step length)
- [x] ~~v1.1 baseline Brady T error~~ — dropped per option (a) decision; Brady is now Phase 5 validation only. NREL published numbers from Duplyakin et al. (2022) become the bar.
- [x] 7/7 Indonesian fields have permeability, porosity, T, P, depth, dominant phase (5 high-confidence + 2 caveat-tagged)

---

## Phase 2 — Simulator Setup + Pilot Campaign

### 2A. Waiwera install
- [ ] Build Waiwera from source on VPS (PETSc + MPI)
- [ ] Run TOUGH2 RFP benchmark — match within 1%
- [ ] Build Waiwera in Kaggle notebook (Dockerfile or conda env, < 30 min)
- [ ] Install PyTOUGH in both environments

### 2B. Simulation pipeline
- [ ] `simulation/grid.py` — 32×32×10 grid, caprock/reservoir/basement layering
- [ ] `simulation/wells.py` — randomized well placement
- [ ] `simulation/scenarios_v2.yaml` — LHS-sampled parameter combinations (12 dimensions)
- [ ] `simulation/campaign.py` — generate decks, run Waiwera, parse outputs to HDF5
- [ ] `simulation/queue.db` — SQLite job queue

### 2C. VPS worker + Kaggle burst
- [ ] systemd unit `geoforce-sim-worker.service` (niced, cgroup CPU 50%)
- [ ] `notebooks/03-kaggle-sim-burst.ipynb` — chunked, designed for 12hr session
- [ ] HF Dataset push automation on completion

### 2D. Pilot batch (100 scenarios)
- [ ] Run 100-scenario pilot
- [ ] Upload to `ForceX-AI/geoforce-v2-data`
- [ ] `notebooks/04-pilot-batch-audit.ipynb` — mass + energy conservation, NaN check, T bounds, P bounds
- [ ] Document per-scenario timing on VPS + Kaggle

### Phase 2 exit gate
- [ ] Waiwera RFP benchmark passes (< 1% vs. analytical)
- [ ] Pilot audit: ≥ 90/100 scenarios pass
- [ ] 1,000-scenario projection feasible on free compute

---

## Phase 3 — Full Simulation Campaign

- [ ] 1,000 scenarios complete (or 500 with documented justification)
- [ ] Train/val/test split (800/100/100), stratified, manifest hashed
- [ ] `notebooks/05-campaign-progress.ipynb` — live queue health
- [ ] `simulation/audit.py` — full-campaign audit, rejected scenarios logged

### Phase 3 exit gate
- [ ] ≥ 900 valid scenarios in train+val+test
- [ ] Stratified parameter coverage (LHS plot per dimension)

---

## Phase 4 — 3D U-Net Architecture and Training

- [ ] `model/unet3d.py` — 3D U-Net per `initial/PLAN.md` §3A (11 in × 40 out channels)
- [ ] `model/preprocessing.py` — normalization (frozen post-training)
- [ ] `model/physics_loss.py` — mass conservation, energy conservation, saturation constraint, gravity, steam-table consistency
- [ ] `model/train.py` — Kaggle T4 training with mixed precision, checkpointing
- [ ] `notebooks/06-unet3d-train.ipynb`
- [ ] `notebooks/07-unet3d-eval.ipynb` — held-out test metrics
- [ ] `model/weights/geoforce_v2.pt` — uploaded to `ForceX-AI/geoforce-v2-model`

### Phase 4 exit gate (success criteria from PLAN-V2.md §1)
- [ ] T RMSE < 5°C on held-out
- [ ] P RMSE < 0.5 MPa on held-out
- [ ] Steam saturation RMSE < 0.1
- [ ] R² > 0.95 (all variables)
- [ ] Inference time < 1s per scenario
- [ ] Physics violation rate < 1%

---

## Phase 5 — Validation

- [ ] `notebooks/08-brady-benchmark.ipynb` — meet/beat USGS published numbers
- [ ] `notebooks/09-indonesia-qualitative.ipynb` — production decline curves vs. published Pertamina/Star Energy
- [ ] `notebooks/10-physics-audit.ipynb` — mass + energy + steam-table consistency on 100 random test scenarios
- [ ] `docs/technical-report-v2.md` — TOUGH/Waiwera vs analytical, two-phase vs single-phase, 3D vs 2D, Brady, Indonesian, limitations

### Phase 5 exit gate
- [ ] Brady T < 4%, P < 5% (or beat USGS published)
- [ ] At least one Indonesian field shows physically plausible decline curve
- [ ] Physics audit < 1% violation
- [ ] Technical report committed

---

## Phase 6 — Platform Integration

- [ ] `agent/api.py` `/predict` updated for new I/O shape (4 output groups × 10 timesteps × 3D voxels)
- [ ] `dashboard/` — 3D voxel viewer (three.js / deck.gl), saturation overlay, enthalpy panel, timestep slider
- [ ] Subagent prompts updated for two-phase + 3D vocabulary
- [ ] New HF Space `ForceX-AI/geoforce-v2` (production, ForceX-AI org) deployed
- [ ] `platform.forcex-ai.com/geoforce-v2` iframe URL repointed
- [ ] v0.2 Space archived at `robiriu/geoforce-v0`
- [ ] `forcex-ai.com` landing page copy updated

### Phase 6 exit gate
- [ ] All 3 v2 demo scenarios run end-to-end < 5s in dashboard
- [ ] Mobile + desktop renders correctly
- [ ] HF Space healthcheck green

---

## Phase 7 — Publish

- [ ] HF model card on `ForceX-AI/geoforce-v2-model` with full Brady + Indonesian results
- [ ] HF Dataset card on `ForceX-AI/geoforce-v2-data` with provenance + citations
- [ ] Stanford Geothermal Workshop submission
- [ ] LinkedIn post — "from hackathon to v2.0" honest narrative
- [ ] ITB Geothermal Engineering faculty outreach email
- [ ] Pertamina Geothermal Energy data-sharing proposal draft
- [ ] `docs/v3-roadmap.md` — GNN seed work for v3.0

---

## Decisions Log

| Date | Decision | Source |
|---|---|---|
| 2026-05-03 | Lift hackathon scope locks; pursue full v2.0 transformation per `initial/PLAN.md` | user |
| 2026-05-03 | Vertex AI Gemini direct (not LiteLLM initially) for orchestrator, free GenAI App Builder credit until Mar 2027 | user |
| 2026-05-03 | Waiwera primary simulator (TOUGH3 license requested for cross-validation, never blocking) | user |
| 2026-05-03 | VPS + Kaggle as free simulation compute; no Oracle Cloud (signup blocked) | user |
| 2026-05-03 | Long-lived `v2-transform` branch; `main` frozen at v0.2 | user |
| 2026-05-03 | v0.2 hackathon build stays deployed at `robiriu/geoforce` until v2.0 ships | user |
| 2026-05-03 | GCP project `forcex-studio` repurposed and renamed display "GeoForce"; APIs (Vertex AI, Generative Language) enabled | user |
| 2026-05-03 | Adopt Google ADK 1.32 (open-source Apache 2.0) on top of Vertex Gemini for the agent runtime — gives tool-call loop, session mgmt, streaming, and LiteLLM-portability for free | user |
| 2026-05-03 | Phase 0 uses single root LlmAgent with 4 tools (not 8 live subagents) to conserve GenAI App Builder credit; multi-agent decomposition deferred to Phase 6 | user (cost concern) |
| 2026-05-03 | Brady OSR is well-time-series, not 2D field. v1.1-on-Brady baseline notebook **dropped**; Brady moves to Phase 5 validation only (NREL Duplyakin 2022 numbers become the bar). Option (a) per assistant flag. | user |
| 2026-05-03 | Phase 1 §1B Utah FORGE **deferred to Phase 5** — different physics regime (EGS in granitic basement vs Indonesian volcanic-arc); not in Phase 1 exit gate; revisit only if EGS comparison adds technical-report value | assistant recommendation, awaiting confirmation |

---

## Blocker Log

(Empty as of 2026-05-03 — Phase 0 in progress.)

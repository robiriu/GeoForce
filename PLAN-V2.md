# GeoForce v2.0 — Execution Plan

**Status:** Draft, awaiting approval
**Created:** 2026-05-03
**Supersedes:** `initial/PLAN.md` (kept as the source aspirational doc; this is the operational plan)

This plan turns `initial/PLAN.md` from aspiration into execution under real free-tier compute and a solo developer workflow.

---

## 0. Locked decisions (set, not up for re-debate)

| Topic | Decision |
|---|---|
| Hackathon scope locks (single-phase only, no simulators, never retrain CNN) | **Lifted** |
| Orchestrator LLM | **Vertex AI Gemini** (GenAI App Builder credit, ~Rp 16.8M, expires Mar 2027) |
| LLM SDK | **Vertex AI SDK direct** initially; LiteLLM swap if/when credit runs low |
| Simulator (primary) | **Waiwera** (open-source, no license wait); TOUGH3 license requested in parallel for credibility, not for blocking work |
| Simulation compute (24/7 worker) | **Existing VPS** (`platform.forcex-ai.com` host) — niced background process |
| Simulation compute (burst parallelism) | **Kaggle saved sessions** — up to 5 concurrent, 12 hr each |
| Simulation compute (backup bursts) | **GitHub Actions** matrix builds, 6hr/job, 20 concurrent |
| Training compute | **Kaggle T4/P100 free GPU** (30 hr/week) |
| Dataset storage | **HuggingFace Datasets** (free, public) |
| Inference serving | **HuggingFace Spaces** (existing) |
| Repo strategy | **Long-lived `v2-transform` branch** off main; `main` stays frozen at v0.2 |
| v0.2 hackathon build | Stays deployed on HF + `platform.forcex-ai.com/geoforce-v2` until v2.0 ships |
| Multi-agent orchestration pattern | **Kept** (8 subagents, skills, slash commands) — ported to Vertex/Gemini |

---

## 1. Success criteria for v2.0 (from `initial/PLAN.md`, unchanged)

| Metric | Target | Validation source |
|---|---|---|
| Temperature RMSE | < 5 °C | Brady held-out set + Indonesian qualitative |
| Pressure RMSE | < 0.5 MPa | Brady held-out set |
| Steam saturation RMSE | < 0.1 | TOUGH3/Waiwera held-out |
| R² (all variables) | > 0.95 | Brady held-out |
| Inference time (single scenario) | < 1 s | HF Space measured |
| Mass + energy conservation violation | < 1% | Physics loss audit |
| Two-phase support | Yes | Vapor-dominated test scenario green |
| 3D | Yes | Gravity segregation captured |
| Brady benchmark match | T < 4%, P < 5% | NREL OSR held-out |

A run that fails any of these is not v2.0 — it's a v1.x revision.

---

## 2. Phases — gates, deliverables, compute, risks

Phases are gated, not time-boxed. Each phase has an **entry condition**, a **deliverables list**, and a hard **exit gate**. No phase begins until the prior phase's exit gate is green.

### Phase 0 — Foundation

**Goal:** prepare the codebase, infra, and accounts to execute the rest of the plan without further setup friction.

**Entry condition:** plan approved.

**Deliverables:**
1. Branch `v2-transform` created off `main`, pushed to `robiriu/GeoForce`.
2. `CLAUDE.md` and `AGENTS.md` updated — scope locks removed, v2.0 success criteria pasted as the new constitution.
3. Root `PROGRESS.md` rewritten — v0.2 hackathon record archived to `archive/PROGRESS-v0.2.md`; new `PROGRESS.md` mirrors this plan's phase structure.
4. Root `JOURNAL.md` continued with 2026-05-03 entry: scope re-expansion decision, locked decisions list.
5. `agent/runtime.py` migrated from `claude_agent_sdk.ClaudeSDKClient` → `google.cloud.aiplatform` Vertex Gemini client. Tool calling reimplemented using Gemini's `FunctionDeclaration` schema. SSE event format preserved so the dashboard does not need to change.
6. `agent/api.py` adapted: `/sessions` and `/query` work identically to v0.2 from the dashboard's POV; only the backend LLM differs.
7. `.env` template updated: `GOOGLE_APPLICATION_CREDENTIALS` (service account JSON path), `GCP_PROJECT=forcex-studio`, `GCP_LOCATION=asia-southeast1`, `GEMINI_MODEL=gemini-2.0-flash-001` (exact model ID confirmed against Vertex catalog at runtime).
8. Vertex service account created on `forcex-studio` with `roles/aiplatform.user`, key downloaded, gitignored.
9. Kaggle account API token (`~/.kaggle/kaggle.json`) configured on dev box for notebook automation.
10. HuggingFace Dataset repo `ForceX-AI/geoforce-v2-data` created (empty, public) under the ForceX-AI org, with placeholder README.
11. v2-transform `dashboard/` rebuilt and deployed to a separate HF Space `ForceX-AI/geoforce-v2-dev` (so v0.2 stays at `robiriu/geoforce`).

**Exit gate:**
- `agent/api.py` running locally answers a multi-turn query end-to-end via Vertex Gemini, with a single `predict_solver` tool call dispatched correctly. Tool argument schema validated (no schema drift). SSE stream parses cleanly in the dashboard.
- All eight original subagents present in `.claude/agents/` and the loader successfully forwards them to Gemini system prompts.
- `gemini-2.0-flash-001` quota check: ≥ 1000 RPD remaining on the project.

**Compute home:** dev box (this VPS), Vertex AI for orchestrator inference.

**Risks:**
- Vertex Gemini's function-calling JSON differs from Claude's; tool responses may need re-shaping for `predict_solver`/`predict_surrogate` outputs. **Mitigation:** Pydantic schema validation + retry-on-malformed in the runtime.
- The dashboard expects Claude-style `text_delta` SSE events. **Mitigation:** translate Gemini's `candidates[].content.parts[].text` into the same event shape inside `agent/api.py` — frontend untouched.

---

### Phase 1 — Real Data Foundation

**Goal:** ingest NREL Brady OSR + Utah FORGE + published Indonesian field parameters into a usable training-data scaffold.

**Entry condition:** Phase 0 exit gate green.

**Deliverables:**
1. `data/brady/` — cloned `NREL/geothermal_osr` (BSD-3, gitignored). `data/brady/loader.py` parses 102 .xlsx scenarios into `BradyScenario` dataclasses + `stack()` for batched (N, 241, k) tensors. **Note:** Brady is a well-time-series dataset (4 injectors + 6 producers × mass flow / BHP / BHT × 241 monthly steps), not a 2D field dataset.
2. `data/forge/` — Utah FORGE well-log + 3D geological model downloads, parsed into PyTOUGH-compatible structures via `data/forge/loader.py`.
3. `data/indonesia/parameters.yaml` — published parameter ranges for Kamojang, Darajat, Wayang Windu, Salak, Lahendong, Ulubelu, Karaha-Talaga Bodas. Each entry cites the paper.
4. `data/README.md` — provenance, license, citation for every dataset.
5. `data/indonesia/README.md` — list of papers, what was extracted, what remains unknown.
6. `tests/test_brady_loader.py` — Phase 1 exit-gate check.

**Dropped (was deliverable 4–5 in v0 of this plan):** `notebooks/01-brady-explore.ipynb` and `notebooks/02-brady-v1-cnn-baseline.ipynb`. The v1.1 CNN produces a 32×32 spatial T/P field; Brady provides per-well time series. A meaningful v1.1-on-Brady error number would require a fabricated adapter that the eventual 3D U-Net does not need. Brady becomes a Phase-5-only validation target instead. Decision logged in PROGRESS.md.

**Exit gate:**
- Brady loader returns ≥ 95 of 101 scenarios without parse errors. ✓ (101/101 parse, 100 stack at standard length)
- Indonesian parameters table covers ≥ 5 of 7 fields with permeability range, porosity, base T/P, dominant phase.

**Compute home:** dev VPS (data ingestion is I/O bound, no GPU needed).

**Risks:**
- Brady OSR format may not match what its README implies; could need ad-hoc parsing. **Mitigation:** budget time for parser surprises; lean on PyTOUGH's existing readers where possible.
- Indonesian field papers may be paywalled or behind ITB credentials. **Mitigation:** Stanford Geothermal Workshop archive is open; start there. Pertamina annual reports also have aggregate parameters.

---

### Phase 2 — Simulator Setup + Pilot Campaign

**Goal:** install Waiwera on VPS + Kaggle, run a 100-scenario pilot batch, validate the full sim → training-data pipeline before committing to 1,000.

**Entry condition:** Phase 1 exit gate green.

**Deliverables:**
1. **Waiwera install on VPS** — built from source, runs TOUGH2 reference benchmark `RFP` (Radial Flow Problem) and matches published solution within 1%.
2. **Waiwera install on Kaggle** — Dockerfile or conda env that builds Waiwera inside a Kaggle notebook session in < 30 min.
3. **PyTOUGH installed** on both — for input deck templating and output reading.
4. `simulation/campaign.py` — generates input decks from `scenarios.yaml v2`, runs Waiwera, parses outputs into `(inputs, outputs)` HDF5 chunks.
5. `simulation/scenarios_v2.yaml` — LHS-sampled parameter combinations covering the 12 dimensions in `initial/PLAN.md` §2B.
6. `simulation/grid.py` — 32×32×10 3D grid with caprock/reservoir/basement layering, hydrostatic + geothermal initial conditions.
7. `simulation/wells.py` — randomized well placement with N_prod ∈ [1, 8], N_inj ∈ [0, 4].
8. **VPS background worker** — systemd unit `geoforce-sim-worker.service`, niced, cgroup-limited to 50% CPU so it doesn't degrade `platform.forcex-ai.com`. Pulls jobs from a SQLite job queue at `/home/ubuntu/GeoForce/simulation/queue.db`.
9. **Kaggle burst notebook** — `notebooks/03-kaggle-sim-burst.ipynb`, parameterized by job-range, designed for the 12hr Kaggle session limit. Pushes outputs to HF Dataset on completion.
10. **100-scenario pilot batch** — uploaded to `ForceX-AI/geoforce-v2-data` on HF.
11. `notebooks/04-pilot-batch-audit.ipynb` — sanity audit: mass conservation, energy conservation, no NaNs, T bounded by [T_inj, T_max + 20°C], P within reasonable range. Reports % of pilot batch that passes audit.

**Exit gate:**
- Waiwera RFP benchmark on VPS passes (< 1% error vs. analytical).
- Pilot batch audit: ≥ 90 of 100 scenarios pass all sanity checks.
- Per-scenario wall-clock timing measured on both VPS and Kaggle. Total cost projection for 1,000 scenarios estimated.

**Compute home:** VPS (continuous worker) + Kaggle (5 parallel burst sessions).

**Risks:**
- Waiwera build fails on VPS due to PETSc/MPI dependency hell. **Mitigation:** fall back to a Docker image; both PyTOUGH and Waiwera have community Dockerfiles.
- Kaggle's 12hr session is too short for some scenarios. **Mitigation:** chunk by scenario count, not time; checkpoint output per scenario.
- VPS worker degrades `platform.forcex-ai.com`. **Mitigation:** cgroup CPU/memory limits; scheduled to run only off-peak (cron + systemd timer).

---

### Phase 3 — Full Simulation Campaign

**Goal:** complete 1,000 scenarios. Or scale back to 500 with documented justification.

**Entry condition:** Phase 2 exit gate green AND pilot timing data shows 1,000 is feasible on free compute.

**Deliverables:**
1. 1,000 scenarios uploaded to `ForceX-AI/geoforce-v2-data`, split into `train/` (800), `val/` (100), `test/` (100).
2. `data/scenarios_manifest.json` — stratified split metadata, hash of each scenario's inputs.
3. `notebooks/05-campaign-progress.ipynb` — auto-updating Kaggle dashboard for queue progress.
4. `simulation/audit.py` — re-run on full campaign; reject failed scenarios into `data/rejected/` with reason logged.

**Exit gate:**
- ≥ 900 valid scenarios in `train + val + test`.
- All scenarios pass audit.
- Stratified split confirms parameter coverage (LHS plot per dimension).

**Compute home:** VPS + Kaggle (continuous + burst).

**Risks:**
- Kaggle account flagged for "unusual activity" if too many notebooks run concurrently. **Mitigation:** stay under 5 concurrent saved sessions, throttle burst rate.
- VPS worker accumulates errors over weeks. **Mitigation:** systemd auto-restart, structured logging, `notebooks/05` shows queue health.

---

### Phase 4 — 3D U-Net Architecture and Training

**Goal:** train a 3D U-Net on the campaign data that meets §1 success criteria on the held-out test set.

**Entry condition:** Phase 3 exit gate green.

**Deliverables:**
1. `model/unet3d.py` — architecture per `initial/PLAN.md` §3A: encoder-bottleneck-decoder with skip connections, 11 input channels, 40 output channels, ~500K–2M parameters.
2. `model/preprocessing.py` — input normalization per `initial/PLAN.md` §3B; output denormalization per §3C.
3. `model/physics_loss.py` — mass conservation, energy conservation, saturation constraint (Sl + Sg = 1 hard via sigmoid), gravity term in pressure gradient. Each term toggleable.
4. `model/train.py` — Kaggle T4 training script. Mixed-precision. Checkpointing. Logs to W&B (free academic tier) or TensorBoard.
5. `notebooks/06-unet3d-train.ipynb` — Kaggle T4 training notebook.
6. `notebooks/07-unet3d-eval.ipynb` — eval on held-out test set, produces metrics table.
7. `model/weights/geoforce_v2.pt` — final weights, uploaded to `ForceX-AI/geoforce-v2-model` on HF.

**Exit gate:**
- All success criteria from §1 met on held-out test set.
- Physics violation rate < 1% on held-out test set.

**Compute home:** Kaggle T4/P100 (training); dev VPS (eval).

**Risks:**
- 3D U-Net too large for Kaggle T4 16GB VRAM. **Mitigation:** start at 32×32×8 grid; gradient checkpointing; mixed precision; reduce batch size before reducing model.
- Physics loss destabilizes training. **Mitigation:** physics loss weights start at 0, ramp up via curriculum after data loss converges.
- Training time exceeds Kaggle weekly quota. **Mitigation:** checkpoint frequently; resume across multiple weekly windows. Worst case: rent one cheap GPU hour from Lambda Labs (~$1).

---

### Phase 5 — Validation

**Goal:** prove v2.0 works against published external benchmarks, not just our held-out set.

**Entry condition:** Phase 4 exit gate green.

**Deliverables:**
1. **Brady benchmark** (`notebooks/08-brady-benchmark.ipynb`):
   - Train v2.0 on Brady OSR train split.
   - Eval on Brady held-out.
   - Compare T, P, energy errors vs USGS published numbers (T < 3.68%, P < 4.75%, energy < 4.04%).
2. **Indonesian qualitative validation** (`notebooks/09-indonesia-qualitative.ipynb`):
   - Build scenarios from `data/indonesia/parameters.yaml` for Kamojang, Darajat, Wayang Windu, Salak.
   - Run v2.0 predictions.
   - Compare production decline curves to published Pertamina/Star Energy data (qualitative, not RMSE).
3. **Physics audit** (`notebooks/10-physics-audit.ipynb`):
   - For 100 random test scenarios, compute mass + energy balance violation per timestep.
   - Steam table consistency: h(T,P) vs IAPWS-IF97 lookup.
   - Reports % violation, worst case scenarios.
4. **Technical report** (`docs/technical-report-v2.md`):
   - TOUGH/Waiwera-trained data vs analytical (v1.1).
   - Two-phase results vs single-phase (v1.1).
   - 3D vs 2D (v1.1).
   - Brady benchmark comparison.
   - Indonesian qualitative results.
   - Honest limitations list.

**Exit gate:**
- Brady benchmark: meet or beat USGS published numbers.
- Indonesian qualitative: at least one Indonesian field shows physically plausible production decline.
- Physics audit: < 1% violation rate.
- Technical report committed and pushed.

**Compute home:** Kaggle (notebooks 08, 09); dev VPS (notebook 10, doc writing).

**Risks:**
- Brady benchmark fails — model overfit to our synthetic Waiwera data. **Mitigation:** if so, retrain on Brady-only, see how that performs; document the gap.
- No Indonesian field data publicly detailed enough. **Mitigation:** qualitative comparison only, no RMSE claim.

---

### Phase 6 — Platform Integration

**Goal:** replace v0.2 dual-engine build at `platform.forcex-ai.com/geoforce-v2` with v2.0.

**Entry condition:** Phase 5 exit gate green.

**Deliverables:**
1. `agent/api.py` — `/predict` route updated for new I/O shape (4 output groups × 10 timesteps × 32×32×10 voxels).
2. `dashboard/` — new components: 3D voxel viewer (three.js or deck.gl); saturation field overlay; enthalpy panel; timestep slider.
3. `agent/runtime.py` subagent prompts updated — they now reference two-phase concepts and 3D coordinates.
4. New HF Space `ForceX-AI/geoforce-v2` (production, under ForceX-AI org), serving v2.0 model.
5. `platform.forcex-ai.com/geoforce-v2` iframe URL repointed to new Space.
6. v0.2 build archived to HF Space `robiriu/geoforce-v0`.
7. Landing-page copy on `forcex-ai.com` updated to reflect v2.0 capabilities.

**Exit gate:**
- All three scenarios from `demo/scenarios.yaml` (now v2 versions: vapor-dominated, liquid-dominated, mixed) run end-to-end through chat → tool call → 3D render in < 5s.
- Mobile + desktop dashboard renders correctly.
- HF Space healthcheck green.

**Compute home:** dev VPS (build), HF Spaces (deploy), Vertex (orchestrator inference).

**Risks:**
- 3D voxel viewer bundle size exceeds dashboard budget. **Mitigation:** lazy-load three.js; canvas-only fallback for small screens.
- HF Space 16GB CPU plan can't load v2.0 weights + run inference. **Mitigation:** quantize model to int8 for inference; benchmark before commit.

---

### Phase 7 — Publish

**Goal:** position v2.0 publicly and academically.

**Entry condition:** Phase 6 exit gate green.

**Deliverables:**
1. HuggingFace model card on `ForceX-AI/geoforce-v2-model` — full Brady benchmark numbers, Indonesian qualitative, limitations.
2. HuggingFace Dataset card on `ForceX-AI/geoforce-v2-data` — provenance, citations, license.
3. Stanford Geothermal Workshop submission (next deadline TBD; archive at https://pangea.stanford.edu/ERE/db/GeoConf/).
4. LinkedIn post — honest "from hackathon to v2.0" narrative, with public links.
5. ITB Geothermal Engineering faculty outreach email — request review, offer to demo.
6. Pertamina Geothermal Energy data-sharing proposal draft.
7. v3.0 GNN seed work documented as `docs/v3-roadmap.md` (fracture network, Voronoi grid, SeqSage).

**Exit gate:** all deliverables shipped.

**Compute home:** none (writing + outreach).

**Risks:** none technical.

---

## 3. Compute budget reconciliation

| Resource | Source | Approximate budget | Used by |
|---|---|---|---|
| Vertex Gemini Flash inference | GenAI App Builder credit (Rp 16.8M, exp Mar 2027) | ~3.5B input tokens / ~30M output tokens | Phase 0 onward, orchestrator + subagents |
| Free Trial general (Rp 2.97M, exp May 11 2026) | GCP general | Save for emergency or one-off Vertex Workbench burst | Optional Phase 4 GPU burst if Kaggle is exhausted |
| VPS continuous compute | Already paid | 50% CPU budget, 24/7 | Phases 2, 3 (sim worker) |
| Kaggle notebook hours | Free, 30 hr/wk | ≥ 5 concurrent saved sessions | Phases 2, 3 (sim burst), Phase 4 (training) |
| GitHub Actions minutes | Free, 2000/mo private (unlimited public) | Backup matrix bursts | Phase 3 fallback |
| HF Datasets storage | Free, public | unlimited | Phase 1 onward |
| HF Spaces hosting | Free CPU Basic | 2 vCPU 16GB always-on | Phase 6 deploy |

No paid services required. If a phase blows its compute budget, it gets re-scoped, not cash-injected.

---

## 4. Risk register (project-level, beyond per-phase)

| Risk | Impact | Mitigation |
|---|---|---|
| Vertex GenAI credit insufficient for full project lifecycle | Orchestrator goes silent | LiteLLM swap to OpenRouter free tier (DeepSeek V3, Llama 3.3 70B); pre-tested in Phase 0 stretch |
| Kaggle account flagged | Lose burst compute | VPS continuous + GH Actions matrix as backup; spread load across multiple weeks |
| Waiwera proves too slow on free compute | Campaign stalls at 200/1000 | Reduce to 500 scenarios; document as "v2.0 lite"; v2.1 completes the rest |
| 3D U-Net cannot meet §1 criteria | v2.0 misses target | Reduce grid to 24×24×8; OR ensemble v1.1 CNN + 3D coarse correction; OR document as "v2.0 partial — 3D pressure only, T stays 2D" |
| HF Space cannot host v2.0 inference | No public demo | Inference moves to Vertex serverless container (uses GenAI credit) |
| Solo developer bandwidth | Phases drag | Phase ordering allows parallelism: while Phase 3 campaign runs in background, Phase 4 architecture can be drafted |

---

## 5. What is **not** in this plan

- v3.0 GNN for fracture networks — `initial/PLAN.md` Phase 6 future work, ticketed but not executed in v2.0 scope.
- TOUGH3 simulator — license requested for credibility, but Waiwera is the executing simulator. If TOUGH3 license arrives mid-Phase-3 and runs without disruption, we cross-validate; we do not retrain.
- Live coupling to Pertamina production telemetry — out of scope without data-sharing agreement.
- Mobile-app version — dashboard stays web.
- Multi-language support — English only.

---

## 6. Definition of done for v2.0

The v2.0 release ships when:
- All success criteria in §1 are met on held-out test set.
- Brady benchmark meets or beats USGS published numbers.
- v2.0 is live at `platform.forcex-ai.com/geoforce-v2` replacing v0.2.
- Technical report is published.
- v0.2 is archived (not deleted) for historical reference.
- LinkedIn announcement is posted.

Anything short of this is a v1.x revision, not v2.0.

---

## 7. Approval

Sign-off needed from project owner (Robi) before Phase 0 begins.

- [ ] Locked decisions (§0) acknowledged
- [ ] Success criteria (§1) acknowledged
- [ ] Compute budget (§3) acknowledged
- [ ] Risks (§4) acknowledged
- [ ] Approved to begin Phase 0

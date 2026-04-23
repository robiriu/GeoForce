# GeoForce — Claude Code Opus 4.7 Hackathon Plan

**Deadline:** 2 days from 2026-04-23
**Author:** Robi Dany Riupassa (built with Claude Code Opus 4.7)
**Repo:** https://github.com/robiriu/GeoForce-CCHackathon

---

## 1. Reality Check

The v2-real-transform plan (`/initial/PLAN.md`) is a **12-week program**: TOUGH3 licensing, 1000+ 3D multiphase simulations (~20–40 VPS days), 3D U-Net training, Brady benchmark. **None of that fits in 2 days.** Pretending otherwise guarantees failure.

What *is* true and usable *today*:

- **v1.1 CNN surrogate is already trained, validated, and deployed** (R²_T 0.994, R²_P 0.997, inference 3.2 ms, speedup 282,350×)
- **248 KB of weights** + 1,000 training scenarios exist in `ForceX-AI/products/...`
- **9 real engineering questions** are already written down in `initial/REAL-ENGINEERING-QUESTIONS.md`
- The hackathon is about **Claude Code Opus 4.7** — judges reward *what an Opus 4.7 agent can build*, not v2 physics realism

## 2. Hackathon Thesis (the pitch in one sentence)

> **GeoForce Agent** — a Claude Opus 4.7 agent that answers real geothermal engineering questions by driving a deployed physics-informed CNN surrogate, with uncertainty quantification via Monte Carlo ensembles — built end-to-end in 2 days with Claude Code.

Why this wins:
- Showcases **Opus 4.7 tool use + agentic reasoning** (the hackathon's point)
- Uses a **real ML artifact** (v1.1, already validated — no training risk in 2 days)
- Produces a **visible, live demo** (NL query → uncertainty-quantified answer + 2D field plots)
- Honest about limitations (single-phase, 2D) — matches v1.1's real scope

## 3. Scope — In / Out

### IN (must ship)

1. **Port v1.1 inference** into this repo (model weights + `ReservoirCNN` class + normalization constants — no retraining)
2. **Tool layer** — 4 tools callable by the agent:
   - `predict(scenario)` → single deterministic T/P field
   - `monte_carlo(base_scenario, param_distributions, n)` → P10/P50/P90 envelopes
   - `sensitivity(base_scenario, perturb_pct)` → per-parameter impact ranking
   - `visualize(field, kind)` → matplotlib PNG of T or P field
3. **Agent** — built on the `claude-agent-sdk` (Python) using `claude-opus-4-6` or the current Opus 4.7 model ID, with a system prompt that makes it a geothermal reservoir advisor
4. **Answer 3 of the 9 real questions** (exploration phase, Q1–Q3):
   - Q1: "If I drill at (x, y), what temperature will I hit?"
   - Q2: "How many MW can this reservoir sustain for 20 years?"
   - Q3: "Where should I place the next 3 production wells?"
5. **Demo UI** — Streamlit single-page app (fastest to build, runs locally)
6. **README + 90-second demo video** (screen recording with voiceover)
7. **Push everything to `GeoForce-CCHackathon` repo** + tag `v0.1-hackathon`

### OUT (explicitly cut)

- Any TOUGH3/Waiwera installation or 3D simulation work (v2 territory)
- Retraining the CNN, even on Brady data
- 3D visualization (three.js / deck.gl)
- PostgreSQL integration
- Authentication, multi-tenant, billing
- HuggingFace publication (nice-to-have, only if Day 2 afternoon runs clean)
- Q4–Q9 (production-phase questions — require state tracking we don't have)
- Writing a paper

## 4. Technical Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Streamlit UI  (/app/app.py)                                  │
│  - Text box: natural-language query                           │
│  - Panel: agent reasoning trace                               │
│  - Panel: T/P field plots + P10/P50/P90 bands                 │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  Claude Opus 4.7 Agent  (/agent/geoforce_agent.py)            │
│  - claude-agent-sdk, ClaudeAgentOptions                       │
│  - System prompt: geothermal reservoir advisor                │
│  - Tool-use loop until answer is complete                     │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  Tool Layer  (/tools/*.py)                                    │
│  - predict        : single deterministic run                  │
│  - monte_carlo    : ensemble → P10/P50/P90                    │
│  - sensitivity    : one-at-a-time perturbation                │
│  - visualize      : matplotlib → PNG bytes                    │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  Model Core  (/model/reservoir_cnn.py + weights/*.pt)         │
│  - ReservoirCNN (6-in → 10-out, 57,802 params)                │
│  - load_v1_1() loads geoforce_cnn_v1.1.pt                     │
│  - build_input(scenario) — 6-channel encoding                 │
│  - decode_output(tensor) — de-normalize to °C / Pa            │
└──────────────────────────────────────────────────────────────┘
```

### Proposed directory layout

```
GeoForce-CCHackathon/
├── HACKATHON-PLAN.md          (this file)
├── README.md                  (Day 2 write-up)
├── pyproject.toml             (deps: torch, numpy, claude-agent-sdk, streamlit, matplotlib)
├── .env.example               (ANTHROPIC_API_KEY)
├── initial/                   (seed docs — untouched)
├── model/
│   ├── reservoir_cnn.py       (ported from ForceX-AI/mvp/geoforce/models/)
│   ├── encoding.py            (6-channel builder + de-normalizer)
│   └── weights/
│       └── geoforce_cnn_v1.1.pt   (copied from ForceX-AI/products/model_registry/)
├── tools/
│   ├── predict.py
│   ├── monte_carlo.py
│   ├── sensitivity.py
│   └── visualize.py
├── agent/
│   ├── geoforce_agent.py      (system prompt + tool registration)
│   └── prompts.py
├── app/
│   └── app.py                 (Streamlit entry point)
├── tests/
│   └── test_smoke.py          (load model, run 1 prediction, assert shape)
└── demo/
    ├── scenarios.yaml         (3 demo scenarios for Q1–Q3)
    └── video.mp4              (90s recording — Day 2)
```

## 5. Two-Day Schedule

### Day 1 — Build the engine (target: end of day, agent can answer Q1)

**Morning — 3h**
- [ ] Copy `geoforce_cnn_v1.1.pt` + `ReservoirCNN` class + normalization constants into `/model/`
- [ ] Write `model/encoding.py` with the exact 6-channel encoding from v1.1
- [ ] `tests/test_smoke.py` — load model, predict on a toy scenario, assert output shape `(10, 32, 32)` and T range `[25, 350]`
- [ ] `pyproject.toml` with pinned versions; `pip install -e .` clean on a fresh venv

**Afternoon — 4h**
- [ ] `tools/predict.py` — wraps `ReservoirCNN.forward()` with a clean `predict(scenario_dict) → {T: (5,32,32), P: (5,32,32), t_ms}`
- [ ] `tools/monte_carlo.py` — accept base scenario + per-param distributions (uniform, truncnorm, lognormal), run N forward passes, return P10/P50/P90 per cell/timestep
- [ ] `tools/sensitivity.py` — one-at-a-time ±20% perturbation, rank params by ΔT_mean
- [ ] `tools/visualize.py` — 2D heatmap at final timestep, optional uncertainty band

**Evening — 2h**
- [ ] `agent/geoforce_agent.py` — `claude-agent-sdk` client, register 4 tools, system prompt
- [ ] Smoke test from CLI: `python -m agent.geoforce_agent "What temperature would I hit drilling at cell (16,16) with log_k=-14?"`
- [ ] Commit + push — milestone: **agent answers Q1 in terminal**

### Day 2 — Polish + demo + ship

**Morning — 3h**
- [ ] Streamlit `app/app.py` — input box, reasoning trace panel, plot panel
- [ ] Hard-code 3 demo scenarios in `demo/scenarios.yaml` (a drilling-target query, a 20-yr sustainability query, a well-placement query)
- [ ] Dry-run each through the agent — tune system prompt until answers are crisp
- [ ] Fix any tool-use issues (parameter schemas, output formatting)

**Afternoon — 3h**
- [ ] Write `README.md`: problem, architecture, run instructions, example queries, **honest limitations section** (single-phase, 2D, synthetic training data)
- [ ] Record 90-second demo video (OBS or Loom): query → agent thinks → MC envelope appears
- [ ] Tag `v0.1-hackathon`, push, update repo description
- [ ] **Stop here if behind schedule**

**Evening — 2h (only if on schedule)**
- [ ] Deploy Streamlit to HuggingFace Spaces (free) OR Fly.io
- [ ] Post submission link

### Buffer
If any step slips by >1h, cut the next *optional* thing in this order: HF deploy → 3rd demo scenario (Q3) → sensitivity tool (keep only predict + MC).

## 6. Deliverables Checklist

- [ ] Agent answers Q1, Q2, Q3 from real user queries
- [ ] Monte Carlo UQ produces P10/P50/P90 for at least one query
- [ ] Streamlit app runs locally with `streamlit run app/app.py`
- [ ] Demo video ≤ 90s
- [ ] README with honest limitations
- [ ] Git tag `v0.1-hackathon`
- [ ] Tests pass (`pytest tests/`)

## 7. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| v1.1 weights don't load (path / PyTorch version skew) | Medium | Day 1 morning is load-smoke-test; if broken, regenerate from training state_dict format we can read |
| `claude-agent-sdk` tool-use loop flakes on complex queries | Medium | Keep tool schemas tiny, 2–3 params max; prompt constrains agent to call ≤3 tools per turn |
| Streamlit async + sync SDK mismatch | Low | Run agent synchronously in Streamlit callback; stream reasoning via `st.write_stream` |
| MC ensemble too slow (1000 runs × 3 ms ≈ 3 s) | Very Low | 3 ms inference × 1000 = 3s — fine for a demo |
| Day 2 compresses into 1 day | Medium | Cut list in §5 buffer; HF deploy and 3rd scenario are the safe valves |
| ANTHROPIC_API_KEY quota during demo recording | Low | Record before deploying publicly; use local Claude Code session if needed |

## 8. Memory / Context Handoff

After this plan is approved, I'll maintain a `PROGRESS.md` at repo root with checkbox state, updated at end of each work block. Session memory (via the auto-memory system) will hold the "GeoForce" alias and the hackathon milestone.

## 9. What I Need From You Before Starting

1. **Approve or edit this scope** — especially §3 (in/out) and the 3 chosen questions
2. **ANTHROPIC_API_KEY** — needs to be available in the environment (or confirm the local Claude Code session is acceptable as the agent)
3. **Preferred demo framing** — Indonesian field (Kamojang/Darajat) or a generic synthetic field? (Kamojang is more on-brand; synthetic avoids over-claiming)
4. **Python env** — use the system Python / an existing venv / fresh `.venv` here?

---

**Stop point:** nothing below touches code yet. Awaiting your review.

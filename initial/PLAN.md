# GeoForce v2.0 — Transformation to Real Engineering Tool

**Status:** Planning
**Start Date:** TBD
**Target:** A geothermal reservoir prediction model that can answer real engineering questions for Indonesian fields (Kamojang, Darajat, Wayang Windu, Lahendong, Salak).

---

## Why v1.1 Cannot Handle Real Cases

GeoForce v1.1 is a validated proof-of-concept. It proves the pipeline works (data -> train -> validate -> serve -> platform). But it solves only one simplified scenario class:

| Aspect | v1.1 (Current) | Reality |
|--------|----------------|---------|
| Physics | Single-phase liquid water, constant properties | Two-phase steam-water, IAPWS-IF97 steam tables, phase transitions |
| Grid | 2D (32x32 = 1,024 cells) | 3D (50x50x20 = 50,000+ cells minimum) |
| Permeability | One scalar per scenario | Spatially varying field with fracture networks |
| Training data | Our own analytical heat+Darcy solver | TOUGH2/TOUGH3 multiphase simulation outputs |
| Outputs | Normalized T and P | T, P, steam saturation, enthalpy, steam fraction |
| Inputs | 6 parameters | 10+ parameters + porosity fields, fault maps, well trajectories |
| Temporal | 5 timesteps (4-year intervals) | Flexible timesteps, production schedule-dependent |
| Validation | Against own synthetic simulations | Against published field data + USGS Brady benchmark |

### Three Fatal Gaps

1. **No phase physics.** Kamojang and Darajat are vapor-dominated — the reservoir is steam, not liquid water. GeoForce v1.1 has no concept of boiling, condensation, or steam fraction. It literally cannot represent these fields.

2. **2D only.** Steam rises, liquid sinks. Gravity segregation drives reservoir behavior in all real geothermal systems. A 2D horizontal slice misses this entirely.

3. **Training data is wrong.** Our finite-difference solver approximates heat conduction + Darcy flow with constant fluid properties. Real reservoirs need multiphase flow with pressure-dependent density, viscosity, and enthalpy from steam tables.

---

## The Transformation Plan

### Phase 1: Real Data Foundation (Weeks 1-2)

**Goal:** Get real simulation data and prove we can learn from it.

#### 1A. Download NREL Brady Hot Springs Dataset

The USGS/NREL published the Open Source Reservoir (OSR) — 101 CMG STARS simulation scenarios for a Brady-like geothermal field. This is the gold standard ML benchmark in geothermal.

- **Source:** https://github.com/NREL/geothermal_osr
- **Also at:** https://gdr.openei.org/submissions/1346
- **Contents:** 101 scenarios, T/P/enthalpy at wells, 2020-2040 production forecasts
- **Format:** Jupyter notebooks + CSV/HDF5
- **License:** Open (DOE-funded)
- **Published benchmark:** <3.68% temperature error, <4.75% pressure error

Tasks:
- [ ] Clone NREL/geothermal_osr repository
- [ ] Explore data format, understand scenario structure
- [ ] Retrain current CNN architecture on Brady data (quick validation)
- [ ] Compare our results against published USGS benchmark
- [ ] Document gaps between Brady data structure and our training pipeline

#### 1B. Download Utah FORGE Dataset

FORGE (Frontier Observatory for Research in Geothermal Energy) is the DOE's flagship geothermal research site in Milford, Utah. It has the most comprehensive open geothermal dataset in the world.

- **Source:** https://gdr.openei.org/forge and https://utahforge.com/project-data-dashboard/
- **Contents:** Well logs, T/P profiles, microseismicity, stress data, 3D geological model, stimulation data
- **Use for:** Understanding real input data formats, building realistic input channel design

Tasks:
- [ ] Download FORGE well log data (temperature, pressure, lithology)
- [ ] Download 3D geological model
- [ ] Map FORGE data structure to GeoForce input requirements
- [ ] Identify which data types are available for Indonesian fields

#### 1C. Collect Published Indonesian Field Parameters

Indonesian field data is not publicly available in raw form, but published papers contain enough parameters to build realistic simulation campaigns.

Sources:
- Stanford Geothermal Workshop papers (https://pangea.stanford.edu/ERE/db/GeoConf/)
- World Geothermal Congress proceedings
- ITB thesis repository
- Pertamina and Star Energy technical publications

Key fields to collect parameters for:

| Field | Operator | Type | Published Temp | Published Pressure | Capacity |
|-------|----------|------|---------------|-------------------|----------|
| Kamojang | PGE | Vapor-dominated | ~245 C | ~35 bar | 375 MW |
| Darajat | Star Energy | Vapor-dominated | ~250 C | ~30 bar | 260 MW |
| Wayang Windu | Star Energy | Liquid + vapor caps | ~270 C | Variable | 227 MW |
| Salak | Star Energy | Liquid-dominated | ~240 C | Variable | 377 MW |
| Lahendong | PGE | High-T liquid | ~300 C | Variable | 120 MW |
| Ulubelu | PGE | Liquid-dominated | ~280 C | Variable | 220 MW |
| Karaha-Talaga Bodas | PGE | Mixed | ~350 C | Variable | 30 MW |

Tasks:
- [ ] Compile parameter table from published Stanford/WGC papers
- [ ] Document permeability ranges for Indonesian volcanic systems
- [ ] Document fracture characteristics (orientation, density, aperture)
- [ ] Build scenarios.yaml v2 with realistic Indonesian ranges
- [ ] Identify which fields have the most published data (prioritize for validation)

---

### Phase 2: Real Simulator Setup (Weeks 2-4)

**Goal:** Generate proper multiphase simulation data for training.

#### 2A. Install Geothermal Simulator

Two options (pursue both, use whichever works first):

**Option A: TOUGH3 (industry standard)**
- Request from LBNL: https://tough.lbl.gov/software/tough3/
- Free for research use
- Requires license agreement (may take 1-2 weeks)
- Install with PyTOUGH wrapper for Python integration
- Use EOS1 module (pure water, two-phase) initially
- Later upgrade to EWASG module (water + NaCl + NCG)

**Option B: Waiwera (fully open-source)**
- Source: https://waiwera.github.io/
- Fortran 2003, parallel, no license needed
- Validated against TOUGH2 benchmark problems
- May be easier to automate for batch campaigns
- Less industry adoption than TOUGH2/3

Tasks:
- [ ] Request TOUGH3 license from LBNL
- [ ] Install Waiwera from source (backup option)
- [ ] Install PyTOUGH (Python interface to TOUGH2/3)
- [ ] Run TOUGH2 standard benchmark problems to verify installation
- [ ] Set up batch simulation runner (Python script + LHS parameter sampling)

#### 2B. Design Simulation Campaign

Build 1,000-5,000 simulation scenarios covering Indonesian geothermal parameter space.

**3D Grid Design:**
```
Initial:  32 x 32 x 10 = 10,240 cells (manageable on VPS CPU)
Target:   64 x 64 x 20 = 81,920 cells (requires TOUGH3 parallel)
Domain:   2 km x 2 km x 2 km (typical Indonesian field extent)
```

**Parameter Space (LHS sampling):**

| Parameter | Min | Max | Unit | Source |
|-----------|-----|-----|------|--------|
| Base temperature | 200 | 350 | C | Indonesian field range |
| Base pressure | 20 | 120 | bar | Hydrostatic at 500-3000m |
| Log10 permeability | -16 | -12 | log10(m2) | Volcanic rock range |
| Porosity | 0.01 | 0.15 | fraction | Andesite to fractured tuff |
| Depth | 500 | 3000 | m | Shallow to deep |
| Heat source depth | 3000 | 6000 | m | Magmatic heat source |
| Injection rate | 0 | 100 | kg/s | Per well |
| Production rate | 10 | 150 | kg/s | Per well |
| N production wells | 1 | 8 | count | Field size dependent |
| N injection wells | 0 | 4 | count | Reinjection strategy |
| Rock thermal conductivity | 1.5 | 4.0 | W/(m K) | Volcanic rock range |
| Initial steam saturation | 0.0 | 1.0 | fraction | Liquid to vapor-dominated |

**Output Variables (per cell, per timestep):**
- Temperature (C)
- Pressure (Pa)
- Steam saturation (0-1)
- Specific enthalpy (kJ/kg)
- Liquid density (kg/m3)

**Timesteps:** 10 snapshots over 30 years (years 1, 3, 5, 7, 10, 13, 16, 20, 25, 30)

Tasks:
- [ ] Write simulation campaign generator script
- [ ] Define grid with vertical layering (caprock, reservoir, basement)
- [ ] Implement well placement randomization
- [ ] Set up initial conditions (hydrostatic gradient, geothermal gradient)
- [ ] Run pilot batch (10 scenarios) to estimate per-simulation time
- [ ] Estimate total compute time for 1,000 scenarios
- [ ] Run full campaign (may need to use cloud compute for speed)

---

### Phase 3: Model Architecture Upgrade (Weeks 4-8)

**Goal:** Build a model that handles 3D, two-phase, spatially-varying inputs.

#### 3A. Architecture Selection

**v2.0 Target: 3D U-Net**

Why U-Net over current flat CNN:
- Skip connections preserve spatial detail at fine scales
- Well-proven for image-to-image prediction tasks
- Encoder-decoder structure naturally handles multi-scale features
- Can handle 3D volumes (3D convolutions)
- Moderate parameter count (500K-2M, still CPU-feasible)

```
Input: (batch, C_in, 32, 32, 10)   — 3D volume with multiple channels
       |
   [Encoder]
       Conv3D(C_in, 32) + BN + ReLU
       Conv3D(32, 32) + BN + ReLU
       MaxPool3D(2)
       Conv3D(32, 64) + BN + ReLU
       Conv3D(64, 64) + BN + ReLU
       MaxPool3D(2)
       |
   [Bottleneck]
       Conv3D(64, 128) + BN + ReLU
       Conv3D(128, 128) + BN + ReLU
       |
   [Decoder]
       Upsample3D(2) + Cat(skip)
       Conv3D(128+64, 64) + BN + ReLU
       Conv3D(64, 64) + BN + ReLU
       Upsample3D(2) + Cat(skip)
       Conv3D(64+32, 32) + BN + ReLU
       Conv3D(32, C_out, 1x1x1) + Sigmoid
       |
Output: (batch, C_out, 32, 32, 10)  — T, P, saturation, enthalpy at each timestep
```

**v3.0 Target: Graph Neural Network (GNN)**

For fracture-dominated Indonesian systems, following Gudala & Yan (2025):
- Handles unstructured/Voronoi grids natively
- Can represent discrete fracture networks (DFN)
- R-squared > 0.95 for T, P, displacement in published results
- Sequential Graph Sage (SeqSage) architecture

#### 3B. Input Channel Design

| Channel | Description | Shape | Normalization |
|---------|-------------|-------|---------------|
| 0 | Initial temperature field | (32,32,10) | (T-25)/325 |
| 1 | Log10 permeability field | (32,32,10) | (logk+16)/4 |
| 2 | Porosity field | (32,32,10) | (phi-0.01)/0.14 |
| 3 | Well mask (production) | (32,32,10) | Gaussian decay |
| 4 | Well mask (injection) | (32,32,10) | Gaussian decay |
| 5 | Initial pressure | (32,32,10) | (P-Pmin)/(Pmax-Pmin) |
| 6 | Initial steam saturation | (32,32,10) | [0,1] |
| 7 | Rock type indicator | (32,32,10) | Categorical (caprock=0, reservoir=1, basement=2) |
| 8 | Depth (z-coordinate) | (32,32,10) | (z-zmin)/(zmax-zmin) |
| 9 | Production rate schedule | (32,32,10) | Normalized rate |
| 10 | Injection rate schedule | (32,32,10) | Normalized rate |

Total: 11 input channels (vs 6 in v1.1)

#### 3C. Output Channel Design

| Channel Group | Variables | Shape | Denormalization |
|--------------|-----------|-------|-----------------|
| Temperature | T at 10 timesteps | (10, 32, 32, 10) | T * 350 C |
| Pressure | P at 10 timesteps | (10, 32, 32, 10) | P * 120 bar |
| Steam saturation | Sg at 10 timesteps | (10, 32, 32, 10) | [0, 1] |
| Enthalpy | h at 10 timesteps | (10, 32, 32, 10) | h * 3000 kJ/kg |

Total: 40 output channels (vs 10 in v1.1)

#### 3D. Physics-Informed Loss Upgrade

Current physics loss: soft temporal smoothness + Laplacian + Darcy coupling

v2.0 physics loss:
- **Mass conservation:** d(phi*rho)/dt + div(rho*v) = q_wells
- **Energy conservation:** d(phi*rho*h)/dt + div(rho*h*v) = div(K*gradT) + q_wells
- **Saturation constraint:** Sl + Sg = 1 (hard constraint via sigmoid)
- **Steam table consistency:** h(T,P) must be physically consistent
- **Gravity term:** P gradient should include rho*g*dz component

Tasks:
- [ ] Implement 3D U-Net architecture in PyTorch
- [ ] Design input preprocessing pipeline for TOUGH3 outputs
- [ ] Design output denormalization pipeline
- [ ] Implement upgraded physics loss functions
- [ ] Benchmark training time on VPS CPU
- [ ] Determine if GPU is needed (cloud GPU if so)

---

### Phase 4: Validation and Benchmarking (Weeks 8-10)

**Goal:** Prove the model works on real geothermal physics.

#### 4A. Validation Against Brady Hot Springs

The USGS published these benchmarks for Brady-like reservoir ML:

| Metric | USGS Result | Our Target |
|--------|-------------|------------|
| Temperature error | <3.68% | <4.0% |
| Pressure error | <4.75% | <5.0% |
| Energy error | <4.04% | <5.0% |
| Inference time | 0.9 s | <0.5 s |

Tasks:
- [ ] Train on Brady OSR data
- [ ] Evaluate on held-out Brady scenarios
- [ ] Compare results with published USGS numbers
- [ ] Document where we match and where we don't

#### 4B. Validation Against Indonesian Field Data

Use published monitoring data from Stanford/WGC papers:
- Kamojang production decline curves (Darma et al., 2010)
- Wayang Windu expansion history (Star Energy publications)
- Darajat production data (Hadi et al., various years)

This is qualitative validation — does the model produce physically reasonable results for Indonesian-like parameters?

Tasks:
- [ ] Build Indonesian validation scenarios from published parameters
- [ ] Run predictions and compare to published production histories
- [ ] Document results in validation report
- [ ] Identify remaining gaps

#### 4C. Updated Technical Report

Publish GeoForce v2.0 technical report covering:
- TOUGH3-trained data (vs analytical in v1.1)
- Two-phase results (vs single-phase)
- 3D results (vs 2D)
- Brady benchmark comparison
- Indonesian field qualitative validation
- Honest limitations list

---

### Phase 5: Platform Integration (Weeks 10-12)

**Goal:** Replace v1.1 on the platform with v2.0.

Tasks:
- [ ] Update serve.py for new model architecture and I/O format
- [ ] Update platform GeoForcePage.tsx for new output variables (add saturation, enthalpy views)
- [ ] Add 3D visualization (three.js or deck.gl for 3D grid display)
- [ ] Update HuggingFace model card and dataset
- [ ] Write LinkedIn post announcing v2.0
- [ ] Update landing page copy

---

### Phase 6: Publish and Position (Weeks 12+)

Tasks:
- [ ] Submit to Stanford Geothermal Workshop (annual, January deadline typically)
- [ ] Submit to GRC (Geothermal Resources Council) annual meeting
- [ ] Publish v2.0 model + Indonesian dataset on HuggingFace
- [ ] Write technical blog post comparing v1.1 to v2.0 (honest, show the journey)
- [ ] Reach out to ITB Geothermal Engineering faculty for review
- [ ] Prepare data-sharing proposal for Pertamina Geothermal Energy

---

## Available Public Data Sources

### Ready to Use Now

| Dataset | Source | URL |
|---------|--------|-----|
| NREL Brady OSR | NREL/USGS | https://github.com/NREL/geothermal_osr |
| Brady Hot Springs ML Results | GDR | https://gdr.openei.org/submissions/1346 |
| Utah FORGE | DOE | https://gdr.openei.org/forge |
| GeoThermalCloud Data | LANL | https://github.com/SmartTensors/GeoThermalCloud.jl |
| GDR Repository | DOE | https://gdr.openei.org/ |
| Nevada GEOTHERM | NBMG | https://nbmg.unr.edu/geothermal/Data.html |

### Simulators

| Simulator | License | URL |
|-----------|---------|-----|
| TOUGH3 | Free for research | https://tough.lbl.gov/software/tough3/ |
| Waiwera | Open-source | https://waiwera.github.io/ |
| PyTOUGH | Open-source | https://github.com/acroucher/PyTOUGH |
| FEHM | Open-source | https://fehm.lanl.gov/ |
| GEOPHIRES-X | Open-source | https://github.com/NREL/GEOPHIRES-X |

### Key Papers

| Paper | Authors | Year | Relevance |
|-------|---------|------|-----------|
| Modeling Subsurface Performance with ML | Beckers et al. (NREL/USGS) | 2022 | Brady benchmark, our primary comparison target |
| Prediction Modeling for Geothermal Reservoirs Using DL | Gudmundsdottir & Horne (Stanford) | 2020 | LSTM vs feedforward for well-level prediction |
| GNN for Multi-Physics Geothermal with DFN | Gudala & Yan | 2025 | GNN architecture for fractured reservoirs (v3.0 target) |
| LSTM-CNN Surrogate for Well Placement | Various | 2025 | 99.8% accuracy on homogeneous, 94% on heterogeneous |
| Physics-Guided DL for Geothermal Energy | Various | 2023 | Physics loss design for geothermal |
| ML/DL in Geothermal Review | Al-Fakih et al. | 2024 | Comprehensive review of all approaches |

---

## Compute Requirements Estimate

| Task | Compute | Time Estimate |
|------|---------|---------------|
| TOUGH3 simulation (1 scenario) | VPS CPU | ~30-60 min |
| 1,000 scenarios campaign | VPS CPU (2 cores) | ~20-40 days |
| 1,000 scenarios campaign | Cloud (16 cores) | ~3-5 days |
| U-Net training (1,000 scenarios) | VPS CPU | ~4-8 hours |
| U-Net training (5,000 scenarios) | Cloud GPU (A10) | ~2-4 hours |
| Validation + reporting | VPS CPU | ~1 day |

**Budget note:** The simulation campaign is the bottleneck. Running 1,000 TOUGH3 simulations on VPS will take weeks. Consider:
- Cloud burst (AWS/GCP spot instances, ~$50-100 for the campaign)
- Reducing to 500 scenarios initially
- Using Waiwera with MPI parallelism if VPS has multiple cores

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| TOUGH3 license takes too long | Delays Phase 2 by weeks | Start with Waiwera (no license needed) |
| VPS too slow for 1,000 simulations | Campaign takes >1 month | Use cloud spot instances for batch |
| 3D U-Net too large for CPU training | Training takes days | Start with 32x32x8 grid, upgrade later |
| Indonesian field data not detailed enough | Can't validate against real fields | Use Brady benchmark as primary validation + qualitative Indonesian comparison |
| Two-phase physics makes the problem much harder | Model accuracy drops below acceptable | Start with liquid-dominated fields (Salak, Ulubelu) before attempting vapor-dominated (Kamojang) |

---

## Success Criteria for v2.0

| Metric | Target | Why |
|--------|--------|-----|
| Temperature RMSE | <5 C | Matches USGS Brady benchmark |
| Pressure RMSE | <0.5 MPa | Below typical wellbore measurement uncertainty |
| Steam saturation RMSE | <0.1 | Useful for production forecasting |
| R-squared (all variables) | >0.95 | Industry-acceptable prediction quality |
| Inference time | <1 second | Real-time exploration workflow |
| Physics violation rate | <1% | Mass and energy conservation |
| Can predict two-phase | Yes | Required for Indonesian fields |
| 3D | Yes | Required for gravity effects |
| Validated against Brady | Yes | Published benchmark comparison |

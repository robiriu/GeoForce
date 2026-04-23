# GeoForce v2.0 — Transformation Progress

**Last Updated:** 2026-04-16

---

## Phase Status

| Phase | Name | Status | Started | Completed |
|-------|------|--------|---------|-----------|
| 1 | Real Data Foundation | Not Started | — | — |
| 2 | Real Simulator Setup | Not Started | — | — |
| 3 | Model Architecture Upgrade | Not Started | — | — |
| 4 | Validation and Benchmarking | Not Started | — | — |
| 5 | Platform Integration | Not Started | — | — |
| 6 | Publish and Position | Not Started | — | — |

---

## Detailed Task Tracking

### Phase 1: Real Data Foundation

**1A. NREL Brady Hot Springs Dataset**
- [ ] Clone NREL/geothermal_osr repository
- [ ] Explore data format, understand scenario structure
- [ ] Retrain current CNN on Brady data
- [ ] Compare results against published USGS benchmark (<3.68% T error)
- [ ] Document gaps

**1B. Utah FORGE Dataset**
- [ ] Download FORGE well log data
- [ ] Download 3D geological model
- [ ] Map FORGE data structure to GeoForce input requirements

**1C. Indonesian Field Parameters**
- [ ] Compile parameter table from published papers
- [ ] Document permeability ranges for Indonesian volcanic systems
- [ ] Document fracture characteristics
- [ ] Build scenarios.yaml v2 with realistic Indonesian ranges

### Phase 2: Real Simulator Setup

**2A. Simulator Installation**
- [ ] Request TOUGH3 license from LBNL
- [ ] Install Waiwera (backup, open-source)
- [ ] Install PyTOUGH
- [ ] Run TOUGH2 standard benchmark problems

**2B. Simulation Campaign**
- [ ] Write simulation campaign generator script
- [ ] Define 3D grid with vertical layering
- [ ] Run pilot batch (10 scenarios)
- [ ] Estimate total compute time
- [ ] Run full campaign (1,000+ scenarios)

### Phase 3: Model Architecture Upgrade

- [ ] Implement 3D U-Net architecture
- [ ] Design input preprocessing for TOUGH3 outputs
- [ ] Design output denormalization pipeline
- [ ] Implement upgraded physics loss functions
- [ ] Benchmark training time

### Phase 4: Validation and Benchmarking

- [ ] Train on Brady OSR data
- [ ] Evaluate against USGS published benchmarks
- [ ] Build Indonesian validation scenarios
- [ ] Run qualitative validation against published field data
- [ ] Write v2.0 technical report

### Phase 5: Platform Integration

- [ ] Update serve.py for v2.0 model
- [ ] Update platform GeoForcePage.tsx
- [ ] Add 3D visualization
- [ ] Update HuggingFace model card
- [ ] Update landing page copy

### Phase 6: Publish and Position

- [ ] Submit to Stanford Geothermal Workshop
- [ ] Publish v2.0 model on HuggingFace
- [ ] LinkedIn announcement
- [ ] ITB faculty review outreach
- [ ] Pertamina data-sharing proposal

---

## Log

### 2026-04-16
- Created transformation plan
- Completed deep research on state-of-the-art
- Identified NREL Brady OSR as immediate training data source
- Identified TOUGH3/Waiwera as simulator options
- Identified 3D U-Net as v2.0 architecture target
- Identified GNN (SeqSage) as v3.0 architecture for fracture systems

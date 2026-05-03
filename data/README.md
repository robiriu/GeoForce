# GeoForce v2.0 — Data Directory

This directory holds external datasets used for Phase 1 (Real Data Foundation) and beyond. Contents are not committed in full — most subdirectories are git-ignored or pulled from upstream sources at setup time.

## Subdirectories

### `brady/` — NREL Open-Source Reservoir (OSR)

- **Source:** https://github.com/NREL/geothermal_osr
- **License:** BSD 3-Clause (Alliance for Sustainable Energy, LLC, 2022)
- **Format:** 102 .xlsx files in `data/OpenSourceReservoir-CMG/`, one per simulated scenario. Each file: 241 monthly timesteps × 30 well measurements (4 injectors + 6 producers; mass flow [kg/day], bottom-hole pressure [kPa], bottom-hole temperature [°C]) + final-step Obj Func.
- **Reference paper:** Duplyakin et al. (2022). "Modeling Subsurface Performance of a Geothermal Reservoir Using Machine Learning." *Energies* 15(3), 967. https://www.mdpi.com/1996-1073/15/3/967
- **OSTI dataset record:** https://www.osti.gov/biblio/1842479
- **Note for v2.0:** Brady is a **well-time-series benchmark**, not a 2D field benchmark. The v1.1 ReservoirCNN (32×32 spatial output) cannot be evaluated on Brady directly because the I/O shapes are structurally different. Brady is therefore reserved as the **Phase 5 validation target** for the v2.0 3D U-Net once it produces well outputs as a by-product of voxel fields. See `loader.py` and PROGRESS.md §1A.

To clone (one-time setup):

```bash
cd data
git clone --depth 1 https://github.com/NREL/geothermal_osr brady
```

Loader: `data/brady/loader.py` — `load_all()` returns 101 `BradyScenario` dataclasses, `stack()` produces batched (N, 241, k) arrays for ML use.

### `forge/` — Utah FORGE (Phase 1B, not yet downloaded)

Planned: well-log + 3D geological model from Utah FORGE EGS site. See PROGRESS.md §1B.

### `indonesia/` — Indonesian field parameters (Phase 1C, not yet populated)

Planned: `parameters.yaml` with Kamojang, Darajat, Wayang Windu, Salak, Lahendong, Ulubelu, Karaha-Talaga Bodas. See PROGRESS.md §1C.

## License notes

Each subdirectory may carry its own license. Do not redistribute downstream artifacts (HF Datasets, training notebooks) without preserving upstream attribution.

# Indonesian Geothermal Field Parameters

Curated published parameter ranges for the seven Indonesian geothermal fields most relevant to GeoForce v2.0 validation:

| Field | Region | Operator | Phase | Confidence |
|---|---|---|---|---|
| Kamojang | West Java | PGE | vapor | High |
| Darajat | West Java | Star Energy | vapor | High |
| Wayang Windu | West Java | Star Energy | liquid (some shallow vapor) | Medium |
| Salak / Awibengkok | West Java | Star Energy | liquid | High |
| Lahendong | North Sulawesi | PGE | liquid | High |
| Ulubelu | Lampung (Sumatra) | PGE | liquid | High |
| Karaha-Talaga Bodas | West Java | PGE | vapor | Medium |

Source: `parameters.yaml` in this directory.

## What was extracted

For each field:
- Reservoir temperature range (°C)
- Reservoir depth range (m below surface)
- Porosity (matrix; sometimes effective)
- Permeability (matrix vs. fracture / effective when known)
- Initial pressure range (MPa)
- Dominant phase (vapor / liquid / two-phase)
- Primary citations (peer-reviewed journals + Stanford Geothermal Workshop archive)

## What remains unknown

- **Wayang Windu** — well-test reports are commercially restricted; numbers are based on regional analogs.
- **Karaha-Talaga Bodas** — limited recent open literature; values are conservative vapor-dominated analogs (Kamojang/Darajat).
- Field-scale **anisotropy tensors** are not extracted — only scalar matrix vs. fracture ranges.
- **Production-decline curves** with timestamps are not in this YAML; they live in operator annual reports (Pertamina Geothermal Energy, Star Energy) and will be ingested in Phase 5 validation work as needed.
- **Steam fraction profiles** for vapor-dominated fields are field-specific and will be assembled per-field during Phase 4 training-data design.

## Sourcing methodology

1. Stanford Geothermal Workshop archive (open access at `pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/`) — primary source for recent reservoir characterization.
2. Geothermics journal special issues on Indonesian fields (2008, 2010, 2018) — primary source for foundational characterization.
3. World Geothermal Congress proceedings — secondary source.
4. Cross-checked against summary papers like Allis (2000) on vapor-dominated systems.

## Update policy

Parameters here are **starting values for v2.0 scenario-generation bounds and qualitative validation only**. They are not authoritative reservoir descriptions. When a higher-fidelity number is needed (e.g., for Phase 2/3 simulation campaigns), pull the source PDF, extract the specific number under its specific context, and either update this YAML or override per-scenario in `simulation/scenarios_v2.yaml`.

## License

This compilation (the YAML curation, not the underlying papers) is released under the same MIT license as the GeoForce project. Cite both:
1. The original published source in the YAML's `sources` field.
2. This file, if convenient: GeoForce v2.0, `data/indonesia/parameters.yaml`.

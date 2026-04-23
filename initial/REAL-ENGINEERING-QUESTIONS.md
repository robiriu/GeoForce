# Real Engineering Questions GeoForce v2.0 Must Answer

These are the questions that reservoir engineers at Pertamina Geothermal Energy (PGE), Star Energy, and similar operators actually ask during exploration, development, and production management. GeoForce v2.0 must answer these to be a real engineering tool.

Each question includes the engineering context, what data is needed, and what GeoForce v2.0 must output. After the transformation, these questions become our landing page triggers — proof that GeoForce solves real problems.

---

## Exploration Phase

### Q1: "If I drill here, what temperature will I hit at 2,000 meters?"

**Who asks this:** Exploration geologist at PGE planning a new well at Karaha-Talaga Bodas or a greenfield prospect.

**Context:** An exploration well costs $7-8M USD. Success rate in Indonesia is ~60-70%. Before committing, the team needs to estimate downhole temperature at target depth based on surface surveys (MT resistivity, gravity, geochemistry) and nearby well data.

**What GeoForce v2.0 needs:**
- Input: MT-derived resistivity model (proxy for clay cap and reservoir boundary), surface heat flow estimate, regional geology (rock type, fault proximity), nearest well temperature data
- Output: Predicted temperature profile with depth (T vs z), confidence interval
- Speed: <1 second (so engineers can test 50 candidate locations in a meeting)

**v1.1 status:** Cannot do this. 2D only, no depth dimension, no link to surface geophysics.

**v2.0 target:** Given a 3D parameter set (T_base, k, porosity, depth, heat source), predict the 3D temperature field. The well temperature profile is a vertical slice through this field.

---

### Q2: "How many megawatts can this reservoir support for 30 years?"

**Who asks this:** Resource assessment engineer at Star Energy evaluating Wayang Windu expansion (Unit 3 proposal).

**Context:** Before committing to a $200-500M power plant, the operator needs to know if the reservoir can sustain the extraction rate for the 30-year concession period. This requires predicting temperature and pressure decline under sustained production.

**What GeoForce v2.0 needs:**
- Input: Reservoir size, initial T/P, permeability, porosity, number of production wells, production rate per well, reinjection strategy
- Output: Temperature and pressure at production wells over 30 years. Steam fraction over time. Cumulative energy extracted (GWh).
- Critical metric: Year when temperature drops below economic cutoff (~180 C for flash plants)

**v1.1 status:** Can predict T/P decline over 20 years but with wrong physics (no steam, no reinjection effects). Directionally correct but not quantitatively useful.

**v2.0 target:** Predict two-phase T, P, steam saturation, enthalpy at wells over 30 years with <5% error.

---

### Q3: "Where should I place the next 3 production wells to maximize output?"

**Who asks this:** Reservoir engineer at PGE Kamojang planning make-up well drilling to maintain 375 MW capacity as older wells decline.

**Context:** PGE needs to drill ~2 make-up wells per year across their fleet to maintain capacity. Each well costs $5-7M. Choosing the wrong location wastes capital and may interfere with existing production (pressure interference, thermal breakthrough).

**What GeoForce v2.0 needs:**
- Input: Existing well locations and production history, reservoir model (T/P/k/phi), surface constraints (land access, environmental)
- Output: Ranked candidate locations with predicted production rate, cumulative output over 20 years, interference risk score
- Speed: <10 seconds per candidate (evaluate 1,000 candidates in ~3 hours, including optimization)

**v1.1 status:** Has a well placement optimization concept but the underlying prediction is too simplified to be useful.

**v2.0 target:** Run Monte Carlo optimization over well locations using the surrogate model, with uncertainty bounds on each candidate.

---

## Development Phase

### Q4: "What happens if we reinject at 80 C instead of 160 C?"

**Who asks this:** Process engineer at Star Energy Darajat evaluating brine reinjection strategies.

**Context:** Separated brine from flash plants must be reinjected. Colder reinjection saves surface equipment costs but risks thermal breakthrough — cold water reaching production wells and killing steam output. The tradeoff depends on permeability pathways and distance between injection and production wells.

**What GeoForce v2.0 needs:**
- Input: Full reservoir model, injection well location, injection temperature, injection rate, production well locations
- Output: Time to thermal breakthrough at each production well. Temperature at production wells over time. Optimal injection temperature that balances economics and thermal risk.

**v1.1 status:** Cannot model injection (single-phase, no injection wells in the model). This is a fatal gap.

**v2.0 target:** Model injection-production coupling with two-phase physics. Predict breakthrough time to within +-3 years.

---

### Q5: "Will this reservoir transition from liquid-dominated to vapor-dominated over 20 years of production?"

**Who asks this:** Senior reservoir engineer at PGE assessing long-term behavior of Ulubelu or Lahendong.

**Context:** Some Indonesian fields start as liquid-dominated but can transition to two-phase or vapor-dominated as pressure declines during production. This fundamentally changes well behavior, surface equipment requirements, and revenue (steam plants vs binary plants).

**What GeoForce v2.0 needs:**
- Input: Initial T, P, steam saturation (possibly 100% liquid), production schedule
- Output: Steam saturation evolution over 30 years, zone-by-zone. Phase boundary migration. When and where boiling begins.

**v1.1 status:** Impossible. Single-phase model cannot represent phase transitions.

**v2.0 target:** This is the core capability of v2.0 — predicting phase evolution in 3D. Success here validates the entire TOUGH2 training data approach.

---

## Production Management

### Q6: "Our production at Well KMJ-68 has declined 15% this year. Why, and what should we do?"

**Who asks this:** Production engineer at PGE Kamojang reviewing quarterly production report.

**Context:** Production decline can be caused by many factors: pressure depletion, scaling (silica deposits in wellbore), cold water influx from nearby injection, well mechanical damage, or reservoir boundary effects. The engineer needs to diagnose the cause and recommend intervention.

**What GeoForce v2.0 needs:**
- Input: Historical production data (wellhead T, P, flow rate), surrounding well data, reservoir model
- Output: Most likely cause of decline (pressure depletion vs thermal breakthrough vs scaling), predicted future production under different intervention scenarios (workover, new make-up well, reduced injection nearby)

**v1.1 status:** Cannot do diagnostic analysis. No history matching capability.

**v2.0 target:** Given a calibrated reservoir model, predict what-if scenarios for different interventions. History matching is the key capability needed — adjusting model parameters to fit observed production data.

---

### Q7: "If we increase production from 227 MW to 300 MW at Wayang Windu, how long before the reservoir cannot sustain it?"

**Who asks this:** VP of Operations at Star Energy evaluating capacity expansion proposal.

**Context:** Wayang Windu has a complex reservoir with liquid-dominated zones overlaid by vapor caps. Increasing production requires understanding whether the reservoir can supply the additional steam long-term, or whether the expansion will cause unsustainable pressure decline.

**What GeoForce v2.0 needs:**
- Input: Calibrated Wayang Windu reservoir model, current production wells, proposed new wells, increased extraction rate
- Output: Reservoir pressure and temperature evolution at 300 MW vs 227 MW. Year when output drops below 300 MW (sustainability limit). Optimal staged ramp-up schedule.

**v1.1 status:** Cannot represent the multi-zone structure of Wayang Windu (liquid + vapor caps at different depths).

**v2.0 target:** 3D two-phase model that captures vertical zonation and gravity segregation.

---

## Regulatory and Environmental

### Q8: "What is the probability that production will cause surface subsidence greater than 5 cm over 20 years?"

**Who asks this:** Environmental compliance officer preparing AMDAL (environmental impact assessment) for a new geothermal development.

**Context:** Indonesian regulations require environmental impact assessments before new development. Pressure drawdown from geothermal production can cause surface subsidence. The officer needs probabilistic estimates, not single-point predictions.

**What GeoForce v2.0 needs:**
- Input: Reservoir parameters with uncertainty ranges, production schedule
- Output: Probabilistic forecast (P10/P50/P90) of cumulative pressure drawdown, linked to a geomechanical model for subsidence estimation
- Key requirement: **Uncertainty quantification** — not just best-guess, but probability distributions

**v1.1 status:** No UQ capability. Deterministic single-point predictions only.

**v2.0 target:** Run 1,000+ Monte Carlo samples in <20 minutes to produce P10/P50/P90 envelopes for all output variables.

---

### Q9: "Can we meet PLN's 30-year PPA commitment at 95% capacity factor?"

**Who asks this:** Commercial director at PGE negotiating a Power Purchase Agreement with PLN for a new development.

**Context:** PLN PPAs for geothermal typically require 85-95% capacity factor over 30 years. The operator needs high confidence that the reservoir can deliver. Over-promising means financial penalties; under-promising means lost revenue.

**What GeoForce v2.0 needs:**
- Input: Reservoir model, development plan (wells, production rate, reinjection)
- Output: Year-by-year capacity factor prediction with uncertainty bands. Probability of maintaining >95% CF for 30 years. Number of make-up wells needed and when.

**v1.1 status:** Cannot provide this level of production forecasting.

**v2.0 target:** Coupled reservoir-wellbore model that converts subsurface T/P/steam to surface power output.

---

## Advanced / Future (v3.0+)

### Q10: "How does seismic activity correlate with injection rate, and can we optimize injection to minimize induced seismicity risk?"

**Who asks this:** Seismologist at PGE monitoring induced seismicity at a field with community concerns.

**Context:** Geothermal reinjection can trigger microseismic events. At some Indonesian fields (e.g., near populated areas), this is a social license issue. Understanding the link between injection parameters and seismicity allows proactive management.

**GeoForce v3.0+ needs:** Thermo-hydro-mechanical (THM) coupling — linking fluid pressure changes to stress changes and fault slip. This is the frontier of geothermal reservoir modeling.

---

### Q11: "What is the optimal development sequence for a 5-unit, 250 MW geothermal complex over 15 years?"

**Who asks this:** VP of Development at PGE planning a greenfield development (e.g., new concession in Flores or Sulawesi).

**Context:** Large geothermal developments are staged: 30 MW first, then expand to 60, 110, 175, 250 MW over 10-15 years. Each stage involves new wells, pipelines, and plant capacity. The optimal staging depends on reservoir behavior — production decline in early units determines when and where to drill for later stages.

**GeoForce v3.0+ needs:** Multi-stage optimization combining reservoir prediction, well placement, and economic modeling. This is where the agent framework becomes critical — a reservoir agent, an optimization agent, and an economics agent working together.

---

## Summary: What Each Question Requires

| Question | Phase Physics | 3D | History Matching | UQ | Well Model | v2.0 Scope |
|----------|-------------|----|-----------------|----|-----------|------------|
| Q1: Drill temperature | Needed | Yes | No | No | No | Yes |
| Q2: MW capacity | Needed | Yes | No | No | Basic | Yes |
| Q3: Well placement | Needed | Yes | No | Yes | Basic | Yes |
| Q4: Reinjection temp | Critical | Yes | No | No | No | Yes |
| Q5: Phase transition | Critical | Yes | No | No | No | Yes |
| Q6: Decline diagnosis | Needed | Yes | Yes | No | Yes | Partial |
| Q7: Capacity expansion | Needed | Yes | Ideally | No | Basic | Yes |
| Q8: Subsidence risk | Needed | Yes | No | Yes | No | Yes (UQ) |
| Q9: PPA commitment | Needed | Yes | Ideally | Yes | Yes | Partial |
| Q10: Induced seismicity | THM | Yes | Yes | Yes | No | v3.0 |
| Q11: Development sequence | Needed | Yes | Yes | Yes | Yes | v3.0 |

**v2.0 can directly address Q1-Q5 and Q7-Q8. Q6, Q9 are partially addressable. Q10-Q11 are v3.0 targets.**

---

## Landing Page Use

After v2.0 is complete, these questions become the marketing hook. Instead of generic "AI for geothermal", the landing page shows:

> **"If I drill here, what temperature will I hit at 2,000 meters?"**
> GeoForce answers in 0.3 seconds. TOUGH2 takes 45 minutes.

> **"How many megawatts can this reservoir sustain for 30 years?"**
> GeoForce runs 10,000 scenarios overnight. Manual modeling takes 6 months.

> **"Where should I place the next 3 wells to maximize output?"**
> GeoForce evaluates 1,000 candidates in 3 hours. An engineer evaluates 5 per week.

This is specific. This is what engineers search for. This is what makes ForceX AI a tool, not a demo.

---
name: field-visualization
description: Render 2D temperature and pressure fields as matplotlib heatmaps, with optional side-by-side solver-vs-surrogate comparison, P10/P50/P90 uncertainty overlays, well markers, and time sequences. Saves figures to demo/figures/. Use whenever any agent produces a T or P field.
---

# Field Visualization Skill

Turn (H, W) or (T, H, W) arrays into clear, labeled matplotlib figures.

## Core Plot Functions

Located in `tools/visualize.py`:

### `plot_single(field, kind, title=None, well_locations=None, save_as=None)`

Render one temperature or pressure field as a heatmap.

```python
from tools.visualize import plot_single

path = plot_single(
    field=T_field,           # (32, 32) numpy array in °C
    kind="temperature",      # or "pressure"
    title="Temperature at t=20y",
    well_locations=[(10, 16), (20, 16)],
    save_as="demo/figures/q1_T_year20.png",
)
```

### `plot_side_by_side(solver_field, surrogate_field, kind, save_as=None)`

Two subplots side-by-side, shared colorbar.

```python
path = plot_side_by_side(
    solver_field=solver_T,
    surrogate_field=surrogate_T,
    kind="temperature",
    save_as="demo/figures/q1_comparison.png",
)
```

### `plot_time_sequence(fields, times_years, kind, save_as=None)`

Grid of subplots, one per timestep.

```python
path = plot_time_sequence(
    fields=T_timesteps,     # (5, 32, 32)
    times_years=[4, 8, 12, 16, 20],
    kind="temperature",
    save_as="demo/figures/q2_T_sequence.png",
)
```

### `plot_with_uq(median, p10, p90, kind, save_as=None)`

Median field + uncertainty band as contour overlay.

```python
path = plot_with_uq(
    median=p50,             # (32, 32)
    p10=p10,
    p90=p90,
    kind="temperature",
    save_as="demo/figures/q2_T_uq.png",
)
```

## Colormap Conventions

| Variable | Colormap | vmin | vmax | Unit |
|---|---|---|---|---|
| Temperature | `magma` | 25 | 350 | °C |
| Pressure | `viridis` | 5 | 25 | MPa |
| Saturation | `cool` | 0 | 1 | — (not used in v0.1) |
| UQ band | `plasma` (alpha=0.3) | — | — | — |

## Annotations

Every figure includes:
- Title with query context
- Colorbar with units
- Well markers (white circles = producers, cyan triangles = injectors)
- Axis labels: "x (cell)" or "x (m)" depending on scale

## Output Location

All figures save to `demo/figures/`. Use descriptive, collision-free filenames:
- `<query_id>_<kind>_<time>.png` — e.g., `q1_T_year20.png`
- Use `.svg` for the hero figure in the demo video (scalable)

## Anti-patterns

- Do not use `plt.show()` — headless only
- Do not overwrite files without warning
- Do not mix colormaps for the same variable across figures
- Do not plot field rotation or 3D projections

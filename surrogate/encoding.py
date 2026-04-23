"""v1.1 input/output encoding for ReservoirCNN.

FROZEN — these constants must match the values baked into
`weights/geoforce_cnn_v1.1.pt` exactly. Any change invalidates the weights.

v1.1 input channels (6, 32, 32):
    0: initial temperature field (per-cell, normalized to [0, 1] on [T_MIN, T_MAX])
    1: log10 permeability (scalar broadcast, normalized on [LOG_PERM_MIN, LOG_PERM_MAX])
    2: well mask (1.0 at well cells, decaying to neighbors)
    3: base pressure (scalar broadcast, normalized on [BASE_P_MIN, BASE_P_MAX])
    4: porosity (scalar broadcast, normalized on [POR_MIN, POR_MAX])
    5: depth (scalar broadcast, normalized on [DEPTH_MIN, DEPTH_MAX])

Output channels (10, 32, 32):
    0-4: temperature at 5 timesteps, sigmoid-normalized on [T_MIN, T_MAX] in degrees C
    5-9: pressure at 5 timesteps, sigmoid-normalized on [P_MIN, P_MAX] in Pa
"""

from __future__ import annotations

import numpy as np
import torch

GRID_SIZE = 32
N_TIME_STEPS = 5

# Frozen v1.1 normalization constants (embedded in the checkpoint).
NORMALIZATION: dict[str, float] = {
    "T_MIN": 25.0,
    "T_MAX": 350.0,
    "P_MIN": 1.0e5,
    "P_MAX": 5.0e7,
    "LOG_PERM_MIN": -16.0,
    "LOG_PERM_MAX": -12.0,
    "POR_MIN": 0.01,
    "POR_MAX": 0.15,
    "DEPTH_MIN": 800.0,
    "DEPTH_MAX": 2500.0,
    "BASE_T_MIN": 180.0,
    "BASE_T_MAX": 320.0,
    "BASE_P_MIN": 5.0e6,
    "BASE_P_MAX": 2.5e7,
}


def _norm(value: float, lo: float, hi: float) -> float:
    return float(np.clip((value - lo) / (hi - lo), 0.0, 1.0))


def _build_well_mask(
    well_locations: list[tuple[int, int]],
    grid_size: int = GRID_SIZE,
) -> np.ndarray:
    """Match the training well-mask encoding exactly (1.0 at well, decay to neighbors)."""
    mask = np.zeros((grid_size, grid_size), dtype=np.float32)
    for wr, wc in well_locations:
        wr, wc = int(wr), int(wc)
        if not (0 <= wr < grid_size and 0 <= wc < grid_size):
            continue
        mask[wr, wc] = 1.0
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                r, c = wr + dr, wc + dc
                if 0 <= r < grid_size and 0 <= c < grid_size:
                    dist = abs(dr) + abs(dc)
                    mask[r, c] = max(mask[r, c], 1.0 / (1.0 + dist))
    return mask


def build_input_tensor(
    *,
    initial_temperature: np.ndarray,
    log_permeability: float,
    well_locations: list[tuple[int, int]],
    base_pressure: float,
    porosity: float,
    depth: float,
    grid_size: int = GRID_SIZE,
) -> torch.Tensor:
    """Assemble the 6-channel input tensor matching v1.1 training.

    Args:
        initial_temperature: 2D array of shape (32, 32) in degrees Celsius.
        log_permeability: scalar log10 permeability (typical -16 to -12).
        well_locations: list of (row, col) integer tuples.
        base_pressure: scalar pressure at reservoir base (Pa).
        porosity: dimensionless (0.01 to 0.15).
        depth: reservoir depth (m, 800 to 2500).
        grid_size: grid cells per side (default 32, must match weights).

    Returns:
        torch.Tensor of shape (1, 6, grid_size, grid_size), dtype float32.
    """
    if initial_temperature.shape != (grid_size, grid_size):
        msg = (
            f"initial_temperature shape {initial_temperature.shape} "
            f"does not match grid_size={grid_size}"
        )
        raise ValueError(msg)

    n = NORMALIZATION
    arr = np.zeros((6, grid_size, grid_size), dtype=np.float32)

    t0_norm = (initial_temperature - n["T_MIN"]) / (n["T_MAX"] - n["T_MIN"])
    arr[0] = np.clip(t0_norm, 0.0, 1.0).astype(np.float32)

    arr[1] = _norm(log_permeability, n["LOG_PERM_MIN"], n["LOG_PERM_MAX"])
    arr[2] = _build_well_mask(well_locations, grid_size)
    arr[3] = _norm(base_pressure, n["BASE_P_MIN"], n["BASE_P_MAX"])
    arr[4] = _norm(porosity, n["POR_MIN"], n["POR_MAX"])
    arr[5] = _norm(depth, n["DEPTH_MIN"], n["DEPTH_MAX"])

    return torch.from_numpy(arr).unsqueeze(0)


def denormalize_output(out: torch.Tensor) -> dict[str, np.ndarray]:
    """Convert model output from [0,1] to physical units.

    Args:
        out: tensor of shape (batch, 10, H, W) with values in [0, 1].

    Returns:
        dict with keys 'temperature' (shape (batch, 5, H, W), deg C) and
        'pressure' (shape (batch, 5, H, W), Pa).
    """
    n = NORMALIZATION
    arr = out.detach().cpu().numpy()
    t_norm = arr[:, :N_TIME_STEPS]
    p_norm = arr[:, N_TIME_STEPS:]
    temperature = t_norm * (n["T_MAX"] - n["T_MIN"]) + n["T_MIN"]
    pressure = p_norm * (n["P_MAX"] - n["P_MIN"]) + n["P_MIN"]
    return {"temperature": temperature, "pressure": pressure}

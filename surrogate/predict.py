"""Model loader and inference wrapper for GeoForce v1.1 surrogate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from .encoding import build_input_tensor, denormalize_output
from .model import ReservoirCNN

DEFAULT_WEIGHTS = Path(__file__).parent / "weights" / "geoforce_cnn_v1.1.pt"

_model_cache: ReservoirCNN | None = None


def load_model(
    weights_path: str | Path | None = None,
    device: str | torch.device = "cpu",
) -> ReservoirCNN:
    """Load v1.1 ReservoirCNN weights, cached in process memory.

    Args:
        weights_path: path to the .pt checkpoint. Defaults to the bundled v1.1.
        device: torch device (default CPU — the model is tiny).

    Returns:
        ReservoirCNN in eval mode with weights loaded.
    """
    global _model_cache
    if _model_cache is not None and weights_path is None:
        return _model_cache

    path = Path(weights_path) if weights_path else DEFAULT_WEIGHTS
    if not path.exists():
        msg = f"weights not found at {path}"
        raise FileNotFoundError(msg)

    ckpt: Any = torch.load(path, map_location=device, weights_only=False)
    state_dict = ckpt["model_state_dict"] if isinstance(ckpt, dict) and "model_state_dict" in ckpt else ckpt
    in_channels = ckpt.get("in_channels", 6) if isinstance(ckpt, dict) else 6

    model = ReservoirCNN(in_channels=in_channels)
    model.load_state_dict(state_dict)
    model.eval()
    model.to(device)

    if weights_path is None:
        _model_cache = model
    return model


def predict(
    *,
    initial_temperature: np.ndarray,
    log_permeability: float,
    well_locations: list[tuple[int, int]],
    base_pressure: float,
    porosity: float,
    depth: float,
    model: ReservoirCNN | None = None,
) -> dict[str, np.ndarray]:
    """Run a single v1.1 surrogate prediction.

    Args:
        initial_temperature: (32, 32) array in deg C.
        log_permeability: scalar log10 permeability.
        well_locations: list of (row, col) tuples.
        base_pressure: Pa.
        porosity: dimensionless.
        depth: m.
        model: pre-loaded ReservoirCNN, or None to use the cached default.

    Returns:
        dict with:
            'temperature': (5, 32, 32) deg C
            'pressure':    (5, 32, 32) Pa
    """
    if model is None:
        model = load_model()

    x = build_input_tensor(
        initial_temperature=initial_temperature,
        log_permeability=log_permeability,
        well_locations=well_locations,
        base_pressure=base_pressure,
        porosity=porosity,
        depth=depth,
    )

    with torch.no_grad():
        y = model(x)

    out = denormalize_output(y)
    return {
        "temperature": out["temperature"][0],
        "pressure": out["pressure"][0],
    }

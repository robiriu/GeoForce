"""ReservoirCNN architecture for GeoForce v1.1.

Ported verbatim from ForceX-AI's training code. The state dict of
`weights/geoforce_cnn_v1.1.pt` loads into this class without renaming.

Architecture:
    encoder:  ConvBlock(6 -> 32) -> ConvBlock(32 -> 32)
    middle:   ResidualBlock(32) x 2
    decoder:  ConvBlock(32 -> 32) -> Conv2d(32 -> 10, 1x1) -> Sigmoid

57,802 parameters. ~3 ms per inference on CPU.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class ConvBlock(nn.Module):
    """Conv2d -> BatchNorm -> ReLU."""

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3) -> None:
        super().__init__()
        self.conv = nn.Conv2d(
            in_channels,
            out_channels,
            kernel_size,
            padding=kernel_size // 2,
            bias=False,
        )
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.relu(self.bn(self.conv(x)))


class ResidualBlock(nn.Module):
    """Residual block with two 3x3 convs and a skip connection."""

    def __init__(self, channels: int) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = out + residual
        return self.relu(out)


class ReservoirCNN(nn.Module):
    """CNN surrogate for 2D geothermal reservoir T and P prediction.

    Input shape:  (batch, 6, 32, 32) — see `encoding.py` for channel layout.
    Output shape: (batch, 10, 32, 32) — 5 T timesteps then 5 P timesteps,
        each normalized to [0, 1] via a final sigmoid.

    Use `predict.predict()` for the normal inference path (loads weights,
    builds tensor, denormalizes to physical units).
    """

    def __init__(
        self,
        in_channels: int = 6,
        n_time_steps: int = 5,
        base_filters: int = 32,
    ) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.n_time_steps = n_time_steps
        self.out_channels = 2 * n_time_steps

        self.encoder = nn.Sequential(
            ConvBlock(in_channels, base_filters, 3),
            ConvBlock(base_filters, base_filters, 3),
        )
        self.middle = nn.Sequential(
            ResidualBlock(base_filters),
            ResidualBlock(base_filters),
        )
        self.decoder = nn.Sequential(
            ConvBlock(base_filters, base_filters, 3),
            nn.Conv2d(base_filters, self.out_channels, 1),
            nn.Sigmoid(),
        )

        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.middle(self.encoder(x)))

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

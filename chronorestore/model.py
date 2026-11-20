"""Compact U-Net generator and PatchGAN discriminator."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn.utils import spectral_norm


class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, down: bool = False):
        super().__init__()
        if down:
            layers: list[nn.Module] = [nn.Conv2d(in_channels, out_channels, 4, 2, 1)]
        else:
            layers = [nn.Upsample(scale_factor=2, mode="nearest"), nn.Conv2d(in_channels, out_channels, 3, 1, 1)]
        layers += [nn.InstanceNorm2d(out_channels), nn.LeakyReLU(0.2, inplace=True)]
        self.layers = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x)


class Generator(nn.Module):
    def __init__(self, base: int = 32):
        super().__init__()
        self.in_conv = nn.Sequential(nn.Conv2d(3, base, 3, 1, 1), nn.LeakyReLU(0.2, inplace=True))
        self.down1 = ConvBlock(base, base * 2, down=True)
        self.down2 = ConvBlock(base * 2, base * 4, down=True)
        self.down3 = ConvBlock(base * 4, base * 8, down=True)
        self.down4 = ConvBlock(base * 8, base * 8, down=True)
        self.up1 = ConvBlock(base * 8, base * 8)
        self.up2 = ConvBlock(base * 16, base * 4)
        self.up3 = ConvBlock(base * 8, base * 2)
        self.up4 = ConvBlock(base * 4, base)
        self.out = nn.Sequential(nn.Conv2d(base * 2, 3, 3, 1, 1), nn.Sigmoid())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        a = self.in_conv(x)
        b = self.down1(a)
        c = self.down2(b)
        d = self.down3(c)
        e = self.down4(d)
        x = self.up1(e)
        x = self.up2(torch.cat((x, d), dim=1))
        x = self.up3(torch.cat((x, c), dim=1))
        x = self.up4(torch.cat((x, b), dim=1))
        return self.out(torch.cat((x, a), dim=1))


class Discriminator(nn.Module):
    def __init__(self, base: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            spectral_norm(nn.Conv2d(6, base, 4, 2, 1)), nn.LeakyReLU(0.2, inplace=True),
            spectral_norm(nn.Conv2d(base, base * 2, 4, 2, 1)), nn.InstanceNorm2d(base * 2), nn.LeakyReLU(0.2, inplace=True),
            spectral_norm(nn.Conv2d(base * 2, base * 4, 4, 2, 1)), nn.InstanceNorm2d(base * 4), nn.LeakyReLU(0.2, inplace=True),
            spectral_norm(nn.Conv2d(base * 4, 1, 3, 1, 1)),
        )

    def forward(self, degraded: torch.Tensor, restored: torch.Tensor) -> torch.Tensor:
        return self.net(torch.cat((degraded, restored), dim=1))

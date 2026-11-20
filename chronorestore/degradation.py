"""Ordered synthetic photo degradation for paired training."""

from __future__ import annotations

from io import BytesIO
import random

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance


def degrade(image: Image.Image, seed: int | None = None) -> Image.Image:
    """Return a reproducibly degraded RGB copy of a clean image."""
    rng = random.Random(seed)
    image = image.convert("RGB")
    width, height = image.size

    # Chemical aging: faded contrast and warm paper tint.
    image = ImageEnhance.Contrast(image).enhance(rng.uniform(0.55, 0.9))
    image = Image.blend(image, Image.new("RGB", image.size, (198, 171, 126)), rng.uniform(0.08, 0.28))
    image = ImageEnhance.Color(image).enhance(rng.uniform(0.35, 0.8))

    # Physical damage: scratches and dust blended into the print.
    damage = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(damage)
    for _ in range(rng.randint(2, 12)):
        x, y = rng.randrange(width), rng.randrange(height)
        x2 = max(0, min(width - 1, x + rng.randint(-25, 25)))
        y2 = max(0, min(height - 1, y + rng.randint(15, 100)))
        draw.line((x, y, x2, y2), fill=rng.choice(((244, 226, 190, 100), (45, 35, 27, 85))), width=rng.choice((1, 1, 2)))
    for _ in range(max(2, width * height // 18000)):
        x, y = rng.randrange(width), rng.randrange(height)
        radius = rng.choice((1, 1, 2, 3))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(234, 220, 190, 110))
    image = Image.alpha_composite(image.convert("RGBA"), damage).convert("RGB")

    # Digitization: sensor noise followed by JPEG compression.
    pixels = np.asarray(image, dtype=np.float32)
    noise = np.random.default_rng(seed).normal(0, rng.uniform(2, 10), pixels.shape)
    image = Image.fromarray(np.uint8(np.clip(pixels + noise, 0, 255)))
    encoded = BytesIO()
    image.save(encoded, format="JPEG", quality=rng.randint(35, 78))
    encoded.seek(0)
    image = Image.open(encoded).convert("RGB")

    # Small pale tears; keep the covered area limited.
    if rng.random() < 0.45:
        mask = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(mask)
        for _ in range(rng.randint(1, 3)):
            x, y = rng.randrange(width), rng.randrange(height)
            rx, ry = rng.randint(3, max(4, width // 18)), rng.randint(3, max(4, height // 18))
            draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=(220, 204, 171, 210))
        image = Image.alpha_composite(image.convert("RGBA"), mask).convert("RGB")
    return image

"""Restore photos at their original size with bounded GPU memory."""
import argparse
from functools import lru_cache
from itertools import islice, product
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from torchvision.transforms import functional as TF

from .model import Generator
from .runtime import get_device


def load_generator(checkpoint, device=None):
    device = get_device() if device is None else torch.device(device)
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    model = Generator().to(device)
    model.load_state_dict(state.get("generator", state))
    return model.eval()


def _positions(length, tile, overlap):
    return list(range(0, max(1, length - tile + 1), tile - overlap)) + ([length - tile] if length > tile and (length - tile) % (tile - overlap) else [])


@lru_cache(maxsize=16)
def _window(height, width):
    return np.maximum(np.outer(np.hanning(height), np.hanning(width)), 0.01).astype(np.float32)


@torch.inference_mode()
def restore_image(image, model, device=None, tile_size=256, overlap=32, refine=False):
    if not isinstance(image, Image.Image):
        raise ValueError("Provide a readable image.")
    if tile_size < 32 or tile_size % 16 or overlap < 0 or overlap >= tile_size:
        raise ValueError("tile_size must be >=32 and divisible by 16; overlap must be smaller than tile_size.")
    device = next(model.parameters()).device if device is None else torch.device(device)
    if image.width * image.height > 25_000_000:
        raise ValueError("Resize photos to at most 25 megapixels before restoring.")
    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    pixels = TF.to_tensor(image)
    output = np.zeros((3, height, width), dtype=np.float32)
    weights = np.zeros((height, width), dtype=np.float32)
    model.eval()

    h, w = min(height, tile_size), min(width, tile_size)
    pad = (0, max(32, (w + 15) // 16 * 16) - w, 0, max(32, (h + 15) // 16 * 16) - h)
    window = _window(h, w)
    positions = product(_positions(height, tile_size, overlap), _positions(width, tile_size, overlap))
    batch_size = 4 if device.type in ("cuda", "mps") and tile_size <= 256 else 1
    while batch := list(islice(positions, batch_size)):
        patches = torch.stack([pixels[:, y:y+h, x:x+w] for y, x in batch]).to(device)
        if any(pad):
            patches = torch.nn.functional.pad(patches, pad, mode="replicate")
        prediction = model(patches)
        if refine:
            for axes in ((-1,), (-2,), (-2, -1)):
                prediction += model(patches.flip(axes)).flip(axes)
            prediction /= 4
        restored = prediction[:, :, :h, :w].cpu().numpy()
        for (y, x), tile in zip(batch, restored):
            output[:, y:y+h, x:x+w] += tile * window
            weights[y:y+h, x:x+w] += window
    output /= weights[None]
    return Image.fromarray(np.uint8(np.clip(output.transpose(1, 2, 0) * 255, 0, 255).round()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda", "mps"))
    args = parser.parse_args(argv)
    source, output = Path(args.input), Path(args.output)
    if not source.is_file() or not Path(args.checkpoint).is_file():
        parser.error("Input image and checkpoint must exist.")
    if source.resolve() == output.resolve() or output.exists():
        parser.error("Choose a new output filename to preserve existing photos.")
    model = load_generator(args.checkpoint, get_device(args.device))
    with Image.open(source) as image:
        restored = restore_image(image, model)
    output.parent.mkdir(parents=True, exist_ok=True)
    restored.save(output)
    print(f"Saved {output}")


if __name__ == "__main__":
    main()

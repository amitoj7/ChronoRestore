"""Deterministic paired augmentation, with separate training and validation images."""
from pathlib import Path
import random

from PIL import Image, ImageOps
from torch.utils.data import Dataset
from torchvision.transforms import functional as TF
from .degradation import degrade

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def image_paths(root):
    paths = sorted(p.resolve() for p in Path(root).rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS)
    if not paths:
        raise ValueError(f"No images found in {root}. Add clean photos first.")
    return paths


class PhotoDataset(Dataset):
    def __init__(self, paths, size=256, training=True, seed=17):
        self.paths = image_paths(paths) if isinstance(paths, (str, Path)) else list(paths)
        if not self.paths:
            raise ValueError("Image list is empty.")
        self.size, self.training, self.seed, self.epoch = size, training, seed, 0

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        rng = random.Random(self.seed + index + (self.epoch * len(self) if self.training else 0))
        try:
            with Image.open(self.paths[index]) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
        except (OSError, ValueError) as exc:
            raise ValueError(f"Cannot read image {self.paths[index]}: {exc}") from exc
        image = TF.resize(image, self.size + (32 if self.training else 0))
        if self.training:
            w, h = image.size
            image = TF.crop(image, rng.randint(0, h - self.size), rng.randint(0, w - self.size), self.size, self.size)
            if rng.random() < 0.5:
                image = TF.hflip(image)
        else:
            image = TF.center_crop(image, self.size)
        return TF.to_tensor(degrade(image, rng.randrange(2**32))), TF.to_tensor(image)

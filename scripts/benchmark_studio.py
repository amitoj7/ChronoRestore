"""Compare the shipped checkpoint's inference modes on the same BSDS500 images."""
from pathlib import Path
import json
import statistics
from time import perf_counter

from PIL import Image, ImageFilter, ImageOps
from torchvision.transforms import functional as TF

from chronorestore.data import image_paths
from chronorestore.degradation import degrade
from chronorestore.evaluate import scores
from chronorestore.restore import load_generator, restore_image


def main():
    paths = image_paths("data/bsds500/test")
    model = load_generator("runs/caltech256_256px/best.pt")
    methods = ("Damaged input", "Median + autocontrast", "Standard", "Refine")
    rows = {method: [] for method in methods}
    for i, path in enumerate(paths):
        with Image.open(path) as source:
            target = TF.center_crop(TF.resize(source.convert("RGB"), 256), 256)
        damaged = degrade(target, 1701 + i)
        operations = (
            lambda: damaged,
            lambda: ImageOps.autocontrast(damaged.filter(ImageFilter.MedianFilter(3))),
            lambda: restore_image(damaged, model),
            lambda: restore_image(damaged, model, refine=True),
        )
        for name, operation in zip(methods, operations):
            start = perf_counter()
            result = operation()
            elapsed = perf_counter() - start
            psnr, ssim = scores(result, target)
            rows[name].append((psnr, ssim, elapsed))
    summary = []
    for name, values in rows.items():
        psnr, ssim, elapsed = zip(*values)
        summary.append(dict(method=name, psnr=statistics.mean(psnr), ssim=statistics.mean(ssim),
                            median_ms=statistics.median(elapsed[1:]) * 1000))
    wins = {metric: sum(a[index] > b[index] for a, b in zip(rows["Refine"], rows["Standard"]))
            for index, metric in enumerate(("psnr", "ssim"))}
    report = dict(dataset="BSDS500 test split", count=len(paths), crop=256, seed=1701,
                  device=str(next(model.parameters()).device), results=summary, refine_wins=wins)
    Path("chronorestore/studio_assets/benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

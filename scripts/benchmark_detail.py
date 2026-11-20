"""Compare baseline and detail checkpoint on paired, held-out BSDS500 images."""
import json
from pathlib import Path
from statistics import mean

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from torchvision.transforms import functional as TF

from chronorestore.data import image_paths
from chronorestore.degradation import degrade
from chronorestore.evaluate import scores
from chronorestore.restore import load_generator, restore_image


def comparison_sheet(output, rows):
    """Show the first three examples in test order, with per-image scores."""
    labels = ("Damaged input", "Original + Refine", "Detail + Refine", "Clean reference")
    sheet = Image.new("RGB", (1104, 1008), "#f1ebe0")
    draw = ImageDraw.Draw(sheet)
    heading, label = (ImageFont.load_default(size=size) for size in (29, 16))
    draw.text((24, 18), "ChronoRestore | Paired test examples", fill="#241a15", font=heading)
    draw.text((24, 56), "First three BSDS500 test images in sorted order, each with simulated damage.", fill="#674c40", font=label)
    for i, title in enumerate(labels):
        draw.text((24 + i * 268, 91), title, fill="#34251f", font=label)
    for i, row in enumerate(rows[:3]):
        top = 114 + i * 294
        with Image.open(output / f"comparison_{i + 1}.png") as photo:
            for column in range(4):
                sheet.paste(photo.crop((column * 256, 0, (column + 1) * 256, 256)), (24 + column * 268, top))
        for column, method in enumerate(("Input", "Original + Refine", "Detail + Refine")):
            stats = row["results"][method]
            draw.text((24 + column * 268, top + 261),
                      f'{stats["psnr"]:.2f} dB / SSIM {stats["ssim"]:.3f}', fill="#4b382e", font=label)
        draw.text((828, top + 261), f'Target: {row["image"]}', fill="#4b382e", font=label)
    sheet.save(output / "paired_comparison.png")


def main():
    original = load_generator("runs/caltech256_256px/best.pt")
    detail = load_generator("runs/detail_finetune/best.pt")
    output = Path("evaluation_detail")
    output.mkdir(exist_ok=True)
    methods = ("Input", "Median + autocontrast", "Original", "Original + Refine",
               "Detail", "Detail + Refine")
    images = []
    paths = image_paths("data/bsds500/test")
    for index, path in enumerate(paths):
        with Image.open(path) as source:
            clean = TF.center_crop(TF.resize(source.convert("RGB"), 256), 256)
        damaged = degrade(clean, 1701 + index)
        outputs = (
            damaged,
            ImageOps.autocontrast(damaged.filter(ImageFilter.MedianFilter(3))),
            restore_image(damaged, original),
            restore_image(damaged, original, refine=True),
            restore_image(damaged, detail),
            restore_image(damaged, detail, refine=True),
        )
        clean_pixels = np.asarray(clean, dtype=np.float32) / 255
        clean_edges = [np.diff(clean_pixels, axis=axis) for axis in (0, 1)]
        results = {}
        for method, image in zip(methods, outputs):
            psnr, ssim = scores(image, clean)
            pixels = np.asarray(image, dtype=np.float32) / 255
            edge_mae = mean(float(np.abs(np.diff(pixels, axis=axis) - clean_edges[axis]).mean())
                            for axis in (0, 1))
            results[method] = {"psnr": psnr, "ssim": ssim, "edge_mae": edge_mae}
        images.append({"image": path.name, "results": results})
        if index < 6:
            gallery = Image.new("RGB", (4 * 256, 256))
            for column, image in enumerate((damaged, outputs[3], outputs[5], clean)):
                gallery.paste(image, (column * 256, 0))
            gallery.save(output / f"comparison_{index + 1}.png")
    summary = {method: {key: mean(row["results"][method][key] for row in images)
                        for key in ("psnr", "ssim", "edge_mae")} for method in methods}
    wins = {key: sum(row["results"]["Detail + Refine"][key] > row["results"]["Original + Refine"][key]
                     for row in images) for key in ("psnr", "ssim")}
    result = {"dataset": "BSDS500 test", "count": len(paths), "crop": 256, "seed": 1701,
              "mean": summary, "detail_wins": wins, "images": images}
    (output / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    comparison_sheet(output, images)
    assets = Path("chronorestore/studio_assets")
    (assets / "detail-benchmark.json").write_bytes((output / "metrics.json").read_bytes())
    with Image.open(output / "paired_comparison.png") as sheet:
        sheet.save(assets / "detail-comparison.webp", quality=91)
    print(json.dumps({"mean": summary, "detail_wins": wins}, indent=2))


if __name__ == "__main__":
    main()

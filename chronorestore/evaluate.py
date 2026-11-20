"""Report paired synthetic PSNR/SSIM on a separate image folder."""
import argparse
import json
from pathlib import Path

import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
from PIL import Image, ImageOps
from torchvision.transforms import functional as TF

from .data import image_paths
from .degradation import degrade
from .restore import load_generator, restore_image
from .runtime import get_device


def scores(prediction, target):
    prediction, target = np.asarray(prediction, dtype=np.float32) / 255, np.asarray(target, dtype=np.float32) / 255
    return (float(peak_signal_noise_ratio(target, prediction, data_range=1)),
            float(structural_similarity(target, prediction, data_range=1, channel_axis=-1)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--data", required=True, help="Held-out images; never use the training folder")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--size", type=int, default=128)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--output", default="evaluation")
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda", "mps"))
    args = parser.parse_args(argv)
    if args.count < 1 or args.size < 32:
        parser.error("count must be positive and size must be >=32")
    paths = image_paths(args.data)[:args.count]
    manifest = Path(args.checkpoint).parent / "split.json"
    if manifest.is_file():
        used = json.loads(manifest.read_text())["train"]
        if set(map(str, paths)) & set(used):
            parser.error("Evaluation contains training images. Choose a held-out folder.")
    model = load_generator(args.checkpoint, get_device(args.device))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, path in enumerate(paths):
        with Image.open(path) as image:
            clean = TF.center_crop(TF.resize(ImageOps.exif_transpose(image).convert("RGB"), args.size), args.size)
        damaged = degrade(clean, args.seed + i)
        restored = restore_image(damaged, model)
        before, after = scores(damaged, clean), scores(restored, clean)
        rows.append({"image": str(path), "input_psnr": before[0], "input_ssim": before[1], "restored_psnr": after[0], "restored_ssim": after[1]})
        if i < 6:
            gallery = Image.new("RGB", (args.size * 3, args.size))
            for column, photo in enumerate((damaged, restored, clean)):
                gallery.paste(photo, (column * args.size, 0))
            gallery.save(output / f"comparison_{i+1}.png")
    report = {"count": len(rows), "seed": args.seed, "size": args.size,
              "mean": {key: float(np.mean([row[key] for row in rows])) for key in rows[0] if key != "image"}, "images": rows}
    (output / "metrics.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report["mean"], indent=2))
    print(f"Saved metrics and galleries (damaged / restored / clean) to {output}. Synthetic benchmark only.")


if __name__ == "__main__":
    main()

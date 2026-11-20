"""Prepare a reproducible 5,000-image training set from official Caltech256."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import random
import tarfile
import urllib.request

from PIL import Image, ImageOps

URL = "https://data.caltech.edu/records/nyy15-4j048/files/256_ObjectCategories.tar"
MD5 = "67b4f42ca05d46448c6bb8ecd2220f6d"


def prepare(destination="data/caltech256_restoration"):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    marker = root / "manifest.json"
    if marker.is_file():
        manifest = json.loads(marker.read_text())
        if all((root / row["path"]).is_file() for row in manifest["images"]):
            print(f"Dataset already prepared: {root}", flush=True)
            return root
    archive = root / "256_ObjectCategories.tar"
    if not archive.is_file():
        temporary = archive.with_suffix(".part")
        print("Downloading Caltech256 (about 1.2 GB) from the official repository...", flush=True)
        with urllib.request.urlopen(urllib.request.Request(URL + "?download=1", headers={"User-Agent": "curl/8.7.1"}), timeout=120) as response, temporary.open("wb") as target:
            downloaded = 0
            while chunk := response.read(4 * 1024 * 1024):
                target.write(chunk)
                downloaded += len(chunk)
                if downloaded % (64 * 1024 * 1024) == 0:
                    print(f"Downloaded {downloaded // (1024 * 1024)} MiB", flush=True)
        temporary.replace(archive)
    digest = hashlib.md5()
    with archive.open("rb") as source:
        while chunk := source.read(4 * 1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != MD5:
        raise RuntimeError("Archive checksum mismatch. Remove the incomplete archive and retry.")
    rows, seen = [], set()
    for split in ("train", "val", "test"):
        (root / split).mkdir(exist_ok=True)
    with tarfile.open(archive) as bundle:
        members = [member for member in bundle.getmembers() if member.isfile() and member.name.lower().endswith('.jpg')]
        random.Random(17).shuffle(members)
        for member in members:
            try:
                with bundle.extractfile(member) as stream, Image.open(BytesIO(stream.read())) as source:
                    image = ImageOps.exif_transpose(source).convert('RGB')
                    w, h = image.size
                    if min(w, h) < 256 or max(w, h) / min(w, h) > 3:
                        continue
                    scale = 320 / min(w, h)
                    image = image.resize((round(w * scale), round(h * scale)), Image.Resampling.LANCZOS)
            except (OSError, ValueError):
                continue
            fingerprint = hashlib.sha256(image.tobytes()).hexdigest()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            split = "train" if len(rows) < 5000 else "val" if len(rows) < 5500 else "test"
            relative = Path(split) / f"{len(rows):05d}.jpg"
            image.save(root / relative, quality=95)
            rows.append({"path": str(relative), "source": member.name, "pixel_sha256": fingerprint})
            if len(rows) % 500 == 0:
                print(f"Prepared {len(rows)}/6000 photos", flush=True)
            if len(rows) == 6000:
                break
    if len(rows) != 6000:
        raise RuntimeError(f"Only {len(rows)} eligible photos found; refusing an incomplete split.")
    marker.write_text(json.dumps({"source": URL, "archive_md5": MD5, "seed": 17, "counts": {"train": 5000, "val": 500, "test": 500}, "images": rows}, indent=2))
    print(f"Ready: {root} — 5000 train, 500 validation, 500 test", flush=True)
    return root


if __name__ == "__main__":
    prepare()

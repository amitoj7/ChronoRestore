"""Download the official BSDS500 starter dataset, retaining its image splits."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tarfile
import urllib.request

URL = "https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/BSR/BSR_bsds500.tgz"


def download(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "BSR_bsds500.tgz"
    if not archive.is_file():
        temporary = archive.with_suffix(".part")
        print(f"Downloading {URL}", flush=True)
        with urllib.request.urlopen(URL, timeout=60) as response, temporary.open("wb") as target:
            shutil.copyfileobj(response, target)
        temporary.replace(archive)
    counts = {split: 0 for split in ("train", "val", "test")}
    with tarfile.open(archive) as bundle:
        for member in bundle:
            parts = Path(member.name).parts
            if member.isfile() and len(parts) >= 3 and parts[-3] == "images" and parts[-2] in counts and Path(parts[-1]).suffix.lower() == ".jpg":
                split, name = parts[-2:]
                folder = destination / split
                folder.mkdir(exist_ok=True)
                with bundle.extractfile(member) as source, (folder / name).open("wb") as target:
                    shutil.copyfileobj(source, target)
                counts[split] += 1
    if counts != {"train": 200, "val": 100, "test": 200}:
        raise RuntimeError(f"Unexpected BSDS500 image counts: {counts}. Check the downloaded archive.")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (destination / "SOURCE.txt").write_text(f"Source: {URL}\nSHA256: {digest}\nCitation: Arbelaez et al., Contour Detection and Hierarchical Image Segmentation, TPAMI 2011.\n")
    print(f"Ready: {destination} — {counts}", flush=True)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/bsds500")
    download(parser.parse_args().output)

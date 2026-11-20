"""Export the trained Detail generator for ONNX Runtime Web."""
import argparse
from pathlib import Path

import torch

from chronorestore.restore import load_generator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path, default=Path("web/models/detail.onnx"))
    args = parser.parse_args()
    model = load_generator(args.checkpoint, "cpu")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model, torch.zeros(1, 3, 256, 256), args.output,
        input_names=["photo"], output_names=["restoration"],
        dynamic_axes={name: {2: "height", 3: "width"} for name in ("photo", "restoration")},
        opset_version=17, dynamo=False,
    )


if __name__ == "__main__":
    main()

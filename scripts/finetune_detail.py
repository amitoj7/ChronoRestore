"""Fine-tune the Caltech generator for color accuracy and edge fidelity."""
import argparse
import csv
from pathlib import Path

import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader

from chronorestore.data import PhotoDataset
from chronorestore.restore import load_generator
from chronorestore.train import atomic_save


def detail_loss(prediction, target):
    color = F.l1_loss(prediction, target)
    edge_x = F.l1_loss(prediction.diff(dim=-1), target.diff(dim=-1))
    edge_y = F.l1_loss(prediction.diff(dim=-2), target.diff(dim=-2))
    return color + 0.4 * (edge_x + edge_y) / 2


@torch.inference_mode()
def validation_loss(model, batches, device):
    model.eval()
    return sum(F.mse_loss(model(x.to(device)), y.to(device)).item() * len(x)
               for x, y in batches) / len(batches.dataset)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path("runs/detail_finetune"))
    args = parser.parse_args()
    if args.epochs < 1 or args.output.exists():
        parser.error("Use a positive epoch count and a new output directory.")
    torch.manual_seed(17)
    torch.set_num_threads(2)
    source = Path("runs/caltech256_256px/best.pt")
    model = load_generator(source)
    device = next(model.parameters()).device
    train = PhotoDataset("data/bsds500/train", size=256, seed=17)
    val = PhotoDataset("data/bsds500/val", size=256, training=False, seed=100017)
    train_batches = DataLoader(train, batch_size=4, shuffle=True)
    val_batches = DataLoader(val, batch_size=4)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.000035)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=0.000007)
    args.output.mkdir(parents=True)
    with (args.output / "losses.csv").open("w", newline="") as file:
        log = csv.writer(file)
        log.writerow(["epoch", "val_mse"])
        best = validation_loss(model, val_batches, device)
        log.writerow([0, best])
        print(f"Initial validation MSE {best:.6f} ({device})", flush=True)
        for epoch in range(1, args.epochs + 1):
            train.epoch = epoch
            model.train()
            for damaged, clean in train_batches:
                optimizer.zero_grad(set_to_none=True)
                loss = detail_loss(model(damaged.to(device)), clean.to(device))
                loss.backward()
                optimizer.step()
            scheduler.step()
            mse = validation_loss(model, val_batches, device)
            log.writerow([epoch, mse])
            file.flush()
            if mse < best:
                best = mse
                atomic_save({"generator": model.state_dict(), "epoch": epoch, "val_mse": mse,
                             "initial_checkpoint": str(source)}, args.output / "best.pt")
            print(f"Epoch {epoch:02d} validation MSE {mse:.6f} (best {best:.6f})", flush=True)


if __name__ == "__main__":
    main()

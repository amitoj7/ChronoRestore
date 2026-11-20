"""Train, validate, and resume the compact restoration GAN."""
import argparse
import csv
import json
import math
from pathlib import Path
import random

import torch
from torch import nn
from torch.utils.data import DataLoader

from .data import PhotoDataset, image_paths
from .model import Discriminator, Generator
from .runtime import get_device


def atomic_save(state, path):
    temporary = path.with_suffix(".tmp")
    torch.save(state, temporary)
    temporary.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/clean")
    parser.add_argument("--val-data", help="Separate validation folder; otherwise reserve 10%% of data")
    parser.add_argument("--output", default="runs")
    parser.add_argument("--epochs", type=int, default=30, help="Total epochs, including resumed epochs")
    parser.add_argument("--size", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda", "mps"))
    parser.add_argument("--resume", help="Path to latest.pt from an interrupted run")
    parser.add_argument("--warmup-epochs", type=int, default=2)
    parser.add_argument("--gan-weight", type=float, default=0.01)
    parser.add_argument("--patience", type=int, default=0, help="Stop after this many epochs without validation improvement; 0 disables")
    args = parser.parse_args(argv)
    if args.epochs < 1 or args.batch_size < 1 or args.size < 32 or args.size % 16:
        parser.error("epochs and batch-size must be positive; size must be >=32 and divisible by 16")
    if args.patience < 0 or args.warmup_epochs < 0 or not math.isfinite(args.gan_weight) or args.gan_weight < 0:
        parser.error("patience, warmup-epochs and gan-weight must be nonnegative")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = get_device(args.device)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if not args.resume and any((output / name).exists() for name in ("latest.pt", "best.pt", "losses.csv")):
        parser.error("Output already contains a run. Use --resume or a different --output.")
    paths = image_paths(args.data)
    if args.val_data:
        train_paths, val_paths = paths, image_paths(args.val_data)
        if set(train_paths) & set(val_paths):
            parser.error("Training and validation folders overlap.")
    else:
        if len(paths) < 2:
            parser.error("Need at least two images to separate training and validation.")
        random.Random(args.seed).shuffle(paths)
        n_val = max(1, len(paths) // 10)
        val_paths, train_paths = paths[:n_val], paths[n_val:]
    split = {"train": [str(p) for p in train_paths], "validation": [str(p) for p in val_paths]}
    train_data = PhotoDataset(train_paths, args.size, True, args.seed)
    val_data = PhotoDataset(val_paths, args.size, False, args.seed + 100000)
    shuffle_rng = torch.Generator()
    loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True, generator=shuffle_rng, num_workers=0)
    val_loader = DataLoader(val_data, batch_size=args.batch_size, num_workers=0)
    generator, discriminator = Generator().to(device), Discriminator().to(device)
    opt_g = torch.optim.Adam(generator.parameters(), lr=1e-4, betas=(0.5, 0.999))
    opt_d = torch.optim.Adam(discriminator.parameters(), lr=4e-4, betas=(0.5, 0.999))
    l1, bce = nn.L1Loss(), nn.BCEWithLogitsLoss()
    start, best, history = 1, float("inf"), []
    config = {key: getattr(args, key) for key in ("size", "seed", "batch_size", "warmup_epochs", "gan_weight")}
    if args.resume:
        state = torch.load(args.resume, map_location=device, weights_only=True)
        if state.get("config") != config or state.get("split") != split:
            parser.error("Resume requires the same dataset paths, size, seed, batch size, warmup, and GAN weight.")
        generator.load_state_dict(state["generator"])
        discriminator.load_state_dict(state["discriminator"])
        opt_g.load_state_dict(state["optimizer_g"])
        opt_d.load_state_dict(state["optimizer_d"])
        start, best, history = state["epoch"] + 1, state["best_val_l1"], state["history"]
    (output / "split.json").write_text(json.dumps(split, indent=2))
    print(f"Device: {device} | train: {len(train_data)} | validation: {len(val_data)}", flush=True)
    for epoch in range(start, args.epochs + 1):
        train_data.epoch = epoch
        shuffle_rng.manual_seed(args.seed + epoch)
        generator.train()
        totals = [0.0, 0.0, 0.0]
        adversarial = epoch > args.warmup_epochs and args.gan_weight > 0
        for step, (damaged, clean) in enumerate(loader, 1):
            damaged, clean = damaged.to(device), clean.to(device)
            restored = generator(damaged)
            d_loss = torch.zeros((), device=device)
            if adversarial:
                discriminator.train().requires_grad_(True)
                opt_d.zero_grad(set_to_none=True)
                real_logits = discriminator(damaged, clean)
                fake_logits = discriminator(damaged, restored.detach())
                d_loss = (bce(real_logits, torch.full_like(real_logits, 0.95)) + bce(fake_logits, torch.zeros_like(fake_logits))) / 2
                if not torch.isfinite(d_loss):
                    raise RuntimeError("Non-finite discriminator loss; previous checkpoint is preserved.")
                d_loss.backward()
                opt_d.step()
            opt_g.zero_grad(set_to_none=True)
            pixel_loss = l1(restored, clean)
            g_loss = pixel_loss
            if adversarial:
                discriminator.eval().requires_grad_(False)
                logits = discriminator(damaged, restored)
                g_loss = g_loss + args.gan_weight * bce(logits, torch.ones_like(logits))
            if not torch.isfinite(g_loss):
                raise RuntimeError("Non-finite generator loss; previous checkpoint is preserved.")
            g_loss.backward()
            opt_g.step()
            for i, loss in enumerate((g_loss, d_loss, pixel_loss)):
                totals[i] += loss.item() * len(clean)
            if step == 1 or step % 100 == 0:
                print(f"Epoch {epoch:03d} | batch {step}/{len(loader)} | L1 {pixel_loss.item():.4f}", flush=True)
        generator.eval()
        val_loss = 0.0
        with torch.inference_mode():
            for damaged, clean in val_loader:
                val_loss += l1(generator(damaged.to(device)), clean.to(device)).item() * len(clean)
        val_loss /= len(val_data)
        if not math.isfinite(val_loss):
            raise RuntimeError("Non-finite validation loss; previous checkpoint is preserved.")
        row = {"epoch": epoch, "g_loss": totals[0] / len(train_data), "d_loss": totals[1] / len(train_data), "train_l1": totals[2] / len(train_data), "val_l1": val_loss}
        history.append(row)
        improved = val_loss < best
        best = min(best, val_loss)
        state = {"generator": generator.state_dict(), "discriminator": discriminator.state_dict(), "optimizer_g": opt_g.state_dict(), "optimizer_d": opt_d.state_dict(), "epoch": epoch, "config": config, "split": split, "history": history, "best_val_l1": best}
        atomic_save(state, output / "latest.pt")
        if improved:
            atomic_save({"generator": generator.state_dict(), "epoch": epoch, "config": config, "val_l1": val_loss}, output / "best.pt")
        with (output / "losses.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row))
            writer.writeheader()
            writer.writerows(history)
        print(f"Epoch {epoch:03d}/{args.epochs} | train L1 {row['train_l1']:.4f} | val L1 {val_loss:.4f} | GAN {'on' if adversarial else 'warmup'}", flush=True)
        best_epoch = min(history, key=lambda record: record["val_l1"])["epoch"]
        if args.patience and epoch - best_epoch >= args.patience:
            print(f"Early stopping: best validation was epoch {best_epoch}.", flush=True)
            break
    print(f"Checkpoints: {output}", flush=True)


if __name__ == "__main__":
    main()

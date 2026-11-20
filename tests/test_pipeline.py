"""Regression checks for the complete training-to-restoration path."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image
import torch

from chronorestore.data import PhotoDataset
from chronorestore.degradation import degrade
from chronorestore.model import Generator, Discriminator
from chronorestore.restore import load_generator, restore_image, main as restore_main
from chronorestore.train import main as train_main
from chronorestore.evaluate import main as evaluate_main


def photo(seed, size=(48, 40)):
    pixels = np.random.default_rng(seed).integers(0, 256, (*size[::-1], 3), dtype=np.uint8)
    return Image.fromarray(pixels)


class Identity(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(1.0))

    def forward(self, x):
        return x * self.weight


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_degradation_is_repeatable_and_preserves_input(self):
        image = photo(1)
        original = np.array(image)
        a, b = degrade(image, 17), degrade(image, 17)
        np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(image, original)
        self.assertEqual(a.size, image.size)
        self.assertFalse(np.array_equal(a, original))

    def test_models_support_training_patch_sizes(self):
        generator, discriminator = Generator(), Discriminator()
        for size in (32, 64, 128):
            x = torch.rand(1, 3, size, size)
            y = generator(x)
            self.assertEqual(y.shape, x.shape)
            self.assertTrue(torch.isfinite(discriminator(x, y)).all())

    def test_tiling_preserves_every_pixel_including_tiny_images(self):
        for size in ((1, 1), (7, 3), (31, 17), (64, 65), (189, 97)):
            image = photo(2, size)
            restored = restore_image(image, Identity(), tile_size=64, overlap=16)
            np.testing.assert_array_equal(image, restored)

    def test_inference_rejects_invalid_settings(self):
        with self.assertRaises(ValueError):
            restore_image(None, Identity())
        for tile, overlap in ((15, 0), (64, 64), (64, -1)):
            with self.assertRaises(ValueError):
                restore_image(photo(1), Identity(), tile_size=tile, overlap=overlap)

    def test_dataset_reports_corrupt_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "broken.jpg"
            path.write_text("not an image")
            with self.assertRaisesRegex(ValueError, "broken.jpg"):
                PhotoDataset(root)[0]

    def test_early_stopping_saves_the_last_and_best_epochs(self):
        from unittest.mock import patch

        class ConstantLoss(torch.nn.Module):
            def forward(self, prediction, target):
                return prediction.sum() * 0 + 1

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "photos"
            data.mkdir()
            for i in range(3):
                photo(i).save(data / f"{i}.png")
            with patch("chronorestore.train.nn.L1Loss", return_value=ConstantLoss()):
                train_main(["--data", str(data), "--output", str(root / "run"), "--epochs", "5", "--patience", "1", "--gan-weight", "0", "--size", "32", "--device", "cpu"])
            state = torch.load(root / "run/latest.pt", weights_only=True)
            best = torch.load(root / "run/best.pt", weights_only=True)
            self.assertEqual(state["epoch"], 2)
            self.assertEqual(best["epoch"], 1)

    def test_train_resume_restore_evaluate_and_demo(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            train, val, test = (root / split for split in ("train", "val", "test"))
            for folder in (train, val, test):
                folder.mkdir()
                for i in range(2):
                    photo(i + len(str(folder))).save(folder / f"{i}.png")
            run, uninterrupted = root / "run", root / "uninterrupted"
            common = ["--data", str(train), "--val-data", str(val), "--size", "32", "--batch-size", "2", "--device", "cpu", "--warmup-epochs", "0"]
            train_main(common + ["--output", str(run), "--epochs", "1"])
            train_main(common + ["--output", str(run), "--epochs", "2", "--resume", str(run / "latest.pt")])
            train_main(common + ["--output", str(uninterrupted), "--epochs", "2"])
            resumed = torch.load(run / "latest.pt", weights_only=True)
            complete = torch.load(uninterrupted / "latest.pt", weights_only=True)
            self.assertEqual(resumed["epoch"], 2)
            self.assertEqual(len(resumed["history"]), 2)
            for name, weights in resumed["generator"].items():
                torch.testing.assert_close(weights, complete["generator"][name], atol=0, rtol=0)
            model = load_generator(run / "best.pt", "cpu")
            self.assertEqual(restore_image(photo(3, (17, 19)), model).size, (17, 19))
            result = root / "restored.png"
            restore_main(["--checkpoint", str(run / "best.pt"), "--input", str(test / "0.png"), "--output", str(result), "--device", "cpu"])
            self.assertTrue(result.is_file())
            with self.assertRaises(SystemExit):
                restore_main(["--checkpoint", str(run / "best.pt"), "--input", str(test / "0.png"), "--output", str(result)])
            evaluation = root / "evaluation"
            evaluate_main(["--checkpoint", str(run / "best.pt"), "--data", str(test), "--output", str(evaluation), "--size", "32", "--device", "cpu"])
            report = json.loads((evaluation / "metrics.json").read_text())
            self.assertEqual(report["count"], 2)
            self.assertTrue(all(np.isfinite(v) for v in report["mean"].values()))
            with self.assertRaises(SystemExit):
                evaluate_main(["--checkpoint", str(run / "best.pt"), "--data", str(train)])
            with self.assertRaises(SystemExit):
                train_main(common + ["--output", str(run)])
            from chronorestore.demo import create_app
            app = create_app(run / "best.pt")
            self.assertTrue(app.config["components"])


if __name__ == "__main__":
    unittest.main()

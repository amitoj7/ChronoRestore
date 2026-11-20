# Verification — 16 October 2026

## Environments exercised

- Local macOS ARM64, Python 3.12, Torch 2.14.1, Torchvision 0.29.1, Gradio 6.30.0. Dependency consistency check passed.
- Google Colab Python 3, Tesla T4, Torch 2.11.0+cu130, Torchvision 0.26.0+cu130.
- Live notebook: https://colab.research.google.com/drive/1ssIPq8oVkAbmSdqE-bZ7N9BhILGmpL7O

## Checks completed

All six regression cases passed locally and in Colab. They cover deterministic degradation, unreadable image errors, generator/discriminator patch sizes, tiny and tiled image boundary handling, invalid settings, and an integrated training/resume/restoration/evaluation/demo flow. The integration case compares resumed generator weights with an uninterrupted run exactly, exercises adversarial backward passes, rejects output overwrites and training-set evaluation, and constructs the demo.

A full 30-epoch CUDA run completed on the official BSDS500 image splits with 128-pixel crops, batch size 8, two warmup epochs, and seed 17. Checkpoint loading through the Colab resume command succeeded after completion. No extra epochs were needed or run for that check.

The trained checkpoint was downloaded and loaded by the local Gradio server. A client uploaded a 481 × 321 synthetic damaged image, invoked restoration through the running server, and received a valid PNG with the same dimensions. Example files are in `examples/`. The visible browser flow was also exercised: upload the sample through the file chooser, click Restore photo, and confirm the output image and download link appeared. A full-page screenshot is saved as `docs/demo-screenshot.jpg`. Both notebook source cells and ZIP archive integrity were checked.

## Recorded benchmark

Model selection used validation L1 only. The selected checkpoint is epoch 28 (validation L1 0.065344). Evaluation used the 200 separate BSDS500 test images, 128-pixel center crops, and damage seed 1701.

| Metric | Damaged input | Restored output |
| --- | ---: | ---: |
| Mean PSNR (dB) | 18.6566 | 21.4322 |
| Mean SSIM | 0.688835 | 0.723443 |

`evaluation/metrics.json` contains every image score; `runs/bsds500/losses.csv` contains all 30 epochs. The benchmark was rerun unchanged to verify visible notebook output, with identical results. No test scores were used to choose a new training configuration.

These checks establish the exercised pipeline works. They do not guarantee all possible inputs, future dependency releases, or future Colab sessions will be error-free. Real historical scans were not used for training or quantitative evaluation. Some scratches and missing detail remain; this checkpoint is a starter model, not a finished archival restoration system.

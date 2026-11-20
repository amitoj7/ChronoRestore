# Completed larger training run

30 epochs, 5000 training images, 500 validation images, 256px crops, batch 4 on Tesla T4. Best checkpoint: epoch 28 (validation L1 0.035889).

500 held-out synthetic test images: PSNR 18.54 → 26.37 dB; SSIM 0.7305 → 0.8199. These scores are not directly comparable with the starter benchmark because the test dataset and crop size differ. Real historical photo and face quality still needs review.

Launch the improved demo from the project directory:
```sh
CHRONORESTORE_CHECKPOINT=runs/caltech256_256px/best.pt python -m chronorestore.demo
```

The original starter weights are preserved in runs/bsds500. The completed results are saved locally in ChronoRestore_256px_results.zip.

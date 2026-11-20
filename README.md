# ChronoRestore

A compact old-photo restoration GAN: synthetic aging and damage → U-Net restoration → comparison with the original. The project includes training, resumable checkpoints, held-out evaluation, image restoration, and a local restoration studio.

## Hosted studio

The Vercel build serves the archive and workbench as a static site. The trained Detail model runs in a browser worker with ONNX Runtime Web. Both Standard and Refine are available, and photos stay on the device. The hosted workbench accepts JPG, PNG and WebP files up to 24 MB and 2 megapixels. The Python studio supports larger images.

Run `npm ci && npm run build` to generate the static site in `dist/`. The included Vercel configuration serves the studio at `/workbench`. To regenerate the deployed model from a local checkpoint, install the `onnx` export dependency, then run `python -m scripts.export_web_model runs/detail_finetune/best.pt`.

## Ready-to-use larger model

The ready bundle includes the completed 5,000-image, 256px training run. All 30 epochs finished; epoch 28 had the best validation loss. On 500 held-out synthetic test images, PSNR improved from 18.54 to 26.37 dB and SSIM from 0.7305 to 0.8199. Real historical-photo quality still needs visual evaluation.

Launch from the project folder:

```bash
python -m chronorestore.demo
```

Open the [ChronoRestore Archive](http://127.0.0.1:7860/) to rotate the photo cube and browse damaged, restored, and clean references. Choose a collection case or open the [restoration studio](http://127.0.0.1:7860/workbench) to upload a JPG, PNG, or WebP image. Choose a file or a BSDS500 dataset sample and the studio automatically opens the live before-and-after slider. Switch between Before and After, or save a PNG copy at the original image size. The studio runs locally and supports up to 24 MB and 25 megapixels per upload.

The studio selects `runs/detail_finetune/best.pt` when present, then falls back to the Caltech256 checkpoint. See [Detail benchmark](docs/QUALITY_BENCHMARK.md) for the paired results displayed in the studio. An explicit checkpoint or `CHRONORESTORE_CHECKPOINT` overrides this choice. The original starter model is preserved. See `docs/LARGER_TRAINING.md`; use `notebooks/ChronoRestore_256px.ipynb` to reproduce the larger run.

## Ready-to-use trained starter

The ready bundle includes `runs/bsds500/best.pt` (selected at epoch 28 from a 30-epoch Tesla T4 run), the resumable `latest.pt`, logs, and `evaluation/metrics.json`. On 200 held-out synthetic examples, mean PSNR improved from 18.66 to 21.43 dB and mean SSIM from 0.689 to 0.723. Some damage remains, and performance on real historical scans is unverified. See `docs/VERIFICATION.md` for exact checks and limits.

After installing the requirements, launch the trained model with:

```bash
CHRONORESTORE_CHECKPOINT=runs/bsds500/best.pt python -m chronorestore.demo
```

On Windows PowerShell, set `$env:CHRONORESTORE_CHECKPOINT="runs/bsds500/best.pt"` before running `python -m chronorestore.demo`.

The archive cube keeps rotating and changes direction over time. Choose Damaged, Restored, or Clean Reference beneath the cube. Drag it or use the arrow keys to change the angle. Press Space while the cube has focus to pause or resume. The desktop site uses a camera pointer with a colored ink trail and click splash. The proof sheet shows the recorded project scores for three individual synthetic test images. Lenis 1.3.27 is served locally on the archive page, with its MIT license in `chronorestore/studio_assets/lenis.LICENSE`. Reduced motion uses native scrolling and disables automatic rotation.

## Original checkpoint benchmark

This earlier experiment compares the same 200 BSDS500 test crops with identical synthetic damage. Median filtering plus autocontrast reached 20.95 dB PSNR and 0.7810 SSIM. Standard reached 25.44 dB and 0.7934. Refine averaged four predictions in flipped orientations and reached 26.03 dB and 0.8232. It improved both metrics on all 200 images relative to Standard. These are synthetic results and provide no comparison to published models on a shared benchmark.

Reproduce with `python -m scripts.benchmark_studio` after downloading BSDS500 and placing the trained Caltech256 checkpoint in `runs/caltech256_256px/best.pt`. The benchmark runs on 256-pixel crops and writes its data to `chronorestore/studio_assets/benchmark.json`. On the measured Apple MPS device, median processing times were 14.7 ms for Standard and 52.5 ms for Refine. Upload, PNG encoding and browser rendering are outside that timing.

## Google Colab training

Open `notebooks/ChronoRestore_Colab.ipynb` in Colab, select **Python 3 / T4 GPU**, and run all cells. The notebook contains the source code, installs its extra dependencies, runs regression checks, downloads the official BSDS500 starter dataset, trains for 30 epochs, evaluates on its test split, and downloads a results ZIP. No source ZIP or personal photos are needed to start.

Defaults: 128-pixel crops, batch size 8, two reconstruction-only warmup epochs, then L1 + adversarial training. These are conservative settings for a free T4. Free GPU availability and session lifetimes are controlled by Colab.

`USE_DRIVE=False` avoids any Drive authorization. Results remain in the current runtime until the final ZIP downloads; an expired/deleted runtime loses them. To persist every epoch to Drive, set `USE_DRIVE=True` and complete Google's Drive authorization yourself. The notebook resumes automatically from `latest.pt` when it exists. Keep configuration and dataset paths the same when resuming.

## Local setup

Use Python 3.10+:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

For Windows, activate with `.venv\Scripts\activate`. For CUDA, install the matching Torch/Torchvision build from [PyTorch](https://pytorch.org/get-started/locally/) first. `--device auto` selects CUDA, then Apple MPS, then CPU.

## Data and training

```bash
python -m chronorestore.download
python -m chronorestore.train --data data/bsds500/train --val-data data/bsds500/val --output runs/bsds500 --epochs 30
```

The [official BSDS500 dataset](https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/resources.html) provides 200 training, 100 validation, and 200 test natural images. It is a small starter dataset, not sufficient evidence of general restoration quality on historical photos. Its original benchmark is image segmentation; our PSNR/SSIM measurements are a separate synthetic restoration experiment.

To use your own photos, supply separate clean training and validation folders. Supported formats: JPG, PNG, WEBP, BMP, TIFF. Without `--val-data`, a seeded 10% split is reserved automatically. Keep duplicates and near-duplicates out of different splits. Evaluation refuses paths used for training. Synthetic aging uses color fading, warm tint, scratches, dust, noise, JPEG artifacts, and small missing regions.

```bash
python -m chronorestore.train --data data/bsds500/train --val-data data/bsds500/val --output runs/bsds500 --epochs 60 --resume runs/bsds500/latest.pt
```

`--epochs` is the total target, not extra epochs. Checkpoints are replaced atomically after each epoch. `latest.pt` includes both networks and optimizers; `best.pt` holds the generator with the lowest validation L1. Existing runs cannot be overwritten accidentally. CSV losses and the image split manifest accompany the checkpoints.

For an L1-only ablation, use a new output folder and `--gan-weight 0`. Keep the same seed, data, crop size, and epoch budget. Larger datasets and a longer run are needed before claiming useful real-photo restoration.

## Evaluate and restore

```bash
python -m chronorestore.evaluate --checkpoint runs/bsds500/best.pt --data data/bsds500/test --output evaluation
python -m chronorestore.restore --checkpoint runs/bsds500/best.pt --input old.jpg --output restored.png
CHRONORESTORE_CHECKPOINT=runs/bsds500/best.pt python -m chronorestore.demo
```

Evaluation saves per-image and mean PSNR/SSIM in `metrics.json`, plus comparisons in **damaged / restored / clean** order. SSIM uses scikit-image with RGB channel handling and a data range of 1. Results depend on the fixed degradation seed, crop size, and dataset. Use validation for tuning and reserve test data for final reporting.

Inference preserves image dimensions, uses overlapping tiles to limit GPU memory, handles tiny images, and refuses to overwrite an existing output. Tiling can cause subtle local inconsistencies because instance normalization is tile-dependent. Images above 25 megapixels must be resized first.

## Scope and limitations

This is an educational baseline inspired by [Bringing Old Photos Back to Life](https://github.com/microsoft/Bringing-Old-Photos-Back-to-Life), not a reproduction of its architecture or published results. It does not perform learned super-resolution, explicit face refinement, or real-photo domain adaptation. The original proposed consistency loop could be satisfied without improving restoration, so it was removed. Large missing areas and identity preservation remain difficult; generated detail is approximate. Keep the original photo.

The code follows the [Ponytail](https://github.com/dietrichgebert/ponytail) preference for a small complete implementation. Tests exercise both networks, deterministic degradation, corrupted-image errors, tiling boundaries, train/resume equivalence, inference, evaluation leakage checks, overwrite protection, and demo construction.

Dataset citation: P. Arbelaez, M. Maire, C. Fowlkes, and J. Malik. *Contour Detection and Hierarchical Image Segmentation*. IEEE TPAMI, 2011. Source URL and the downloaded archive's SHA-256 are recorded in `data/bsds500/SOURCE.txt`.

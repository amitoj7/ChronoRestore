# ChronoRestore Detail benchmark

The original generator corrects much of the fading and color cast, but can leave scratches, soft fur and missing texture. Detail keeps the same architecture and fine-tunes the original Caltech256 checkpoint for ten epochs on 200 BSDS500 training images. The objective adds horizontal and vertical gradient errors to the pixel L1 loss. The 100 validation images select the epoch with the lowest mean squared error. Epoch 10 reduced validation MSE from 0.0029763 to 0.0023648.

## Controlled comparison

All rows use the same 200 BSDS500 test images, 256 × 256 center crops, and identical simulated damage per image. The evaluator uses seed 1701 plus the sorted image index. PSNR and SSIM are measured against known clean targets. Edge MAE averages the direction-wise errors between normalized RGB first differences. Refine averages predictions on the input and three flipped versions after reversing each flip.

| Method | Mean PSNR (dB) ↑ | Mean SSIM ↑ | Edge MAE ↓ |
|---|---:|---:|---:|
| Damaged input | 18.82 | 0.7275 | 0.02584 |
| Median + autocontrast | 20.95 | 0.7810 | 0.02631 |
| Original checkpoint | 25.44 | 0.7934 | 0.02731 |
| Original + Refine | 26.03 | 0.8232 | 0.02379 |
| Detail checkpoint | 26.47 | 0.8394 | 0.02253 |
| **Detail + Refine** | **26.69** | **0.8478** | **0.02182** |

Detail + Refine improved PSNR on 168 images and SSIM on 194 relative to Original + Refine. Mean edge MAE fell by 8.3%. Detail without flips also exceeded Original + Refine on all three mean metrics. This run changed the fine-tuning data and objective together, so it does not isolate the contribution of the gradient term.

## How to use this in the report

> On 200 BSDS500 images with fixed synthetic damage, ChronoRestore Detail + Refine improved mean PSNR from 26.03 to 26.69 dB and mean SSIM from 0.8232 to 0.8478 over the previous Refine checkpoint. Mean edge error decreased by 8.3%. Fine scratches and soft textures remain visible in some outputs.

Use the paired comparison image in `evaluation_detail/paired_comparison.png`. It shows the first three test examples in filename order. The per-image measurements are in `evaluation_detail/metrics.json`. The earlier archive cube and proof-sheet examples still show the original Caltech256 experiment.

Wan et al. reported 23.33 dB and 0.69 SSIM on their synthetically degraded DIV2K benchmark. Xu et al. reported 17.20 dB and 0.758 SSIM for joint restoration and colorization on RealOld. Cite these as related work under their own protocols. A model ranking would require rerunning the methods on the same images and scoring protocol. RealOld access is restricted by the authors. This project did not evaluate real scans or audit cross-dataset near duplicates between Caltech256 and BSDS500.

- [Wan et al., CVPR 2020, Table 1](https://openaccess.thecvf.com/content_CVPR_2020/papers/Wan_Bringing_Old_Photos_Back_to_Life_CVPR_2020_paper.pdf)
- [Xu et al., WACV 2023, Table 2](https://openaccess.thecvf.com/content/WACV2023/papers/Xu_Pik-Fix_Restoring_and_Colorizing_Old_Photos_WACV_2023_paper.pdf)
- [RealOld access in the official repository](https://github.com/DerrickXuNu/Pik-Fix#real-old-photo-data)

## Reproduce

With the original Caltech256 checkpoint and local BSDS500 split installed, run `python -m scripts.finetune_detail` in a checkout without an existing `runs/detail_finetune` directory. Then run `python -m scripts.benchmark_detail`. The studio loads the Detail checkpoint by default.

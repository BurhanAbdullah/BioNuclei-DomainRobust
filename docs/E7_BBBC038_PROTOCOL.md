# E7 — BBBC038 independent external validation protocol

**Status: infrastructure prepared; validation not yet executed.**

## Purpose

E7 is an independent external validation gate for the frozen BioNuclei method. BBBC038v1 stage-1 training data are used because the Broad dataset provides per-nucleus masks and was not used in the BBBC039/S-BIAD634 development sequence.

## Frozen inputs

- **Checkpoint:** the retained E4 checkpoint identified by artifact ID and SHA-256 digest at workflow dispatch time.
- **Dataset:** authoritative Broad BBBC038v1 `stage1_train.zip`.
- **No tuning:** E7 is evaluation-only. No threshold, augmentation, model, preprocessing parameter, or post-processing parameter may be selected using E7 outcomes.

## Deterministic preprocessing

- 2-D images are accepted.
- RGB images are converted to one channel using ITU-R BT.601 luminance coefficients 0.299, 0.587, 0.114.
- Intensities are divided by the 99.5th percentile with a lower bound of 1.0 and clipped to [0, 1], matching the established BioNuclei normalization convention.
- Because the frozen U-Net contains three 2× pooling stages, each spatial dimension is deterministically reflect-padded to the next multiple of 8 when necessary. The prediction is cropped back to the original image shape before any metric is computed; no original image pixels are discarded or resized.
- Each BBBC038 per-nucleus PNG mask is converted to one integer instance label. Overlapping nucleus masks fail the run rather than being silently resolved.
- Predicted instances are obtained from the frozen model's non-background output using 8-connected components, matching the established evaluator.

## Reported endpoints

Image-level means are reported for Dice, IoU, AJI and Boundary-F1, together with per-image instance counts. The checkpoint hash, dataset archive hash, preprocessing definition, exact model-input padding applied per image, and evaluation provenance are retained with the run artifact.

## Integrity rules

1. The checkpoint artifact digest is verified before download.
2. The evaluation fails if the expected checkpoint is absent.
3. The evaluation fails if an image does not have exactly one corresponding image file.
4. The evaluation fails if a mask has the wrong shape or overlaps another nucleus mask.
5. The evaluator records the exact spatial padding used for every image and computes metrics only after cropping the prediction to the original image shape.
6. E7 results remain external-validation evidence and are not used to tune E6 or earlier stages.
7. A successful workflow is not by itself a scientific superiority claim.

## Execution

Use `.github/workflows/e7_bbbc038_external.yml`.

The authoritative BBBC038 source describes stage-1 training as containing images with associated per-nucleus masks and identifies the collection as a diverse benchmark intended to test generalization across biological and imaging variation.

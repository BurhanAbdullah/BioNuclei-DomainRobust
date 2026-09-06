# E6 execution blocker

**Status: EXECUTION-READY — not yet scientifically complete (2026-09-06)**

E6 cannot be declared complete from the currently retained S-BIAD634 evidence. The locked zero-shot evaluation contains all 79 expert-annotated S-BIAD634 image/ground-truth pairs, so those images remain permanently excluded from adaptation.

## Resolution adopted

To preserve the locked S-BIAD634 zero-shot experiment, E6 is explicitly defined as **cross-dataset few-shot adaptation** using the authoritative Aitslab-bioimaging1 fluorescence dataset (Zenodo DOI `10.5281/zenodo.6657260`). Independent published sources describe 50 fluorescence images, more than 2,000 labelled nuclear objects, and a publisher-provided 30/10/10 train/development/test split.

This experiment must never be described as target-domain adaptation to S-BIAD634 and must not reinterpret the locked S-BIAD634 zero-shot result.

## Implemented execution path

- `scripts/download_aitslab_bioimaging1.py` acquires the publisher-provided train/development/test archives from Zenodo and fails closed on missing archives or ambiguous image/annotation pairing.
- `scripts/train_domain_robust.py` accepts `--init-checkpoint`, preserving the existing default source-training behavior while enabling frozen-E4 initialization.
- `scripts/e6_run_external_few_shot.py` runs the preregistered 1%, 5%, 10%, and 25% fractions with deterministic seed 42, image-level sampling, publisher test isolation, and machine-readable provenance.
- `.github/workflows/e6_external_few_shot.yml` verifies the retained E4 artifact digest before running E6 and cross-checks the resulting machine-readable evidence.

The published split is 30 train / 10 development / 10 test images. Fractions are converted to an image budget by `ceil(fraction × 30)`, with a minimum of one image, yielding 1, 2, 3 and 8 adaptation images. The development split remains isolated and the 10-image test split is never used for adaptation.

## Current execution state

The latest E6 push-triggered run is GitHub Actions run `34027678815` on commit `2b0689347f24c5097ec09f0c1cc4b5c8e9d0c27b`. The 1%, 5%, and 10% fractions completed successfully, including their fraction-level cross-checks and evidence uploads. The 25% fraction reached the actual preregistered training step but was cancelled; its cross-check and evidence upload were therefore skipped. The fail-closed aggregate was consequently skipped.

No E6 aggregate metric is claimed. The failed 25% job (`101471454904`) has been explicitly rerun. Its rerun must complete the actual training step and produce independently verifiable machine-readable evidence before E6 can advance.

## Integrity rule

Do not manufacture an adaptation manifest by partitioning the locked 79-image S-BIAD634 zero-shot test set. Do not infer biological or acquisition groups from filenames. Do not promote E6 metrics until all four fractions execute successfully, all artifacts are retained, and the results are independently re-read from machine-readable artifacts.

E7 remains independent and must use the frozen E4 checkpoint without E6-driven tuning.

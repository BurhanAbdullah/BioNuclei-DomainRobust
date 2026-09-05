# E6 external fluorescence few-shot adaptation protocol

**Status: FROZEN EXECUTION PROTOCOL — not yet executed**

## Why this protocol exists

The locked E3 zero-shot experiment uses all 79 expert-annotated S-BIAD634 image/ground-truth pairs as its untouched evaluation set. No independent labelled S-BIAD634 adaptation pool is retained. Repartitioning those 79 images would invalidate the locked zero-shot evidence.

Therefore E6 is explicitly **cross-dataset few-shot adaptation**, not target-test adaptation.

## Authoritative adaptation dataset

**Aitslab-bioimaging1**, Zenodo DOI `10.5281/zenodo.6657260`, is the frozen independent fluorescence dataset for E6. The published dataset description reports 50 fluorescence microscopy images, more than 2,000 labelled nuclear objects, and a pre-defined 30/10/10 train/development/test split. The source describes grayscale fluorescence images and RGB annotation masks.

Authoritative references:

- Dataset DOI: https://doi.org/10.5281/zenodo.6657260
- Data descriptor: https://doi.org/10.1016/j.dib.2022.108769

## Scientific scope

This experiment measures whether the frozen BioNuclei method benefits from small amounts of labelled data from an **independent fluorescence domain**. It does **not** establish that adaptation to S-BIAD634 improves the locked S-BIAD634 zero-shot result.

Any manuscript or release text must preserve this distinction.

## Frozen design

1. Start from the retained frozen source-only E4 checkpoint.
2. Use only the publisher-provided Aitslab-bioimaging1 training split for adaptation.
3. Keep the publisher-provided development split isolated; no test result may influence training, checkpoint, or hyperparameter decisions.
4. Keep the publisher-provided test split completely untouched until final E6 evaluation.
5. Evaluate four preregistered labelled fractions: **1%, 5%, 10%, 25%** of the 30-image training pool.
6. Convert each fraction to an image budget using `ceil(fraction × 30)`, with a minimum of one image: **1, 2, 3, and 8 images**.
7. Select adaptation images at image level with deterministic **seed 42**; never sample patches across split boundaries.
8. Do not use S-BIAD634 labels, S-BIAD634 metadata, or S-BIAD634 test scores for adaptation decisions.
9. Use the same fixed 20-epoch training budget for every fraction; do not tune epochs against the test split.
10. Record dataset archive hashes, manifest hash, checkpoint hashes, configuration hash, seed, fraction, image budget, and exact commands for every run.

## Required outputs

For every fraction:

- adapted checkpoint;
- training history;
- image-level test metrics: Dice, IoU, AJI and boundary F1;
- per-image metrics;
- annotation/image budget;
- provenance record;
- dataset and split hashes;
- machine-readable aggregate results.

## Release gate

E6 is complete only after all four fractions execute successfully, the publisher train/development/test split is preserved, no test images enter adaptation, all artifacts are retained, and the results are independently re-read from machine-readable artifacts.

Until those conditions are satisfied, E6 remains **not complete**.

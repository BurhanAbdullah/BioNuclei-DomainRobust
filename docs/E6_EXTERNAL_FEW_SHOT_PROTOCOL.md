# E6 external fluorescence few-shot adaptation protocol

**Status: PROPOSED ALTERNATIVE — not executed**

## Why this protocol exists

The locked E3 zero-shot experiment uses all 79 expert-annotated S-BIAD634 image/ground-truth pairs as its untouched evaluation set. No independent labelled S-BIAD634 adaptation pool is currently retained. Repartitioning those 79 images would invalidate the locked zero-shot evidence.

Therefore, if the project elects to complete E6 without changing the locked E3 experiment, E6 must be described as **cross-dataset few-shot adaptation**, not target-test adaptation.

## Candidate adaptation dataset

A suitable independent fluorescence nuclear-segmentation dataset is **Aitslab-bioimaging1**, Zenodo DOI `10.5281/zenodo.6657260`. The published dataset description reports 50 fluorescence microscopy images, more than 2,000 labelled nuclear objects, and a pre-defined 30/10/10 train/development/test split. The images are Hoechst-stained nuclei acquired in a high-content screening setting and the annotations are RGB PNG instance/semantic masks. The dataset is independent of S-BIAD634 and is not used in the locked E3 zero-shot evaluation.

Authoritative references:

- Dataset DOI: https://doi.org/10.5281/zenodo.6657260
- Data descriptor: https://doi.org/10.1016/j.dib.2022.108769

## Scientific scope

This experiment measures whether the frozen BioNuclei method can benefit from small amounts of labelled data from an **independent fluorescence domain**. It does **not** establish that adaptation to S-BIAD634 improves the locked S-BIAD634 zero-shot result.

Any manuscript or release text must preserve this distinction.

## Frozen design

1. Start from the frozen source-only E4 checkpoint.
2. Use only the published Aitslab-bioimaging1 training split for adaptation.
3. Keep the published development split for checkpoint/hyperparameter decisions.
4. Keep the published test split completely untouched until final E6 evaluation.
5. Pre-register labelled fractions of 1%, 5%, 10%, and 25% of the adaptation pool.
6. Sample image-level units with seed 42; never sample patches across split boundaries.
7. Do not use S-BIAD634 labels, S-BIAD634 metadata, or S-BIAD634 test scores for adaptation decisions.
8. Record dataset archive hash, manifest hash, checkpoint hash, configuration, seed, fraction, and exact command for every run.

## Required outputs

For every fraction:

- adapted checkpoint;
- training history;
- image-level test metrics: Dice, IoU, AJI and boundary F1;
- per-image metrics;
- annotation count / labelled-image budget;
- provenance record;
- dataset and split hashes;
- machine-readable aggregate results.

## Release gate

E6 is complete only after all four fractions execute successfully, the published train/development/test split is preserved, no test images enter adaptation, all artifacts are retained, and the results are independently re-read from machine-readable artifacts.

Until those conditions are satisfied, E6 remains **not complete**.

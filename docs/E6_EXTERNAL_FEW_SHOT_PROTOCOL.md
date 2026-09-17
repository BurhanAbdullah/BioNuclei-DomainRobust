# E6 external fluorescence few-shot adaptation protocol

**Status: EXECUTED AND ARCHIVED**  
**Protocol freeze:** 2026-09-04  
**Finalizer verification:** run `34312833206`  

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

## Verified execution

All four fractions executed successfully in source run `34208190019` and were independently checked by finalizer run `34312833206`. The finalizer verified the expected image budgets (1, 2, 3, 8), seed 42, 20 epochs, common immutable dataset/configuration/E4 provenance, activation checkpointing, and fail-closed leakage flags. Each fraction was evaluated on the same 10-image publisher test split.

The verified aggregate artifact is `10088980217` with digest `sha256:fad1b13ae05cfcb4cfa7f958a61b027ff84751d1ff980a6d6c5d1794106f7c34`.

## Required outputs — verified

For every fraction the retained aggregate confirms:

- adapted-run provenance;
- image-level test metrics: Dice, IoU, AJI and boundary F1;
- adaptation image budget;
- dataset/configuration/checkpoint provenance;
- leakage controls;
- machine-readable aggregate results.

The separate annotation-budget analysis is archived at `docs/E6_ANNOTATION_EFFICIENCY_2026-09-17.md` and `outputs/e6_annotation_efficiency_2026-09-17.json`.

## Release/scientific interpretation

E6 satisfies its execution and artifact-integrity gate. Its results remain a **cross-dataset adaptation analysis** and must not be presented as evidence of adaptation to the locked S-BIAD634 test set. The observed annotation-budget curve is descriptive and non-monotonic under the fixed 20-epoch protocol; no general causal claim about annotation quantity is justified from these four runs.

# E6 execution blocker

**Status: BLOCKED — 2026-09-05**

E6 cannot be declared complete from the currently retained S-BIAD634 evidence.

The locked zero-shot evaluation contains all 79 expert-annotated S-BIAD634 image/ground-truth pairs. The repository does not contain a second authoritative, labelled S-BIAD634 adaptation pool that is independent of those 79 images. Reusing any of the locked 79 images for adaptation would make the original zero-shot evaluation no longer a clean untouched-test experiment.

The E6 leakage validator correctly fails closed rather than inventing a split.

## Required resolution

A valid E6 execution requires one of the following, chosen and frozen **before E6 training**:

1. an authoritative, independently labelled S-BIAD634 adaptation subset whose provenance and source grouping establish disjointness from the locked 79-image test set; or
2. an explicitly redesigned E6 experiment using a different authoritative labelled fluorescence dataset for adaptation, with the experiment renamed/described as **cross-dataset few-shot adaptation** rather than target-test adaptation.

A concrete independent candidate has now been documented in `docs/E6_EXTERNAL_FEW_SHOT_PROTOCOL.md`: Aitslab-bioimaging1 (Zenodo DOI `10.5281/zenodo.6657260`), reported as 50 fluorescence images with more than 2,000 labelled nuclear objects and a published 30/10/10 train/development/test split. This candidate is a protocol option only; no E6 training result has been claimed.

The second option must not be presented as equivalent to target-domain few-shot adaptation and must not be used to reinterpret the locked S-BIAD634 zero-shot result.

## Integrity rule

Do not manufacture an adaptation manifest by randomly partitioning the locked 79-image zero-shot test set. Do not infer biological or acquisition groups from filenames. Do not promote E6 metrics until the split, provenance, adaptation budget, training procedure, evaluation set, and retained artifacts have all been independently verified.

E7 remains independent and must use the frozen E4 checkpoint without E6-driven tuning.

# Validation and Cross-Check Record

## Purpose

This document records the distinction between repository-level software validation and scientific validation. It is intentionally conservative: a successful test suite is not treated as evidence of model performance.

## Repository tests

### CI run 32041237214

- Job: `tests`
- Result: **success**
- Checkout: passed
- Python setup: passed
- Package installation: passed
- Test suite: passed

### Regression CI run 32006740109

- Job: `tests`
- Result: **success**
- Included the S-BIAD634 pairing regression coverage.

## Cross-checks performed

- [x] BBBC039 official split construction is separated from model evaluation.
- [x] Raw third-party datasets are excluded from Git history.
- [x] Image/mask pairing is deterministic and rejects true duplicate ambiguities.
- [x] S-BIAD634 extra/unrelated ground-truth files are not treated as corresponding masks.
- [x] RGB/RGBA target images are converted deterministically to grayscale before inference.
- [x] Target images are padded to a stride-compatible shape before inference and cropped back afterward.
- [x] Tiled target-domain inference is available for large images.
- [x] Zero-shot result validation requires a complete `metrics.json`.
- [x] Zero-shot result validation requires exactly 79 evaluated images and 79 per-image records.
- [x] Required metric fields are checked before a result can be promoted to the research record.
- [x] Baseline artifact selection is explicit rather than an unrestricted wildcard.

## Scientific validation gates still open

- [ ] Independently audit the BBBC039 baseline numerical metrics from the archived artifact.
- [ ] Verify the current-code S-BIAD634 zero-shot artifact.
- [ ] Cross-check target-domain metrics against per-image records.
- [ ] Run domain-shift/failure stratification.
- [ ] Freeze the proposed robustness method only after failure analysis.
- [ ] Run ablations and strong-baseline comparisons.
- [ ] Run few-shot adaptation and external validation.
- [ ] Perform final statistical and novelty audits.

## Interpretation rule

A green CI run means the tested software path is functioning. It does not establish biological validity, generalization, or clinical utility. Those claims require the corresponding dataset-level and experiment-level evidence.

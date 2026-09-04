# E5 Ablation and Strong-Baseline Preregistration

Status: protocol only; no E5 result is asserted or accepted as release evidence.
Date: 2026-09-04

## Purpose

E5 tests whether the frozen source-only photometric domain-randomization protocol contributes reproducible target-domain improvement and whether that improvement exceeds strong conventional baselines. E5 must not alter the frozen method in response to target-test results.

## Frozen comparison

All E5 runs use the same source split, seed policy, evaluator, corrected instance-mask decoder, target manifest, and 79-image S-BIAD634 test set used for the verified E3/E4 analysis. Target test labels are evaluation-only.

Primary endpoint: AJI. Secondary endpoints: Dice, IoU, instance precision, instance recall, instance F1, and boundary F1.

## Ablations

Run the following source-trained variants with all other configuration held fixed:

1. Full frozen E4: source-only intensity-domain randomization.
2. No intensity-domain randomization: matched source-only baseline.
3. Each independently identifiable augmentation component removed, if the frozen implementation contains multiple photometric components.

If a component is not independently parameterized in the implementation, it is not invented post hoc; the ablation is recorded as not applicable.

## Strong-baseline rule

At least one strong conventional/public baseline must be evaluated under a matched protocol. A baseline is eligible only if its implementation, version/commit, configuration, training data, checkpoint provenance, and evaluation command can be retained and audited. No unavailable or unverified published number is copied into the final table.

The baseline comparison must use the same held-out target images and corrected evaluator where technically compatible. Any evaluator incompatibility must be documented explicitly rather than silently mixing metrics.

## Statistical analysis

Use the prespecified image-level analysis plan in `docs/STATISTICAL_ANALYSIS_PLAN.md`. Report paired per-image differences for matched E5 variants, 95% image-level bootstrap intervals, and the declared hypothesis-testing/multiplicity procedure. Do not treat pixels or instances as independent replicates.

## Leakage controls

No target test image, target label, or target-derived statistic may influence hyperparameter selection, augmentation selection, checkpoint selection, or baseline configuration. Any development use of target data must occur only through a separately documented adaptation protocol and cannot be folded into E5 zero-shot evidence.

## Required artifacts

Every E5 run must retain:

- exact commit SHA;
- configuration and seed;
- source split manifest hash;
- target manifest hash;
- checkpoint SHA-256;
- decoder/evaluator revision;
- complete per-image metrics for all 79 target images;
- aggregate metrics and image-level uncertainty;
- method/baseline provenance;
- failed-run records, if any;
- machine-readable JSON suitable for independent recomputation.

## Gate

E5 is complete only after all preregistered ablations that are applicable have executed, at least one eligible strong baseline has been independently verified, artifacts are complete and cross-checked, and the resulting interpretation is consistent with the retained source artifacts. A positive E5 result does not establish biological generalization or release readiness; E6, E7, uncertainty/failure analysis, clean reproducibility, packaging, and website verification remain required.

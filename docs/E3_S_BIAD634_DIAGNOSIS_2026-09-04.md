# E3 S-BIAD634 Zero-Shot Diagnosis

## Evidence record

- Workflow: `S-BIAD634 zero-shot transfer`
- GitHub Actions run: `33776934058`
- Repository commit evaluated: `fa51e1021c805ea414b9137ac1d30e111551ffc5`
- Baseline training run used by E3: `33768426630`
- Baseline artifact digest: `sha256:ec31fba69ee40de1f86d89ac0275d4341f58ec31a41f4129b33cf2501d3ce74f`
- E3 artifact: `s-biad634-zero-shot-33776934058`
- E3 artifact digest: `sha256:dbd1a7c0e2bda5dd893a87e6e16b960155989ba1a595227a0dc28cddbe83ffe8`
- E4 artifact: `e4-domain-robust-33791838274`
- E4 artifact digest: `sha256:7e6efb89b11d6d04db2eb5da257cd33cb19d93e5223c8e6c93c638308c3e9afa`
- Target images evaluated: 79
- Instance IoU matching threshold: 0.5
- Checkpoint seed: 42
- Tiled inference: 512 pixels with 32 pixel overlap

## Corrected zero-shot result

The corrected evaluator completed on all 79 target images and passed the workflow completeness gate. The artifact reports the following image-level means:

| Metric | Mean |
|---|---:|
| Dice | 0.39958885532931326 |
| IoU | 0.3018572277069463 |
| Instance precision | 0.1657510101162464 |
| Instance recall | 0.19997259690033162 |
| Instance F1 | 0.16421214727788674 |
| AJI | 0.20774710882927272 |
| Boundary F1 | 0.17674640533036035 |

These values are release evidence for the corrected E3 zero-shot experiment, not evidence of robustness improvement.

## Corrected E4 matched comparison

The corrected E4 artifact contains the same 79 target image identifiers as E3 and records the declared method as source-only intensity domain randomization, seed 42, with no target data used for training. Its image-level means are:

| Metric | E3 baseline | E4 domain-randomized | Mean paired change |
|---|---:|---:|---:|
| Dice | 0.39958885532931326 | 0.797841745331221 | +0.3982528900019075 |
| IoU | 0.3018572277069463 | 0.6768663324908323 | +0.3750091047838859 |
| Instance precision | 0.1657510101162464 | 0.3548423433559273 | +0.1890913332396808 |
| Instance recall | 0.19997259690033162 | 0.577991439484901 | +0.37801884258456936 |
| Instance F1 | 0.16421214727788674 | 0.4040309693633102 | +0.23981882208542343 |
| AJI | 0.20774710882927272 | 0.4915463885581285 | +0.2837992797288557 |
| Boundary F1 | 0.17674640533036035 | 0.18377646032618386 | +0.007030054995823467 |

At the per-image level, E4 improved over E3 on 67/79 images for Dice, 67/79 for IoU, 68/79 for AJI and 43/79 for boundary F1. A deterministic exploratory bootstrap of the 79 paired image-level differences using seed 42 and 10,000 resamples produced 95% intervals of approximately [0.344, 0.452] for Dice, [0.325, 0.423] for IoU and [0.239, 0.329] for AJI. The corresponding boundary-F1 interval crossed zero, approximately [-0.0028, 0.0177].

This comparison is **preliminary matched evidence, not the final statistical release gate**. The bootstrap calculation is an exploratory analysis of the retained artifacts and does not substitute for the prespecified statistics and failure-mode analysis required before method freeze.

## Observed failure pattern

The per-image artifact shows substantial heterogeneity rather than a uniform small degradation. The distribution includes images with essentially no matched instances and others with substantially better transfer. For the full 79-image set, the mean target-instance count is 99.46 while the mean predicted-instance count is 420.68. The corresponding mean true-positive, false-positive and false-negative counts are 40.47, 380.22 and 57.81 per image.

The strongest immediate signal is **instance over-production and poor instance matching on a substantial subset of target images**. The median instance precision is 0.0179 and median instance recall is 0.0704, while several images have zero true-positive matches. This is consistent with a transfer failure involving instance separation and/or domain-dependent appearance, rather than a simple uniform loss of foreground overlap.

Pixel overlap is also heterogeneous: Dice ranges from 0.0074 to 0.9691 and AJI from 0.0027 to 0.7480. Boundary F1 is correspondingly low on many failures, with a range from 0.0057 to 0.5605.

A small number of image families have much better transfer than the worst cases. Filename families such as `Ganglioneuroblastoma`, `Neuroblastoma`, and `normal` are **not treated as biological strata here** because the current artifact does not establish the required group mapping. They are retained only as identifiers for qualitative follow-up.

## Interpretation boundary

The current evidence supports the following diagnosis:

1. Source-domain performance remains strong under the corrected decoder and official BBBC039 protocol.
2. Zero-shot transfer to S-BIAD634 is substantially degraded under the same corrected evaluator.
3. The dominant measurable instance-level symptom is a large increase in false-positive predictions relative to matched target instances on many images.
4. Boundary quality degrades together with instance-level performance.
5. Failure severity is heterogeneous across target images.
6. The corrected E4 intervention materially improves image-level Dice, IoU and AJI relative to the corrected E3 baseline on the matched 79-image set, while boundary F1 shows only a small and uncertain change.

The evidence does **not** yet establish which biological or acquisition mechanism causes each failure. Intensity, morphology, scale, staining and other hypotheses require explicit target profiling and stratified analysis before a mechanism is declared.

## Next gate

The next scientific action is to complete the corrected target-domain profile and define the biological-group-aware evaluation strata. The E4 result is strong enough to justify formal method-freeze review, but method freeze must not be declared until the intervention is documented against the diagnosed failure pattern, the matched comparison is independently reproducible, and the prespecified statistics and failure analysis are complete.

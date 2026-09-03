# E3 S-BIAD634 Zero-Shot Diagnosis

## Evidence record

- Workflow: `S-BIAD634 zero-shot transfer`
- GitHub Actions run: `33776934058`
- Repository commit evaluated: `fa51e1021c805ea414b9137ac1d30e111551ffc5`
- Baseline training run used by E3: `33768426630`
- Baseline artifact digest: `sha256:ec31fba69ee40de1f86d89ac0275d4341f58ec31a41f4129b33cf2501d3ce74f`
- E3 artifact: `s-biad634-zero-shot-33776934058`
- E3 artifact digest: `sha256:dbd1a7c0e2bda5dd893a87e6e16b960155989ba1a595227a0dc28cddbe83ffe8`
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

The evidence does **not** yet establish which biological or acquisition mechanism causes each failure. Intensity, morphology, scale, staining and other hypotheses require explicit target profiling and stratified analysis before a mechanism is declared.

## Next gate

The next scientific action is to complete the corrected target-domain profile and define the biological-group-aware evaluation strata. Method freeze must not occur until the observed failure modes are mapped to a pre-registered intervention and then tested against the corrected baseline under matched conditions.

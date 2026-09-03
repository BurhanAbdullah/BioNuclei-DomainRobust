# E4 Verification Record

Date: 2026-09-04

## Hosted execution

- Workflow run: `33791838274`
- Head commit: `72f1bba8f046852724fdbbd110806a5cfada1bd9`
- Job: `100770031212`
- Job conclusion: `success`
- Target evaluation: 79 images
- Provenance/completeness step: `success`
- Artifact: `e4-domain-robust-33791838274`
- Artifact ID: `9912441468`
- Artifact digest: `sha256:7e6efb89b11d6d04db2eb5da257cd33cb19d93e5223c8e6c93c638308c3e9afa`

## Method record

The retained artifact records:

- method: `source_only_intensity_domain_randomization`
- target data used for training: `false`
- seed: `42`

The artifact contains the trained checkpoint, training history, method record, target metrics, provenance, the official BBBC039 split manifest, and source/target download manifests.

## Matched target result

The retained E4 target metrics contain 79 per-image records. Image-level means are:

| Metric | E4 mean |
|---|---:|
| Dice | 0.797841745331221 |
| IoU | 0.6768663324908323 |
| Instance precision | 0.3548423433559273 |
| Instance recall | 0.577991439484901 |
| Instance F1 | 0.4040309693633102 |
| AJI | 0.4915463885581285 |
| Boundary F1 | 0.18377646032618386 |

The retained E3 baseline artifact contains the same 79 target identifiers, enabling a matched image-level comparison. The E3 diagnosis records E4 improvements on 67/79 images for Dice, 67/79 for IoU, 68/79 for AJI, and 43/79 for boundary F1.

## Statistical status

An exploratory paired bootstrap was previously computed from the retained image-level differences using seed 42 and 10,000 resamples. It gave approximate 95% intervals of [0.344, 0.452] for Dice, [0.325, 0.423] for IoU, and [0.239, 0.329] for AJI; the boundary-F1 interval crossed zero at approximately [-0.0028, 0.0177].

These intervals are **exploratory only**. They do not close the prespecified statistical-analysis gate, which still requires the final analysis plan, failure/uncertainty analysis, and biological-group-aware evaluation.

## Release decision

E4 execution and artifact integrity are verified for this run. This does **not** by itself close the E4 scientific contribution gate or justify a final method freeze. The corrected baseline, E3 diagnosis, matched E4 comparison, target-domain profiling, and prespecified statistics must remain synchronized before downstream ablations, adaptation, external validation, or release claims are accepted.

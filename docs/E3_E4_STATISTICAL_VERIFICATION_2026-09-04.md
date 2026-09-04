# E3/E4 prespecified statistical verification

Status: executed and independently cross-validated from retained artifacts.
Date: 2026-09-04

## Source evidence

- E3 artifact: `s-biad634-zero-shot-33776934058`
- E3 digest: `sha256:dbd1a7c0e2bda5dd893a87e6e16b960155989ba1a595227a0dc28cddbe83ffe8`
- E4 artifact: `e4-domain-robust-33791838274`
- E4 digest: `sha256:7e6efb89b11d6d04db2eb5da257cd33cb19d93e5223c8e6c93c638308c3e9afa`
- Corrected baseline checkpoint SHA-256: `7209a6990514380804210292ac208b0f3b0b0a054338a145e1916044762d7c92`
- Matched image count: 79; image identifiers identical with no missing pairs.
- E3 evaluator commit: `fa51e1021c805ea414b9137ac1d30e111551ffc5`
- E4 evaluator/method commit: `72f1bba8f046852724fdbbd110806a5cfada1bd9`

## Prespecified analysis

The primary endpoint is AJI. Secondary endpoints are Dice, IoU, instance precision, instance recall, instance F1 and boundary F1. The analysis unit is the image. Bootstrap uses seed 42 and 10,000 image-level resamples. The primary test is two-sided paired Wilcoxon signed-rank; Holm correction is applied across the six secondary endpoints.

## Results

| Metric | E3 mean | E4 mean | Mean paired Δ | 95% bootstrap CI | Wilcoxon p | Holm p (secondary) |
|---|---:|---:|---:|---:|---:|---:|
| AJI (primary) | 0.207747 | 0.491546 | +0.283799 | [0.239086, 0.329079] | 5.87e-13 | — |
| Dice | 0.399589 | 0.797842 | +0.398253 | [0.344486, 0.451476] | 5.87e-13 | 4.11e-12 |
| IoU | 0.301857 | 0.676866 | +0.375009 | [0.324918, 0.421792] | 5.87e-13 | 4.11e-12 |
| Precision | 0.165751 | 0.354842 | +0.189091 | [0.144562, 0.235435] | 1.66e-12 | 4.48e-12 |
| Recall | 0.199973 | 0.577991 | +0.378019 | [0.309746, 0.445227] | 1.38e-12 | 4.48e-12 |
| Instance F1 | 0.164212 | 0.404031 | +0.239819 | [0.189984, 0.292359] | 1.12e-12 | 4.48e-12 |
| Boundary F1 | 0.176746 | 0.183776 | +0.007030 | [-0.002601, 0.018104] | 0.561 | 0.561 |

AJI improved on 68/79 images (86.1%); 11/79 decreased and none were exactly tied. Boundary F1 improved on 43/79 and decreased on 36/79, so the evidence does not support a clear boundary-F1 improvement.

## Failure analysis retained

The machine-readable result records the ten largest AJI losses, ten largest AJI gains, and ten highest E4 predicted/target instance-count ratios. The largest AJI losses are concentrated among several named target-image families, but these names are not treated as biological/acquisition strata because authoritative group metadata are absent. One target image remains an extreme prediction-count outlier and is retained rather than excluded.

## Interpretation boundary

This closes the prespecified matched statistical-analysis execution gate for the E3/E4 comparison. It does **not** by itself close method freeze, prove biological generalization, or justify a superiority claim across biological groups. Those claims require the documented intervention rationale, controlled ablations, strong-baseline comparison, and independent validation required by the release checklist.

The machine-readable result is `outputs/e3_e4_statistics_2026-09-04.json`; the executable analysis is `scripts/analyze_e3_e4_statistics.py`.

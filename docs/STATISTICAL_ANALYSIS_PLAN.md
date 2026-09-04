# Statistical Analysis Plan

Status: prespecified analysis protocol; no results are asserted here.
Date: 2026-09-04

## Scope

This plan governs the matched E3/E4 S-BIAD634 comparison and the downstream release analysis. It is written before any downstream E5/E6/E7 result is accepted as release evidence.

## Primary comparison

The primary scientific comparison is the image-matched difference between the frozen source-only E3 model and the source-only intensity-domain-randomized E4 model on the same 79 S-BIAD634 images, using the corrected canonical instance-mask decoder and the same evaluator.

Primary endpoint: AJI.

Secondary endpoints: Dice, IoU, instance precision, instance recall, instance F1, and boundary F1.

All analyses are performed on image-level paired observations; pooled pixels or pooled instances are not treated as independent replicates.

## Estimation

For each endpoint, report:

1. E3 mean and median.
2. E4 mean and median.
3. Paired per-image difference (E4 minus E3) mean and median.
4. 95% bootstrap confidence interval for the mean paired difference, using deterministic image-level resampling with the declared seed.
5. Number and proportion of images with positive, zero, and negative paired differences.
6. Distribution of per-image differences and identified influential/failure images.

The bootstrap unit is the image, not an individual pixel, instance, or patch.

## Hypothesis testing

For the primary AJI endpoint, use a two-sided paired Wilcoxon signed-rank test at alpha = 0.05. Report the exact/appropriate test p-value, number of non-zero pairs, and a paired effect-size estimate with its interpretation.

Secondary endpoints use the same paired test and are reported with multiplicity control. Holm correction is applied across the six secondary endpoints. The corrected p-values are reported alongside uncorrected values.

Statistical significance is not interpreted as evidence of biological generalization by itself; magnitude, uncertainty, failure patterns, provenance, and independent validation remain required.

## Missingness and exclusions

No image is excluded because its result is unfavorable. Any exclusion must be traceable to a documented data-integrity or protocol violation and reported with the original identifier and reason. A missing metric is not silently converted to zero.

## Biological/acquisition groups

Group-level inference is conditional on authoritative metadata. Filename families, visual similarity, or inferred acquisition groups are not treated as biological strata. If authoritative groups become available, group summaries will be reported separately and the analysis will account for the nested structure rather than treating images from the same group as independent biological replicates.

## Failure and uncertainty analysis

The final analysis must retain per-image records and examine at least:

- predicted-versus-target instance count ratio;
- false-positive and false-negative instance counts;
- AJI and instance F1 outliers;
- intensity and image-shape/domain-profile variables available without target-label leakage;
- boundary-F1 behavior separately from region-overlap metrics.

Uncertainty is reported at the image level. Bootstrap intervals are not used to claim independent biological replication.

## Reproducibility requirements

Every final statistical artifact must record:

- repository commit SHA;
- evaluator/decoder revision;
- source and target manifest identifiers and SHA-256 values;
- experiment artifact identifiers and digests;
- metric definitions/version;
- image count and identifiers;
- random seed and bootstrap resample count;
- statistical-test and multiplicity-correction versions/parameters.

The machine-readable result must contain the per-image paired table and the aggregate statistical summary so every reported number can be regenerated from retained source artifacts.

## Release gate

This plan does not mark the statistical gate complete. The gate closes only after an executed analysis artifact is independently checked against the retained E3/E4 source artifacts and all required failure/uncertainty and provenance fields are present.

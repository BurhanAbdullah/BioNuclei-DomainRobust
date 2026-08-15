# Focused Novelty Audit — 2026-08-15

## Scope

This audit is deliberately provisional. It is used to constrain the method design before the BBBC039 baseline and BBBC039 → S-BIAD634 zero-shot failure modes are measured. It is **not** a first-to-claim statement.

## Established literature

- **Learning to Generalize over Subpartitions for Heterogeneity-Aware Domain Adaptive Nuclei Segmentation**, IJCV 2024, explicitly studies distribution shift in nuclei segmentation and includes a fluorescence-to-histopathology cross-modality setting.
- **NuSegDG**, Knowledge-Based Systems 2025, addresses domain-generalized nuclei segmentation with heterogeneous-space adaptation, Gaussian-kernel prompting and a two-stage decoder.
- **UN-SAM**, Medical Image Analysis 2025, addresses domain-adaptive/self-prompted universal nuclei segmentation and reports evaluation on unseen nuclei domains.
- S-BSST265/S-BIAD634 is itself a published benchmark for heterogeneous fluorescence nuclear segmentation and has been reused in later segmentation studies.

## Consequence for this project

The following are **not sufficient novelty claims** on their own:

1. another U-Net for nuclei segmentation;
2. generic stain/intensity augmentation;
3. generic domain-adversarial feature alignment;
4. generic SAM fine-tuning;
5. simply testing on S-BIAD634;
6. claiming domain generalization because performance is measured on one unseen dataset.

## Candidate research gap to test

The project should first establish a controlled **fluorescence-to-fluorescence** source/target experiment:

**Source:** BBBC039v1 — controlled fluorescence benchmark.

**Target:** S-BIAD634 / S-BSST265 — heterogeneous human fluorescence data with variation in preparation, imaging modality, magnification, signal-to-noise ratio and biological source.

The scientific contribution must be derived from the observed failure mechanism. Candidate mechanisms include:

- intensity/bit-depth and acquisition nuisance dominating learned features;
- scale mismatch between source and target nuclei;
- boundary uncertainty under low SNR;
- morphology-vs-appearance entanglement;
- domain-specific feature collapse;
- calibration failure under domain shift.

No candidate is selected until baseline evidence identifies which mechanism is actually limiting performance.

## Required comparisons

At minimum, the final method should be compared against:

- the boundary-aware U-Net baseline in this repository;
- a conventional U-Net-style baseline;
- a strong contemporary nuclei segmentation/domain-generalization baseline where implementation and protocol are reproducible;
- the proposed method with each proposed component removed.

If a published method has an available implementation and directly matches the experimental setting, it should be included rather than replaced by a weak reimplementation.

## Required evidence before a novelty claim

- real BBBC039 held-out test result;
- zero-shot BBBC039 → S-BIAD634 result;
- biological-group-aware target-domain analysis;
- controlled ablations;
- confidence intervals or bootstrap intervals at the image/biological-group level as appropriate;
- external validation on a genuinely independent fluorescence dataset;
- final literature search immediately before manuscript submission.

## Current status

The BBBC039 baseline training run is active. Therefore the method section remains intentionally undecided.

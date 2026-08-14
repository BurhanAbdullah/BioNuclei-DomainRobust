# Research Protocol

## Primary question

How well does nuclear instance segmentation transfer from a controlled fluorescence imaging domain to a heterogeneous human bioimaging domain, and can domain-robust training recover the lost performance with limited target-domain annotation?

## Phase 1 — Source-domain baseline

Train the boundary-aware U-Net baseline on the authoritative BBBC039 training split. Evaluate only on the held-out BBBC039 test split for baseline correctness.

Report:

- Dice
- IoU
- AJI
- boundary F1
- object-level errors where implemented

No claim of novelty is made from the baseline architecture.

## Phase 2 — Zero-shot domain shift

Apply the source-trained model to S-BIAD634 without target-domain fine-tuning.

The purpose is to measure the actual domain gap before proposing mitigation.

## Phase 3 — Robustness methods

Candidate methods should be introduced one at a time and compared against the baseline. Examples include intensity/domain randomization, representation alignment, feature normalization, and uncertainty-aware adaptation. The exact proposed method is not fixed until preliminary failure analysis identifies the dominant shift.

## Phase 4 — Few-shot adaptation

Use predefined biological-group-level target subsets at 1%, 5%, 10%, and 25% where supported by the target dataset structure. The same held-out target groups must never be used during training or selection.

## Split integrity

The unit of splitting must reflect the biological origin of the image. Never split random patches from the same original field across train and test. Never allow related tissue preparation, patient/sample, or source-image groups to cross partitions when metadata indicate dependence.

Every experiment must save its split manifest.

## Statistical reporting

Report point estimates together with confidence intervals. Where image/biological-group pairing permits, use paired bootstrap resampling or another pre-specified paired procedure. Report performance by target-domain subgroup where metadata support it, rather than only one pooled metric.

## Reproducibility

Every result must be traceable to:

1. dataset accession/version;
2. split manifest;
3. configuration file;
4. code revision;
5. random seed;
6. checkpoint identifier;
7. evaluation script revision.

## Scientific integrity

The repository must not contain fabricated results. Synthetic data may be used only for code-path and unit-test validation and must be explicitly labeled as such. External literature determines whether a method is genuinely novel; repository language must not overstate novelty before verification.

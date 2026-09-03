# Research Progress

This checklist is updated only when a step is actually verified. Tooling is not marked as scientific verification until it has been executed on the real dataset.

## Phase 0 — foundations

- [x] Define domain-robust nuclear instance-segmentation research question.
- [x] Create reproducible repository structure.
- [x] Add boundary-aware U-Net baseline implementation.
- [x] Add target-generation, loss, and metric tests.
- [x] Add CI and confirm the current test workflow passes.
- [x] Establish no-fabrication/no-leakage/reproducibility rules.

## Phase 1 — BBBC039 source-domain verification

- [x] Verify the authoritative BBBC039 page and published dataset-level facts.
- [x] Correct acquisition logic to use the official `images.zip`, `masks.zip`, and `metadata.zip` archives.
- [x] Add archive hashing and ZIP-integrity checks.
- [x] Add strict local-data verification script.
- [x] Document expected 200-image, 520 x 696, 16-bit structure and official partition policy.
- [x] Add a strict builder for the official metadata-defined train/validation/test manifest.
- [x] Add a GitHub Actions workflow that can download, inspect, verify, split, and archive BBBC039 provenance artifacts in an internet-enabled runner.
- [x] Run real-data acquisition on a GitHub-hosted runner.
- [x] Confirm the official archives are reachable and downloadable from the hosted runner.
- [x] Diagnose and exclude archive sidecar noise (`__MACOSX/` and `._*`).
- [x] Verify 200 unique BBBC039 images and 200 masks from the actual files.
- [x] Verify actual image dimensions and dtype from all 200 accepted images: 520 x 696, uint16.
- [x] Verify image/mask filename correspondence for all 200 pairs.
- [x] Verify the official split from the actual metadata package: 100 training, 50 validation, 50 test; no pairwise overlap.
- [x] Produce and archive the immutable official split manifest. Manifest SHA-256: `91d46e4c3f206692278ae4295c3ead62e6f8fa9a1ebb46986ae2cda71c327ff5`.

## Phase 2 — source-domain baseline

- [x] Implement reproducible boundary-aware U-Net training and evaluation entry points.
- [x] Add CPU-only hosted-runner support with `imagecodecs` for compressed TIFF decoding.
- [x] Make the hosted baseline run configurable by epoch count and seed.
- [x] Archive baseline artifacts with `if: always()`.
- [x] Execute a complete real BBBC039 baseline run on the verified official split. GitHub Actions run `31995038694` completed successfully.
- [x] Train boundary-aware U-Net on the official training split for the reproducible hosted run.
- [x] Evaluate the official validation split.
- [x] Evaluate the held-out official test split.
- [x] Archive the baseline checkpoint and evaluation artifact. Artifact: `bbbc039-baseline-31995038694`.
- [x] Execute a fresh complete BBBC039 baseline run on the same protocol. GitHub Actions run `33737710362` completed successfully.
- [x] Archive the fresh baseline artifact: `bbbc039-baseline-33737710362`, SHA-256 digest `a784132322319663754bb8466b311b3812b821a9f14f9a3f2b77a23c43c00313`.
- [x] Extract and independently inspect Dice, IoU, AJI, and boundary F1 from the fresh archived test metrics.
- [x] Compute/verify image-level bootstrap confidence intervals from the fresh archived test metrics.
- [x] Centralize AJI and instance PRF validation in reusable metric code and add regression tests for shape safety, empty masks, non-contiguous labels, and split-instance errors.
- [x] Re-run the source baseline after the RGB instance-mask decoder correction. Corrected run `33768426630` completed on the official split and archived artifact `bbbc039-baseline-33768426630` with digest `sha256:ec31fba69ee40de1f86d89ac0275d4341f58ec31a41f4129b33cf2501d3ce74f`.
- [ ] Complete a single reproducibility audit tying seed, configuration, split manifest, checkpoint hash, decoder revision, and metrics together.
- [ ] Produce qualitative overlays and failure analysis.

## Phase 3 — cross-domain generalization

- [x] Acquire and verify S-BIAD634 / S-BSST265 on a GitHub-hosted runner.
- [x] Verify the target archive inventory contains 79 raw fluorescence TIFFs and 79 corresponding ground-truth TIFFs; provenance SHA-256: `8285987ed4d57c46a46a55a33c1c085875ea41f429b59cde31d249741aa07ad1`.
- [x] Add deterministic target-domain profiling tooling for image intensity, shape, dtype, annotation count and annotation-area distributions.
- [x] Add LZW TIFF decoding dependency and unconditional diagnostic artifact upload.
- [x] Fix target profiling to decode instance masks with the same repository decoder used by evaluation.
- [x] Fix the target-profile workflow gate to validate the profile schema actually emitted by the profiling script and require all 79 per-image records.
- [ ] Re-run and archive the corrected target-domain profile after the RGB decoder correction.
- [ ] Define biological-group-aware target-domain evaluation.
- [x] Run zero-shot BBBC039 to S-BIAD634 transfer using the corrected evaluator and decoder. GitHub Actions run `33776934058` completed successfully on all 79 target images.
- [x] Diagnose the historical zero-shot pairing failure.
- [x] Fix target pairing to require exactly one matching ground truth per raw image and ignore unrelated GT files.
- [x] Add regression tests for unrelated extra GT files and duplicate matching GT files.
- [x] Add stride-compatible padding and bounded-memory tiled inference for target-domain images.
- [x] Add deterministic RGB/RGBA-to-grayscale conversion for target-domain inputs.
- [x] Change the workflow to select the exact verified baseline artifact rather than a wildcard artifact pattern.
- [x] Archive and independently verify the corrected current-code zero-shot metrics. Artifact `s-biad634-zero-shot-33776934058`, SHA-256 digest `sha256:dbd1a7c0e2bda5dd893a87e6e16b960155989ba1a595227a0dc28cddbe83ffe8`, contains 79 per-image records and passed the completeness gate.
- [x] Quantify domain-shift failure modes at the image/instance level; see `docs/E3_S_BIAD634_DIAGNOSIS_2026-09-04.md`.

## Phase 4 — domain-robust method

- [x] Conduct a provisional focused 2023–2026 novelty audit; see `docs/NOVELTY_AUDIT_2026-08-15.md`.
- [ ] Finalize the novelty audit after corrected baseline/zero-shot failure modes are known.
- [x] Execute a complete E4 source-only intensity/domain-randomization run with all 79 target images evaluated. GitHub Actions run `33618446838` passed the target completeness gate and archived artifact `e4-domain-robust-33618446838`.
- [x] Execute a fresh E4 run on the same source-only protocol. GitHub Actions run `33737663312` completed successfully; artifact `e4-domain-robust-33737663312` was retained with digest `bea00c3a78311e7294954e36b505294ef6b511b7aa9377df346e4475147ec206` and includes 79 target-image metrics plus provenance.
- [x] Independently inspect the fresh E4 artifact structure, method record, configuration, target count, and provenance linkage.
- [ ] Re-run E4 after the RGB decoder correction before comparing it against the corrected baseline.
- [ ] Compare E4 against the corrected baseline under a matched and audited evaluator.
- [ ] Define the final domain-robust method from observed failure modes.
- [ ] Run controlled ablations.
- [ ] Compare against strong published and conventional baselines.
- [ ] Perform statistical analysis across biological groups/images.

## Phase 5 — adaptation and external validation

- [ ] Run few-shot adaptation at pre-registered label fractions.
- [ ] Measure annotation efficiency.
- [ ] Validate on an independent external fluorescence dataset.
- [ ] Evaluate robustness to acquisition/intensity/noise shifts.
- [ ] Evaluate failure cases and uncertainty calibration.

## Phase 6 — paper and release

- [ ] Freeze the final experimental protocol.
- [ ] Complete final literature/novelty audit.
- [ ] Generate all paper figures/tables directly from versioned outputs.
- [ ] Re-run the complete pipeline from a clean environment.
- [ ] Audit every reported number against raw experiment artifacts.
- [ ] Release code, manifests, configurations, and reproducibility instructions.
- [ ] Prepare manuscript only after the evidence supports the claims.

## Current state — 2026-09-04

The RGB/RGBA instance-mask decoder correction has now been exercised by a corrected source baseline and a corrected S-BIAD634 zero-shot transfer run. The corrected source baseline is GitHub Actions run `33768426630`; it trained for 20 epochs on the official 100-image training split and evaluated the 50-image validation and 50-image held-out test splits. Its held-out test means are Dice `0.9696520862500608`, IoU `0.9411678377723045`, AJI `0.9105499261289745`, and boundary F1 `0.6911822539055567`, with image-level 95% bootstrap intervals generated from 2,000 resamples at seed 42. These numbers are traceable to the archived baseline artifact and are now valid corrected baseline evidence.

The corrected S-BIAD634 zero-shot transfer is GitHub Actions run `33776934058`, evaluated on all 79 target images using the corrected evaluator and the corrected baseline artifact from run `33768426630`. Its artifact contains 79 per-image records and has digest `sha256:dbd1a7c0e2bda5dd893a87e6e16b960155989ba1a595227a0dc28cddbe83ffe8`. The image-level means are Dice `0.39958885532931326`, IoU `0.3018572277069463`, instance precision `0.1657510101162464`, instance recall `0.19997259690033162`, instance F1 `0.16421214727788674`, AJI `0.20774710882927272`, and boundary F1 `0.17674640533036035`.

The E3 artifact shows a heterogeneous transfer failure dominated, on many images, by over-production of predicted instances and poor matching. Across the 79 images, mean target-instance count is 99.46 while mean predicted-instance count is 420.68; mean true positives, false positives and false negatives are 40.47, 380.22 and 57.81. Median instance precision is 0.0179 and median instance recall is 0.0704. Several images have zero true-positive matches. These observations support an instance-level transfer failure diagnosis but do not by themselves establish a biological or acquisition mechanism. The detailed evidence boundary is documented in `docs/E3_S_BIAD634_DIAGNOSIS_2026-09-04.md`.

The next gate is corrected target-domain profiling and biological-group-aware evaluation, followed by a corrected E4 rerun. No robustness improvement, method freeze, ablation, strong-baseline comparison, few-shot result, external-validation result, or Release 1.0 status is claimed yet.

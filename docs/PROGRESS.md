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
- [ ] Resolve the unusually low AJI relative to the high pixel-overlap metrics before any baseline numerical claim is promoted to the release record.
- [ ] Complete a single reproducibility audit tying seed, configuration, split manifest, checkpoint hash, and metrics together.
- [ ] Produce qualitative overlays and failure analysis.

## Phase 3 — cross-domain generalization

- [x] Acquire and verify S-BIAD634 / S-BSST265 on a GitHub-hosted runner.
- [x] Verify the target archive inventory contains 79 raw fluorescence TIFFs and 79 corresponding ground-truth TIFFs; provenance SHA-256: `8285987ed4d57c46a46a55a33c1c085875ea41f429b59cde31d249741aa07ad1`.
- [x] Add deterministic target-domain profiling tooling for image intensity, shape, dtype, annotation count and annotation-area distributions.
- [x] Add LZW TIFF decoding dependency and unconditional diagnostic artifact upload.
- [ ] Execute and archive the target-domain profile.
- [ ] Define biological-group-aware target-domain evaluation.
- [ ] Run zero-shot BBBC039 → S-BIAD634 transfer on the current evaluator commit.
- [x] Diagnose the historical zero-shot pairing failure.
- [x] Fix target pairing to require exactly one matching ground truth per raw image and ignore unrelated GT files.
- [x] Add regression tests for unrelated extra GT files and duplicate matching GT files.
- [x] Add stride-compatible padding and bounded-memory tiled inference for target-domain images.
- [x] Add deterministic RGB/RGBA-to-grayscale conversion for target-domain inputs.
- [x] Change the workflow to select the exact verified baseline artifact rather than a wildcard artifact pattern.
- [ ] Archive and independently verify the current-code zero-shot metrics.
- [ ] Quantify domain-shift failure modes.

## Phase 4 — domain-robust method

- [x] Conduct a provisional focused 2023–2026 novelty audit; see `docs/NOVELTY_AUDIT_2026-08-15.md`.
- [ ] Finalize the novelty audit after current baseline/zero-shot failure modes are known.
- [x] Execute a complete E4 source-only intensity/domain-randomization run with all 79 target images evaluated. GitHub Actions run `33618446838` passed the target completeness gate and archived artifact `e4-domain-robust-33618446838`.
- [ ] Independently audit the E4 artifact and compare it against the fresh baseline under a matched protocol.
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

## Current state — 2026-09-03

The scientific foundation is being closed systematically rather than declared complete early. A fresh BBBC039 baseline run (`33737710362`) completed successfully, including held-out test/validation evaluation and image-level bootstrap confidence intervals. Its artifact is retained. During independent metric inspection, the pixel-overlap metrics were high while AJI was unexpectedly low; this is now an explicit release blocker until the instance-metric implementation and/or mask encoding are audited. No numerical baseline result is promoted to a scientific claim until that discrepancy is resolved.

The E4 domain-randomization workflow has also completed a full target-domain evaluation on 79 S-BIAD634 images in run `33618446838`, with the completeness/provenance gates passing and an artifact retained. That is engineering/experimental evidence of a completed E4 execution, not yet evidence that the method improves scientific robustness. A fresh E4 run (`33737663312`) is currently progressing through target evaluation and will be independently checked when complete.

The immediate sequence is therefore: audit the source instance metrics → complete current zero-shot evaluation/profile → quantify domain-shift mechanisms → select/freeze the mechanism-driven robustness method → ablations and strong baselines → few-shot adaptation → independent external validation → final statistical/reproducibility audit → Release 1.0. The community layer follows the scientific release rather than preceding it.

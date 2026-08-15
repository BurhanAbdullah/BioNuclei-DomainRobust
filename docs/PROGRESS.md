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

- [ ] Train boundary-aware U-Net on the official training split.
- [ ] Tune only on the official validation split.
- [ ] Evaluate once on the held-out official test split.
- [ ] Report Dice, IoU, AJI, and boundary F1 with confidence intervals.
- [ ] Save seed, configuration, split manifest, checkpoint hash, and metrics.
- [ ] Produce qualitative overlays and failure analysis.

## Phase 3 — cross-domain generalization

- [ ] Acquire and verify S-BIAD634.
- [ ] Define biological-group-aware target-domain evaluation.
- [ ] Run zero-shot BBBC039 → S-BIAD634 transfer.
- [ ] Quantify domain-shift failure modes.

## Phase 4 — domain-robust method

- [ ] Conduct focused 2023–2026 novelty audit after baseline failure modes are known.
- [ ] Define the proposed domain-robust method from observed failure modes.
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

## Current state

Phase 1 is complete. The real BBBC039v1 archives were downloaded and verified on GitHub's hosted runner; the accepted dataset contains 200 unique fluorescence TIFFs and 200 corresponding PNG masks, all images 520 x 696 uint16. The official metadata defines 100 training, 50 validation, and 50 test images with no pairwise overlap. The immutable split manifest and acquisition provenance are retained as workflow artifacts. The first baseline attempt exposed a real metadata-to-archive filename-extension mismatch before training; this was fixed by resolving official manifest names by exact filename or unique stem. The evaluator was given the same resolution logic, and the hosted workflow was switched to CPU PyTorch wheels to avoid unnecessary CUDA dependency downloads. A new baseline run is now executing; no baseline metric is considered verified until it completes.

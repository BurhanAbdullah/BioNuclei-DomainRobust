# Research Progress

This checklist is updated only when a step is actually verified. Tooling is not marked as scientific verification until it has been executed on the real dataset.

## Phase 0 — foundations

- [x] Define domain-robust nuclear instance-segmentation research question.
- [x] Create reproducible repository structure.
- [x] Add boundary-aware U-Net baseline implementation.
- [x] Add target-generation, loss, and metric tests.
- [x] Add CI and confirm the current test workflow passes (3 passed in 1.99 s; GitHub Actions run 31799852171).
- [x] Establish no-fabrication/no-leakage/reproducibility rules.

## Phase 1 — BBBC039 source-domain verification

- [x] Verify the authoritative BBBC039 page and published dataset-level facts.
- [x] Correct acquisition logic to use the official `images.zip`, `masks.zip`, and `metadata.zip` archives.
- [x] Add archive hashing and ZIP-integrity checks.
- [x] Add strict local-data verification script.
- [x] Document expected 200-image, 520 x 696, 16-bit structure and official partition policy.
- [x] Add a strict builder for the official metadata-defined train/validation/test manifest.
- [x] Add a GitHub Actions workflow that can download, inspect, verify, split, and archive BBBC039 provenance artifacts in an internet-enabled runner.
- [x] Run the first real-data acquisition attempt on a GitHub-hosted runner.
- [x] Confirm the official archives are reachable and downloadable from the hosted runner.
- [x] Detect a concrete packaging/layout discrepancy: the first verification attempt found 400 TIFF paths, with 200 readable 520 x 696 uint16 images and 200 TIFF read errors; the same acquisition also exposed `__MACOSX/` and `._*` AppleDouble sidecars in the ZIP package.
- [x] Diagnose the 400-versus-200 discrepancy as archive-sidecar noise rather than silently treating the extra files as scientific images.
- [x] Update extraction, diagnostics, and strict verification to exclude `__MACOSX/` and `._*` AppleDouble metadata.
- [ ] Re-run strict verification on the cleaned extraction.
- [ ] Verify 200 unique BBBC039 images and 200 masks from the actual files.
- [ ] Verify actual image dimensions and dtype from all accepted images.
- [ ] Verify the official 100/50/50 split from the actual metadata package.
- [ ] Verify image/mask filename correspondence.
- [ ] Produce the immutable local dataset manifest.

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

## Current blocker

The hosted runner successfully downloaded the official BBBC039 archives. The first strict run counted 400 TIFF paths, but its diagnostic showed exactly 200 readable 520 x 696 uint16 images and 200 TIFF read errors; the same package contained explicit `__MACOSX/` and `._*` AppleDouble metadata entries. This is consistent with ZIP sidecar files, not 400 scientific fields. The repository now excludes those sidecars during extraction and verification. The next run must pass the cleaned-data checks before training is allowed.

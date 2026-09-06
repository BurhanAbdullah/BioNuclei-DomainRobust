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
- [x] Verify authoritative BBBC039 acquisition and archive structure.
- [x] Verify 200 images/masks and 520 x 696 uint16 structure.
- [x] Verify official metadata-defined 100/50/50 split with no overlap.
- [x] Archive immutable split manifest; SHA-256 `91d46e4c3f206692278ae4295c3ead62e6f8fa9a1ebb46986ae2cda71c327ff5`.

## Phase 2 — source-domain baseline
- [x] Execute complete real BBBC039 baseline runs.
- [x] Correct the RGB instance-mask decoder and centralize AJI/instance PRF validation.
- [x] Re-run the source baseline after decoder correction: run `33768426630`; artifact `bbbc039-baseline-33768426630`; digest `sha256:ec31fba69ee40de1f86d89ac0275d4341f58ec31a41f4129b33cf2501d3ce74f`.
- [x] Verify corrected held-out test means: Dice `0.9696520862500608`, IoU `0.9411678377723045`, AJI `0.9105499261289745`, boundary F1 `0.6911822539055567`.
- [ ] Complete a single reproducibility audit tying seed, configuration, split manifest, checkpoint hash, decoder revision and metrics together.
- [ ] Produce qualitative overlays and failure analysis.

## Phase 3 — cross-domain generalization
- [x] Acquire and verify S-BIAD634 / S-BSST265 on a hosted runner.
- [x] Verify 79 S-BIAD634 raw/GT pairs; provenance SHA-256 `8285987ed4d57c46a46a55a33c1c085875ea41f429b59cde31d249741aa07ad1`.
- [x] Correct target profiling for the observed RGB/RGBA TIFF schema and canonical mask decoder.
- [x] Run corrected target-domain profile: run `33818554862`; artifact `s-biad634-profile-33818554862`; digest `sha256:c5223353fec6c84d1745d1fd32c3dd7a4c169e38c3706fa7440b3548f49b7f3d`.
- [x] Verify the profile contains all 79 records, valid image/mask spatial agreement, channel metadata and canonical decoder provenance.
- [x] Run corrected zero-shot BBBC039 → S-BIAD634 transfer: run `33776934058`; artifact digest `sha256:dbd1a7c0e2bda5dd893a87e6e16b960155989ba1a595227a0dc28cddbe83ffe8`.
- [x] Diagnose the corrected zero-shot instance-level failure pattern; see `docs/E3_S_BIAD634_DIAGNOSIS_2026-09-04.md`.
- [ ] Obtain authoritative biological/acquisition group metadata before making group-level biological claims.

## Phase 4 — domain-robust method
- [x] Provisional 2023–2026 novelty audit.
- [x] Execute corrected E4 source-only intensity-domain-randomization evaluation across all 79 target images: run `33791838274`; artifact digest `sha256:7e6efb89b11d6d04db2eb5da257cd33cb19d93e5223c8e6c93c638308c3e9afa`.
- [x] Verify E4 artifact completeness, method record and no-target-training provenance.
- [x] Independently cross-validate the matched E4-versus-E3 comparison on the identical 79-image set under the prespecified image-level analysis protocol; verification archived in `docs/E3_E4_STATISTICAL_VERIFICATION_2026-09-04.md`.
- [x] Freeze the source-only photometric domain-randomization protocol for downstream testing; record `docs/METHOD_FREEZE_2026-09-04.md`.
- [x] Run controlled ablations.
- [x] Compare against a retained eligible conventional baseline under the matched target evaluator.
- [x] Execute the prespecified matched image-level statistical analysis for E3/E4; machine-readable result `outputs/e3_e4_statistics_2026-09-04.json` and verification record `docs/E3_E4_STATISTICAL_VERIFICATION_2026-09-04.md`.
- [x] Complete E5 aggregate integrity gate for run `33943463177`; retained gate artifact `e5-gate-33943463177` with digest `sha256:6274b9ab243536ca5d806f327c223f44b89fc4fdd65a47b947e93fe116eb0e5b`.

## Phase 5 — adaptation and external validation
- [x] Establish an explicit, scientifically honest E6 cross-dataset protocol using authoritative Aitslab-bioimaging1; preserve the locked S-BIAD634 zero-shot set as untouched.
- [x] Implement authoritative Aitslab train/development/test acquisition and normalization.
- [x] Implement frozen-E4 initialization and deterministic 1%, 5%, 10%, 25% E6 runner with provenance.
- [x] Add a fail-closed E6 GitHub Actions workflow that verifies the retained E4 artifact before execution.
- [ ] Execute few-shot adaptation at pre-registered label fractions.
- [ ] Measure annotation efficiency.
- [ ] Validate on an independent external fluorescence dataset.
- [ ] Evaluate robustness to acquisition/intensity/noise shifts.
- [ ] Evaluate failure cases and uncertainty calibration.

## Phase 6 — paper and release
- [ ] Freeze final experimental protocol.
- [ ] Complete final literature/novelty audit.
- [ ] Generate paper figures/tables directly from versioned outputs.
- [ ] Re-run complete pipeline from a clean environment.
- [ ] Audit every reported number against raw experiment artifacts.
- [ ] Release code, manifests, configurations and reproducibility instructions.
- [ ] Prepare manuscript only after evidence supports the claims.

## Current state — 2026-09-07

The corrected BBBC039 baseline, corrected S-BIAD634 zero-shot transfer, corrected E4 execution, corrected S-BIAD634 target profile, matched E3/E4 statistical verification, and E5 aggregate integrity gate remain artifact-backed as recorded above.

E6 remains **not scientifically complete**. The latest inspected E6 workflow run `34027678815` completed its 01%, 05%, and 10% fraction jobs successfully, but the 25% job `101563620168` was cancelled during the preregistered training step after the frozen-E4 identity, authoritative Aitslab-bioimaging1 acquisition, publisher split counts, and leakage guard had passed. The aggregate evidence job was therefore correctly skipped. A retry of the failed 25% job has been requested; the GitHub API is currently returning no jobs while that retry is being instantiated, so no execution or metric is claimed from the retry.

E7 remains independent and must not consume the locked S-BIAD634 zero-shot test set. No downstream release gate is promoted while E6 is incomplete. Release readiness remains unclaimed.

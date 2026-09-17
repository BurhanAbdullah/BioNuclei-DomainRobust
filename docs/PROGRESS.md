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
- [x] Execute few-shot adaptation at pre-registered label fractions; finalizer run `34312833206` aggregates the four standardized fractions from source run `34208190019`.
- [x] Measure annotation efficiency as a separate descriptive scientific analysis; machine-readable record `outputs/e6_annotation_efficiency_2026-09-17.json` and report `docs/E6_ANNOTATION_EFFICIENCY_2026-09-17.md`.
- [x] Validate on an independent external fluorescence dataset: E7 BBBC038 run `34312920549` passed.
- [x] Execute E6/E7 image-level uncertainty and failure analysis: run `34312853905`, artifact `10088988731`, 10,000 bootstrap resamples.
- [ ] Establish separate uncertainty calibration metrics beyond the retained image-level failure/uncertainty analysis.

## Phase 6 — paper and release
- [ ] Freeze final experimental protocol.
- [ ] Complete final literature/novelty audit.
- [ ] Generate paper figures/tables directly from versioned outputs.
- [x] Re-run complete pipeline from a clean environment: run `34312877852` passed.
- [ ] Audit every reported number against raw experiment artifacts.
- [ ] Release code, manifests, configurations and reproducibility instructions as the permanent public package/checkpoint.
- [ ] Prepare manuscript only after evidence supports the claims.

## Verified evidence ledger — 2026-09-17

The latest verified research revision is `2dba10e614bc5efc9bc4de66994c7c920d6667cb`. E6 finalizer run `34312833206` completed successfully and produced artifact `10088980217` (`e6-external-few-shot-final-34312833206`, digest `sha256:fad1b13ae05cfcb4cfa7f958a61b027ff84751d1ff980a6d6c5d1794106f7c34`). The aggregate uses only the four standardized E6 fraction artifacts from source run `34208190019` and records immutable dataset/config/E4 hashes, seed 42, 20 epochs, activation checkpointing and fail-closed leakage flags.

E6 annotation-budget analysis was added from the verified finalizer evidence. The four budgets are 1, 2, 3, and 8 adaptation images. AJI values are 0.068280, 0.058361, 0.053096, and 0.055426 respectively. The 1-image to 8-image descriptive change is -0.012854 absolute (-18.83%). This is not interpreted as a causal or general claim that more annotation is harmful; the executed protocol used a fixed 20-epoch budget and different adaptation subsets. The analysis remains explicitly cross-dataset and does not use the locked S-BIAD634 test set.

E7 independent BBBC038 validation passed in run `34312920549`. E6/E7 uncertainty and failure analysis passed in run `34312853905`; retained artifact `10088988731` has digest `sha256:0cbef10c50d7c254a38bf2c865d20dcac4c420010171af70a44e0e266c85d6a7` and records 10,000 bootstrap resamples plus image-level failure evidence tied to source metric hashes. Clean-environment reproduction passed in run `34312877852` with all listed verification steps successful.

No new scientific metric is inferred from documentation changes alone. Remaining release gates are: complete the outstanding Phase-2 reproducibility/qualitative audit; obtain authoritative biological/acquisition metadata for any group-level claim; establish uncertainty calibration beyond the existing image-level analysis; freeze the final experimental protocol; complete the final literature/novelty audit; generate figures/tables from versioned outputs; audit every manuscript number against raw artifacts; publish the permanent checkpoint/package; and complete the final scientific/reproducibility audit.

# Claim–Evidence Matrix — 2026-09-17

This matrix is a release-control document. It separates verified observations from interpretations and prevents a website or manuscript from presenting planned work as completed evidence.

| Claim / statement | Evidence anchor | Status | Reporting constraint |
|---|---|---|---|
| BBBC039 source-domain baseline was executed on real data | Workflow run `33768426630`; artifact `bbbc039-baseline-33768426630`; digest `sha256:ec31fba69ee40de1f86d89ac0275d4341f58ec31a41f4129b33cf2501d3ce74f` | Verified | Report exact split/checkpoint/decoder revision with the final manifest. |
| Corrected held-out BBBC039 means are Dice 0.9696520862500608, IoU 0.9411678377723045, AJI 0.9105499261289745, boundary F1 0.6911822539055567 | Same BBBC039 baseline artifact | Verified | Treat as held-out baseline values; do not generalize to other datasets. |
| S-BIAD634 target data were acquired and profiled | Provenance SHA `8285987ed4d57c46a46a55a33c1c085875ea41f429b59cde31d249741aa07ad1`; profiling run `33818554862`; artifact digest `sha256:c5223353fec6c84d1745d1fd32c3dd7a4c169e38c3706fa7440b3548f49b7f3d` | Verified | Biological/acquisition group claims require authoritative group metadata. |
| Zero-shot BBBC039→S-BIAD634 transfer was executed | Run `33776934058`; artifact digest `sha256:dbd1a7c0e2bda5dd893a87e6e16b960155989ba1a595227a0dc28cddbe83ffe8` | Verified | Use as target-domain diagnostic evidence, not universal failure/generalization. |
| E4 intensity-domain randomization was executed without target training | Run `33791838274`; artifact digest `sha256:7e6efb89b11d6d04db2eb5da257cd33cb19d93e5223c8e6c93c638308c3e9afa` | Verified | Preserve locked target evaluation and no-target-training provenance. |
| E4 vs E3 comparison was statistically evaluated under a matched image-level protocol | `docs/E3_E4_STATISTICAL_VERIFICATION_2026-09-04.md`; `outputs/e3_e4_statistics_2026-09-04.json` | Verified | Report the prespecified test and effect estimates exactly as stored. |
| E5 aggregate integrity gate passed | Run `33943463177`; artifact `e5-gate-33943463177`; digest `sha256:6274b9ab243536ca5d806f327c223f44b89fc4fdd65a47b947e93fe116eb0e5b` | Verified | Gate passage is an integrity statement, not a performance superiority claim. |
| E6 standardized 1%, 5%, 10%, 25% adaptation protocol was executed and archived | Finalizer run `34312833206`; source run `34208190019`; finalizer artifact ID `10088980217`; digest `sha256:fad1b13ae05cfcb4cfa7f958a61b027ff84751d1ff980a6d6c5d1794106f7c34` | Verified | Report the actual observed curve; do not imply monotonic improvement. |
| E6 annotation-efficiency analysis is archived | `docs/E6_ANNOTATION_EFFICIENCY_2026-09-17.md`; `outputs/e6_annotation_efficiency_2026-09-17.json` | Verified | Observed AJI values are non-monotonic; no causal 'more labels harm' claim. |
| E7 independent BBBC038 validation was executed | Run `34312920549` | Verified | Independent validation is dataset-specific; do not claim universal biological generalization. |
| E6/E7 uncertainty/failure analysis was executed | Run `34312853905`; artifact ID `10088988731`; 10,000 bootstrap resamples | Verified | Separate uncertainty calibration metrics remain a publication task if not present in the retained output. |
| Clean-environment reproduction passed | Run `34312877852` | Verified | Preserve exact environment/commit and command in the final release manifest. |
| Permanent BBBC039 checkpoint exists | Release `checkpoint-bbbc039-v1`; asset SHA-256 `7209a6990514380804210292ac208b0f3b0b0a054338a145e1916044762d7c92` | Verified | Checkpoint provenance does not imply final paper release readiness. |

## Claims that must remain open

- No 'first' or 'state-of-the-art' claim without a completed 2023–2026 literature audit.
- No universal cross-dataset, cross-modality, or biological generalization claim.
- No causal explanation for the non-monotonic E6 annotation-efficiency curve.
- No final paper numerical table until every number is generated from versioned machine-readable outputs and checked against the final evidence package.
- No Release 1.0 scientific-readiness claim while release-control checkboxes remain open.

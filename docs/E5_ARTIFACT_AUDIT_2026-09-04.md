# E5 artifact audit — 2026-09-04

## Retained run inspected

- GitHub Actions run: `33829770022`
- Workflow conclusion: `success`
- Artifact: `e5-ablations-33829770022`
- Artifact digest: `sha256:8fa4694f443208ffdc5aabe2c2e91086cfb3fc927425acb9060532797c2383f1`

## Independent artifact check

The downloaded artifact was inspected outside the Actions status summary. It contained complete 79-image metric files and provenance for:

- `no_intensity_randomization`
- `no_contrast`

The required `full_frozen_e4` directory and its evaluation/provenance files were absent. Therefore the successful workflow conclusion is **not** sufficient to accept E5 as a scientific gate.

No metric from this artifact is promoted as an E5 result in the release ledger.

## Corrective controls

The E5 runner/workflow was strengthened to:

1. pass and record the target download-manifest SHA-256 in every variant provenance record;
2. require all three preregistered variant directories (`full_frozen_e4`, `no_intensity_randomization`, `no_contrast`);
3. require 79/79 per-image evaluations and all declared aggregate metrics for every variant;
4. independently evaluate the retained corrected BBBC039 Boundary U-Net conventional comparator on the identical 79-image S-BIAD634 target set;
5. retain source artifact, checkpoint, configuration, source split, target manifest, decoder and evaluator provenance for that comparator.

The corrected runner change is commit `180aabb885a46ee2fef605f1fee2ccde12da0c2e`; the strengthened workflow change is commit `d5093c41682164a74b1b41d1d76f6e59c37bbcae`.

## Gate interpretation

E5 remains **open** until a new run passes the strengthened artifact-level checks and the resulting full-method/ablation/baseline per-image results are independently cross-validated. This audit intentionally does not infer a scientific failure from the missing directory; it identifies an artifact/release-gate integrity failure that must be corrected before acceptance.

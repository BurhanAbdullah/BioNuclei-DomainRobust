# E5 artifact audit — 2026-09-04 / updated 2026-09-05

## Earlier retained run inspected

- GitHub Actions run: `33829770022`
- Workflow conclusion: `success`
- Artifact: `e5-ablations-33829770022`
- Artifact digest: `sha256:8fa4694f443208ffdc5aabe2c2e91086cfb3fc927425acb9060532797c2383f1`

The earlier artifact contained complete 79-image metric files and provenance for `no_intensity_randomization` and `no_contrast`, but the required `full_frozen_e4` directory was absent. Its successful workflow conclusion was therefore not accepted as an E5 scientific gate.

## Corrected retained run

- GitHub Actions run: `33943463177`
- Head commit: `98cc53f9a311479e2d15d113de3aa09e70859611`
- Variant artifacts: `e5-variant-33943463177-full_frozen_e4`, `e5-variant-33943463177-no_intensity_randomization`, `e5-variant-33943463177-no_contrast`
- Aggregate artifact: `e5-gate-33943463177`
- Aggregate artifact digest: `sha256:6274b9ab243536ca5d806f327c223f44b89fc4fdd65a47b947e93fe116eb0e5b`

## Independent artifact check

The aggregate gate job completed successfully. Its retained artifact was downloaded and inspected outside the Actions status summary. It contains all three preregistered E5 variant directories, each with a checkpoint, method record, 20-epoch training history, complete 79-image `evaluation/metrics.json`, and provenance. The provenance records the source split manifest SHA-256, target manifest SHA-256, configuration SHA-256, checkpoint SHA-256, decoder/evaluator, seed and explicit `target_data_used_for_training: false`.

The aggregate job also re-evaluated the retained corrected BBBC039 Boundary U-Net comparator on the identical 79-image S-BIAD634 target set. Its retained provenance records source run `33768426630`, source artifact digest, checkpoint hash, configuration hash, source split hash, target manifest hash, decoder and evaluator, with explicit no-target-training provenance. The comparator passed the workflow's strong-baseline eligibility checks.

The aggregate gate therefore passed the preregistered E5 **integrity/completeness/comparator gate**. This is not, by itself, a claim of biological generalization or superiority.

## Corrective controls

The E5 runner/workflow was strengthened to:

1. pass and record the target download-manifest SHA-256 in every variant provenance record;
2. require all three preregistered variant directories (`full_frozen_e4`, `no_intensity_randomization`, `no_contrast`);
3. require 79/79 per-image evaluations and all declared aggregate metrics for every variant;
4. independently evaluate the retained corrected BBBC039 Boundary U-Net conventional comparator on the identical 79-image S-BIAD634 target set;
5. retain source artifact, checkpoint, configuration, source split, target manifest, decoder and evaluator provenance for that comparator;
6. download merged variant artifacts into the repository root so the archived `outputs/e5/<variant>` paths are validated at the aggregate gate.

The extraction-root defect from the prior strengthened run was corrected in commit `b31972cff9e4e32be9df201d70923177226546e2`; the corrected workflow was then executed successfully in run `33943463177`.

## Gate interpretation

E5 is now **accepted as an artifact/integrity gate** because the corrected rerun passed all preregistered variant completeness/provenance checks and the matched conventional-baseline eligibility check. Downstream statistical interpretation, failure analysis, E6 adaptation, E7 external validation, clean reproducibility and release packaging remain mandatory. No biological-group inference is made from target filenames.

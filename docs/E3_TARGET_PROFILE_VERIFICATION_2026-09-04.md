# E3 Target-Domain Profile Verification — 2026-09-04

## Verification status

**PASS for the corrected target-domain profile artifact.**

GitHub Actions run `33818554862` completed successfully for the S-BIAD634 target-domain validation workflow. The retained artifact is `s-biad634-profile-33818554862` with digest:

`sha256:c5223353fec6c84d1745d1fd32c3dd7a4c169e38c3706fa7440b3548f49b7f3d`

The artifact contains the download manifest, run provenance and `outputs/s_biad634_domain_profile.json`.

## Completeness and schema checks

- Raw image / ground-truth pairs: **79**.
- Per-image profile records: **79**.
- Image records support the observed channel-last RGB schema.
- Image and mask spatial dimensions agree for every record.
- Channel counts agree with the recorded image shapes.
- The profile records the canonical instance-mask decoder `bionuclei.masks.decode_instance_mask`.
- Annotation object counts are non-negative for every record.

## Observed target-domain properties

The verified profile reports:

- annotation objects/image: mean `98.2785`, median `38`, p90 `272`, range `12–969`;
- annotation foreground fraction: mean `0.25639`, median `0.22727`;
- median annotation area: mean of per-image medians `9520.15` pixels, with p10 `430` and p90 `23951.4`;
- image mean intensity: mean `42.9835`, median `37.3792`;
- image standard deviation: mean `34.7818`, median `36.6959`;
- p01 intensity: mean `15.9747`;
- p99 intensity: mean `148.7975`.

These values are descriptive properties of the verified target set, not evidence of a causal acquisition mechanism.

## Biological-group evidence boundary

The current verified profile contains image stems and quantitative image/annotation properties, but it does **not** contain an authoritative biological-group or acquisition-group mapping. Filename families such as `Ganglioneuroblastoma`, `Neuroblastoma`, and `normal` therefore remain identifiers for follow-up rather than declared biological strata.

No biological grouping is fabricated from filenames. Any group-level statistical claim requires an authoritative metadata mapping or an explicitly defined, non-biological filename stratum.

## Release implication

The corrected target-domain profiling gate is closed for completeness and schema integrity. The remaining E3 scientific work is to connect the verified profile to a defensible failure-mechanism analysis and to preserve the biological-group evidence boundary. The corrected E4 run is complete as an artifact-backed execution, but method freeze still requires the matched comparison, prespecified statistics, failure analysis and subsequent ablations/baselines.

# BioNuclei-DomainRobust

## Domain-Robust Nuclear Instance Segmentation for Fluorescence Bioimaging

**BioNuclei-DomainRobust** is a reproducible research project for developing and rigorously evaluating deep-learning methods for **nuclear instance segmentation under cross-domain fluorescence microscopy shift**.

> **Research question:** Can a nuclear segmentation model trained on a controlled fluorescence benchmark generalize to heterogeneous human fluorescence bioimaging without relying on data leakage or an arbitrary architecture change?

## Study at a glance

```text
BBBC039
  ↓
Boundary-aware nuclear instance segmentation
  ↓
Held-out source-domain evaluation
  ↓
Zero-shot transfer to S-BIAD634 / S-BSST265
  ↓
Domain-shift + failure-mode analysis
  ↓
Evidence-driven domain-robust method
  ↓
Ablations + strong baselines
  ↓
Few-shot adaptation
  ↓
Independent external validation
```

## Why this project matters

Fluorescence microscopy can vary substantially across instruments, staining and preparation protocols, magnification, signal-to-noise ratio, tissue context, and biological state. Strong performance on a single benchmark therefore does not establish generalization. This project makes **cross-domain transfer** the central evaluation problem and designs the eventual robustness method from measured failure modes rather than from an arbitrary architecture change.

## Public project page

**[BioNuclei-DomainRobust — public status page](docs/index.md)**

**[Research About page](docs/ABOUT.md)**

## Datasets

The repository **does not redistribute third-party datasets**. It stores acquisition instructions, manifests, integrity checks, preprocessing code, configurations, and experiment workflows. Raw data must be obtained from authoritative providers under their applicable terms.

- **BBBC039** — controlled fluorescence nuclear benchmark from the Broad Bioimage Benchmark Collection.
- **S-BIAD634 / S-BSST265** — heterogeneous human fluorescence nuclear imaging dataset used for cross-domain evaluation.
- **ORION-CRC / HTAN** — reserved as a later multimodal cancer-tissue validation direction.

## Reproducibility and validation

- Official source-domain partitions are preserved.
- Image/sample/patient-level leakage is explicitly controlled.
- Dataset provenance and accessions are recorded.
- Raw third-party data remain outside Git history.
- Every reported metric must come from a versioned experiment artifact.
- Statistical resampling is performed at the image/biological-unit level where appropriate.
- Baselines are retained before claiming improvement.
- Novelty claims are treated as hypotheses until supported by a focused literature audit.
- Failed experiments and engineering blockers are recorded rather than silently removed.

See **[Validation and Cross-Check Record](docs/VALIDATION.md)** for the current software/reproducibility checks and the remaining scientific validation gates.

## Current status

The project is under active experimental development. Verified software/data infrastructure is deliberately separated from scientific claims. Results are promoted to the research record only after the corresponding workflow artifacts have been checked.

## Research documentation

- [`docs/index.md`](docs/index.md) — public project status page.
- [`docs/ABOUT.md`](docs/ABOUT.md) — project motivation, datasets and validation policy.
- [`docs/PROGRESS.md`](docs/PROGRESS.md) — evidence-backed project ledger.
- [`docs/VALIDATION.md`](docs/VALIDATION.md) — cross-check and validation record.
- [`docs/EXPERIMENT_MATRIX.md`](docs/EXPERIMENT_MATRIX.md) — pre-specified experiment sequence and statistical rules.
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) — final paper/release gate.
- [`docs/NOVELTY_AUDIT_2026-08-15.md`](docs/NOVELTY_AUDIT_2026-08-15.md) — provisional literature/novelty audit.

## Repository structure

- `src/` — reusable Python package
- `configs/` — experiment configurations
- `scripts/` — command-line entry points
- `tests/` — unit and integration tests
- `docs/` — research protocols, validation, results and audit records
- `data/` — local-only dataset mount points; raw data are gitignored
- `outputs/` — local experiment outputs; curated results are committed intentionally

## Status policy

**No fabricated metrics. No hidden data leakage. No scientific completion marks without executable evidence.**

## License

Code in this repository is released under the MIT License. Third-party datasets retain their original licenses and access conditions.

## Repository

https://github.com/BurhanAbdullah/BioNuclei-DomainRobust

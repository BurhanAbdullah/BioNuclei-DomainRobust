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

### Why this project matters

Fluorescence microscopy can vary substantially across instruments, staining and preparation protocols, magnification, signal-to-noise ratio, tissue context, and biological state. Strong performance on a single benchmark therefore does not establish generalization. This project makes **cross-domain transfer** the central evaluation problem and designs the eventual robustness method from measured failure modes rather than from an arbitrary architecture change.

## Datasets

The repository **does not redistribute third-party datasets**. It stores acquisition instructions, manifests, integrity checks, preprocessing code, configurations, and experiment workflows. Raw data must be obtained from authoritative providers under their applicable terms.

- **BBBC039** — controlled fluorescence nuclear benchmark from the Broad Bioimage Benchmark Collection.
- **S-BIAD634 / S-BSST265** — heterogeneous human fluorescence nuclear imaging dataset used for cross-domain evaluation.
- **ORION-CRC / HTAN** — reserved as a later multimodal cancer-tissue validation direction.

## Reproducibility commitments

- Official source-domain partitions are preserved.
- Image/sample/patient-level leakage is explicitly controlled.
- Dataset provenance and accessions are recorded.
- Raw third-party data remain outside Git history.
- Every reported metric must come from a versioned experiment artifact.
- Statistical resampling is performed at the image/biological-unit level where appropriate.
- Baselines are retained before claiming improvement.
- Novelty claims are treated as hypotheses until supported by a focused literature audit.
- Failed experiments and engineering blockers are recorded rather than silently removed.

## Public research page

A concise public description of the project, scientific motivation, datasets, and reproducibility policy is available at:

**[BioNuclei-DomainRobust — About](docs/ABOUT.md)**

## Research documentation

- [`docs/PROGRESS.md`](docs/PROGRESS.md) — evidence-backed project ledger.
- [`docs/EXPERIMENT_MATRIX.md`](docs/EXPERIMENT_MATRIX.md) — pre-specified experiment sequence and statistical rules.
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) — final paper/release gate.
- [`docs/NOVELTY_AUDIT_2026-08-15.md`](docs/NOVELTY_AUDIT_2026-08-15.md) — provisional literature/novelty audit.

## Repository structure

- `src/` — reusable Python package
- `configs/` — experiment configurations
- `scripts/` — command-line entry points
- `tests/` — unit and integration tests
- `docs/` — research protocols, dataset documentation, results and audit records
- `data/` — local-only dataset mount points; raw data are gitignored
- `outputs/` — local experiment outputs; curated results are committed intentionally

## Current status

The project is under active experimental development. Verified software/data infrastructure is deliberately separated from scientific claims. Results are promoted to the research record only after the corresponding workflow artifacts have been checked.

## License

Code in this repository is released under the MIT License. Third-party datasets retain their original licenses and access conditions.

## Repository link

**https://github.com/BurhanAbdullah/BioNuclei-DomainRobust**

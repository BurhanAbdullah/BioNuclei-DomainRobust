# BioNuclei-DomainRobust

## Domain-Robust Nuclear Instance Segmentation for Fluorescence Bioimaging

**BioNuclei-DomainRobust** is a reproducible biomedical-AI research project studying whether nuclear instance segmentation learned from one fluorescence-imaging domain can transfer reliably to heterogeneous human fluorescence bioimaging.

### Research question

> Can a nuclear segmentation model trained on a controlled fluorescence benchmark generalize to heterogeneous human fluorescence bioimaging without uncontrolled annotation leakage or an arbitrary architecture change?

### Study design

```text
BBBC039
   |
   v
Boundary-aware nuclear instance segmentation
   |
   v
Held-out source-domain evaluation
   |
   v
Zero-shot transfer to S-BIAD634 / S-BSST265
   |
   v
Domain-shift + failure-mode analysis
   |
   v
Evidence-driven robustness method
   |
   +--> Ablations
   +--> Strong baselines
   +--> Few-shot adaptation
   +--> Independent external validation
```

### Datasets

The repository does **not** redistribute third-party datasets. It provides acquisition instructions, integrity checks, manifests, preprocessing code, configurations, tests, and GitHub Actions workflows so that datasets can be obtained from authoritative providers under their applicable terms.

- **BBBC039** — controlled fluorescence nuclear benchmark from the Broad Bioimage Benchmark Collection.
- **S-BIAD634 / S-BSST265** — heterogeneous human fluorescence nuclear-imaging dataset used for cross-domain evaluation.
- **ORION-CRC / HTAN** — reserved for later multimodal cancer-tissue validation after the core domain-generalization study is established.

### Reproducibility commitments

- Official source-domain partitions are preserved.
- Image/sample/patient-level leakage is explicitly controlled.
- Dataset provenance and accessions are recorded.
- Raw third-party data remain outside Git history.
- Every reported metric must come from a versioned experiment artifact.
- Statistical resampling is performed at the image/biological-unit level where appropriate.
- Baselines are retained before claiming improvement.
- Failed experiments and engineering blockers are recorded instead of silently removed.
- Novelty claims remain hypotheses until supported by a focused literature audit.

### Public repository

**https://github.com/BurhanAbdullah/BioNuclei-DomainRobust**

### Research documentation

- [`README.md`](../README.md) — project overview and quick orientation.
- [`docs/PROGRESS.md`](PROGRESS.md) — evidence-backed project ledger.
- [`docs/EXPERIMENT_MATRIX.md`](EXPERIMENT_MATRIX.md) — pre-specified experiments and statistical rules.
- [`docs/RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) — final paper/release gate.
- [`docs/NOVELTY_AUDIT_2026-08-15.md`](NOVELTY_AUDIT_2026-08-15.md) — provisional literature/novelty audit.

### Status policy

Verified software/data infrastructure is separated from scientific claims. A metric, experiment, or scientific conclusion is promoted to the project record only after the corresponding workflow artifact has been checked and its provenance is recorded.

### License

Code in this repository is released under the MIT License. Third-party datasets retain their original licenses and access conditions.

# BioNuclei-DomainRobust

## Research project

**Domain-Robust Nuclear Instance Segmentation for Fluorescence Bioimaging**

BioNuclei-DomainRobust is a reproducible research project studying how deep-learning nuclear instance segmentation models behave when fluorescence microscopy data change across acquisition and biological domains.

### Core question

> Can a model trained on a controlled fluorescence benchmark generalize to heterogeneous human fluorescence bioimaging without relying on uncontrolled annotation leakage or an arbitrary architecture change?

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
Domain-shift and failure-mode analysis
   |
   v
Evidence-driven robustness method
   |
   +--> Ablations
   +--> Strong baselines
   +--> Few-shot adaptation
   +--> Independent external validation
```

### Why this matters

Fluorescence microscopy varies across instruments, staining and preparation protocols, magnification, signal-to-noise ratio, tissue context, and biological state. A segmentation model that performs well on one benchmark can therefore fail when moved to a different imaging domain. This project treats that transfer problem as the central scientific evaluation rather than assuming that higher in-domain accuracy implies generalization.

### Data

The repository does **not** redistribute third-party datasets. Dataset download instructions, manifests, integrity checks, preprocessing code, and experiment configuration are provided so that data can be obtained from authoritative sources under their applicable terms.

- **BBBC039** — controlled fluorescence nuclear benchmark from the Broad Bioimage Benchmark Collection.
- **S-BIAD634 / S-BSST265** — heterogeneous human fluorescence nuclear imaging dataset used for cross-domain evaluation.
- **ORION-CRC / HTAN** — reserved as a later multimodal cancer-tissue validation direction rather than being used to manufacture an early novelty claim.

### Reproducibility commitments

- Dataset provenance and accessions are recorded.
- Official source-domain partitions are preserved.
- Image/sample/patient-level leakage is explicitly controlled.
- Raw third-party data remain outside Git history.
- Every reported metric must come from a versioned experiment artifact.
- Image-level statistical resampling is preferred over treating individual pixels as independent biological observations.
- Baselines are retained and compared before claiming improvement.
- Novelty is treated as a hypothesis until supported by a focused literature audit.

### Repository

The complete code, experiments, documentation, workflows, and research ledger are publicly available here:

**https://github.com/BurhanAbdullah/BioNuclei-DomainRobust**

### Project status

The repository is under active experimental development. Verified infrastructure and dataset acquisition are separated from scientific claims. Experimental results are only promoted to the project record after the corresponding workflow artifacts have been independently checked.

### Contact / citation

For reuse, cite the repository version/commit used for an experiment and cite the original dataset publications and repositories separately. Dataset ownership and licensing remain with the original data providers.

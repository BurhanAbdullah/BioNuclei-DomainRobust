# BioNuclei-DomainRobust

## Domain-Robust Nuclear Instance Segmentation for Fluorescence Bioimaging

**Public project status page**

### What is this project?

BioNuclei-DomainRobust studies whether a nuclear instance-segmentation model trained on one fluorescence-imaging domain can remain reliable when transferred to heterogeneous human fluorescence microscopy.

### Research pipeline

**BBBC039 → boundary-aware U-Net → held-out source evaluation → S-BIAD634 zero-shot transfer → domain-shift analysis → evidence-driven robustness method → ablations → few-shot adaptation → independent validation**

### Verified infrastructure

- ✅ Reproducible Python package and experiment configuration
- ✅ Automated tests and GitHub Actions CI
- ✅ BBBC039 official-data acquisition and verification workflow
- ✅ Official 100/50/50 source-domain split handling
- ✅ Boundary-aware U-Net training/evaluation workflow
- ✅ S-BIAD634 acquisition and deterministic image/ground-truth pairing
- ✅ Target-domain RGB/RGBA handling, stride-compatible padding and tiled inference
- ✅ Artifact/provenance validation gates

### Current scientific status

The project distinguishes **engineering validation** from **scientific claims**. A result is reported only after its corresponding experiment artifact has been checked.

- **Source-domain baseline:** completed on the verified BBBC039 split.
- **Target-domain transfer:** evaluation infrastructure is implemented; the current release-gate result still requires verification before being promoted as the definitive result.
- **Domain-robust method:** intentionally not frozen until target-domain failure modes are measured.

### Validation

The latest verified repository CI run completed successfully with the test suite passing. The repository also contains regression tests for the S-BIAD634 pairing logic and reproducibility gates.

### For researchers

Start here:

- [About the project](ABOUT.md)
- [Research progress ledger](PROGRESS.md)
- [Experiment matrix](EXPERIMENT_MATRIX.md)
- [Release checklist](RELEASE_CHECKLIST.md)
- [Novelty audit](NOVELTY_AUDIT_2026-08-15.md)

### Repository

[GitHub repository](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust)

### Data policy

Raw third-party datasets are not redistributed in this repository. Use the documented authoritative acquisition workflows and follow the original dataset terms.

### Reproducibility principle

No fabricated metrics. No hidden data leakage. No scientific completion marks without executable evidence.

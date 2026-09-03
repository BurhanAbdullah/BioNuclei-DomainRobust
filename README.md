# BioNuclei-DomainRobust

> **Reproducible research for domain-robust nuclear instance segmentation in fluorescence bioimaging.**

**BioNuclei-DomainRobust** evaluates cross-domain generalization from **BBBC039** to **S-BIAD634 / S-BSST265** with rigorous validation, reproducible experiments, explicit dataset provenance and evidence-driven robustness analysis.

This repository is first and foremost a **scientific research project**. Its immediate goal is to establish a rigorous, reproducible foundation for robust fluorescence nuclear instance segmentation under domain shift.

## Research objective

Fluorescence bioimaging datasets can differ substantially in acquisition conditions, biological context, staining, intensity distributions and imaging characteristics. A model that performs well in one dataset may therefore degrade when applied to another domain.

BioNuclei studies this problem systematically rather than treating cross-domain performance as an afterthought.

The current research path is:

```text
BBBC039
  |
  v
Nuclear instance segmentation
  |
  v
Controlled source-domain evaluation
  |
  v
S-BIAD634 / S-BSST265
  |
  v
Cross-domain generalization
  |
  v
Failure-mode analysis
  |
  v
Evidence-driven robustness
  |
  v
Ablation and baseline comparison
  |
  v
Few-shot adaptation
  |
  v
Independent external validation
```

The scientific workflow is designed so that robustness decisions are supported by observed failure modes, controlled experiments and held-out evaluation.

## What is evaluated

The repository focuses on **domain-robust nuclear instance segmentation in fluorescence microscopy**.

The evaluation framework considers:

- Source-domain performance on BBBC039
- Cross-domain transfer to S-BIAD634 / S-BSST265
- Instance-level segmentation quality
- Boundary quality
- Domain-shift behaviour and failure modes
- Reproducibility of preprocessing, training and evaluation
- Statistical validity at the appropriate biological/image unit
- Independent validation after protocol freeze

The repository distinguishes engineering success from scientific evidence. A workflow passing CI does not by itself establish scientific superiority.

## Reproducibility first

Every scientific result should be traceable to the code, configuration, dataset manifest and generated artifact used to obtain it.

The project therefore maintains:

- Versioned experiment configurations
- Dataset manifests and provenance records
- Explicit train/evaluation separation
- Automated validation gates
- Reproducible evaluation scripts
- Test coverage for critical code paths
- Evidence-backed progress records
- Documentation of failed experiments and engineering blockers
- A novelty audit rather than unsupported novelty claims

Raw third-party datasets are not redistributed by this repository. Users should obtain them from their authoritative sources and follow their applicable terms.

## Dataset roles

| Dataset | Role |
|---|---|
| **BBBC039** | Source-domain training and controlled evaluation |
| **S-BIAD634** | Cross-domain evaluation |
| **S-BSST265** | Cross-domain evaluation / broader robustness analysis |
| **BBBC038** | Reserved independent external validation |
| **ORION-CRC / HTAN** | Longer-term multimodal biological validation direction |

See [`docs/DATASETS.md`](docs/DATASETS.md) for the detailed dataset policy and acquisition information.

## Experimental evidence

The research is organized into explicit experimental stages rather than a single benchmark number. The experiment matrix records the intended sequence, gates and statistical rules.

- [`docs/EXPERIMENT_MATRIX.md`](docs/EXPERIMENT_MATRIX.md)
- [`docs/RESEARCH_PROTOCOL.md`](docs/RESEARCH_PROTOCOL.md)
- [`docs/VALIDATION.md`](docs/VALIDATION.md)
- [`docs/PROGRESS.md`](docs/PROGRESS.md)
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md)
- [`docs/NOVELTY_AUDIT_2026-08-15.md`](docs/NOVELTY_AUDIT_2026-08-15.md)

## Scientific model

The current segmentation research uses a **Boundary U-Net** based approach. The model is evaluated as a scientific measurement system within a controlled reproducibility protocol.

The project does not treat a language model as the segmentation engine and does not allow generated language to substitute for quantitative image analysis.

## Future direction: BioMCP

Once the **BioNuclei scientific foundation is mature and rigorously validated**, the research direction can expand toward a broader project: **BioMCP**.

The long-term idea is to develop a full-fledged **Model Context Protocol layer for bioimaging**, inspired by the general pattern of MCP-based scientific tool interoperability, that can connect LLM-based agents to established open-source imaging software and reproducible scientific workflows.

Conceptually:

```text
Researcher
    |
    v
LLM / scientific agent
    |
    v
BioMCP
    |
    +-------------------+
    |                   |
    v                   v
Image analysis       Scientific data
software             and metadata
    |                   |
    +---------+---------+
              |
              v
        Reproducible
        workflows
              |
              v
       Structured evidence
              |
              v
       Human scientific review
```

Potential integrations could eventually include open-source bioimage analysis environments for visualization, segmentation, measurement, tracking, annotation, metadata handling and workflow execution.

The important architectural boundary is that the **LLM would coordinate and communicate with scientific tools, while the underlying scientific software performs the actual image analysis and measurements**.

BioMCP is therefore a **future research direction at this stage**, not a claim that the complete platform already exists or has been validated.

### Proposed future ecosystem

The longer-term BioNuclei research programme may develop into several connected components:

| Component | Long-term role | Current status |
|---|---|---|
| **BioNuclei** | Robust bioimaging research and validation foundation | Active research |
| **BioMCP** | MCP-based interoperability between agents and bioimaging tools | Future direction |
| **BioFM** | Domain-aware foundation models for bioimaging | Future research direction |
| **BioWF** | Reproducible scientific workflow execution | Future research direction |
| **BioSkills** | Reusable scientific procedures and validated tool-use knowledge | Future research direction |

These components should only move from research direction to implemented capability when the corresponding engineering and scientific evidence exists.

## Design principles

### Scientific software remains authoritative

The agent should not replace established image-analysis algorithms. It should select, configure and coordinate them through explicit interfaces.

### Measurements remain inspectable

Quantitative results should originate from executable scientific operations with structured outputs and provenance.

### Reproducibility is part of the architecture

Dataset identity, configuration, tool versions, workflow steps and outputs should remain reconstructable.

### Evidence precedes expansion

BioMCP should be built on a validated scientific substrate rather than using an agent layer to conceal unresolved scientific uncertainty.

## Repository structure

```text
src/        Reusable scientific Python package
configs/    Experiment configurations
scripts/    Reproducibility and evaluation entry points
tests/      Unit and integration tests
docs/       Research protocols, validation and documentation
data/       Local dataset mount points; raw data are gitignored
outputs/    Local experiment outputs and curated evidence
```

## Documentation

### Research

- [`docs/EXPERIMENT_MATRIX.md`](docs/EXPERIMENT_MATRIX.md)
- [`docs/RESEARCH_PROTOCOL.md`](docs/RESEARCH_PROTOCOL.md)
- [`docs/DATASETS.md`](docs/DATASETS.md)
- [`docs/VALIDATION.md`](docs/VALIDATION.md)
- [`docs/PROGRESS.md`](docs/PROGRESS.md)
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md)
- [`docs/NOVELTY_AUDIT_2026-08-15.md`](docs/NOVELTY_AUDIT_2026-08-15.md)

### Future BioMCP direction

- [`docs/BIOMCP_MANIFESTO.md`](docs/BIOMCP_MANIFESTO.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/biomcp/README.md`](docs/biomcp/README.md)

### Research website

- [`docs/index.html`](docs/index.html)
- [`docs/research.html`](docs/research.html)
- [`docs/biomcp.html`](docs/biomcp.html)

## Scientific status

**Current priority: establish BioNuclei-DomainRobust as a rigorous, reproducible domain-generalization study.**

The future BioMCP ecosystem will be developed only after the underlying scientific work has been sufficiently validated and the corresponding engineering interfaces can be implemented and tested.

No fabricated metrics. No hidden data leakage. No unsupported novelty claims. No scientific completion marks without executable evidence.

## License

Code in this repository is released under the MIT License. Third-party datasets retain their original licenses and access conditions.

## Repository

[GitHub](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust)

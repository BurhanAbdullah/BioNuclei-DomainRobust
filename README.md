# BioMCP — Agentic AI for Bioimaging Science

> **AI orchestrates. Scientific software measures.**

This repository is the current research substrate for **BioNuclei**, a domain-robust fluorescence nuclear-segmentation study that is evolving toward **BioMCP**: an open, auditable interoperability layer connecting AI agents with bioimage-analysis tools, models, datasets, workflows, provenance and, eventually, scientific memory.

The repository name remains **BioNuclei-DomainRobust** for continuity. The long-term project identity is BioMCP; BioNuclei remains the experimental and validation foundation.

## What we are building

BioMCP is intended to make bioimaging science **discoverable, executable, inspectable and reproducible** through explicit tool interfaces rather than generated scientific claims.

```text
Researcher
    ↓
AI agent / LLM planner
    ↓
BioMCP — typed scientific tool layer
    ├── datasets & provenance
    ├── image / metadata operations
    ├── segmentation & model inference
    ├── quantitative measurements
    ├── validation & failure analysis
    └── experiment / workflow execution
    ↓
BioWF — auditable workflows
BioSkills — reusable scientific protocols
BioFM — domain-aware models
    ↓
Structured evidence + provenance
    ↓
Human scientific review
```

The core design boundary is deliberate: **the LLM plans and communicates; deterministic scientific software performs measurements.**

## The BioMCP ecosystem

| Layer | Purpose | Status |
|---|---|---|
| **BioFM** | Domain-aware vision and multimodal foundation-model research | Research direction |
| **BioMCP** | Typed interfaces between agents and bioimaging/scientific tools | Core architecture under development |
| **BioWF** | Reproducible, inspectable workflow composition | Planned architecture |
| **BioSkills** | Reusable scientific procedures, validation rules and domain guidance | Planned architecture |

These names define the research direction; they do not imply that every component is already implemented.

## Why this matters

Modern bioimage analysis already contains mature tools for visualization, segmentation, tracking, quantification, metadata and data management. The challenge is increasingly **interoperability and scientific coordination**: researchers must connect specialized tools, preserve context, choose valid protocols and reconstruct what happened.

BioMCP investigates whether an agent-accessible layer can connect these capabilities without replacing the underlying scientific software or allowing an LLM to invent measurements.

## BioNuclei: the scientific foundation

The current repository provides a concrete testbed for this architecture through cross-domain fluorescence nuclear instance segmentation.

```text
BBBC039 source domain
        ↓
Boundary-aware nuclear segmentation
        ↓
Held-out source evaluation
        ↓
Zero-shot S-BIAD634 transfer
        ↓
Domain-shift / failure-mode diagnosis
        ↓
Evidence-driven robustness method
        ↓
Ablations + strong baselines
        ↓
Few-shot adaptation
        ↓
Independent external validation
```

The scientific protocol is intentionally evidence-first. The eventual robustness method must follow measured domain failure modes rather than an arbitrary architecture change.

## Current evidence policy

The repository separates **engineering evidence**, **experimental evidence**, and **scientific claims**.

- Every reported metric must be traceable to a versioned artifact.
- Dataset provenance, manifests and split rules are recorded.
- Test data are isolated from model-selection decisions.
- Image/biological-unit level statistical analysis is preferred over pixel-level pseudo-replication.
- Failed experiments and engineering blockers remain part of the audit trail.
- A passing CI workflow proves the tested software path, not scientific superiority.
- Novelty is not claimed from architecture alone; it must be supported by mechanism, literature and held-out evidence.

## Data policy

Third-party datasets are **not redistributed**. The repository contains acquisition instructions, manifests, integrity checks, preprocessing code, configurations and workflows. Raw data must be obtained from authoritative providers under their applicable terms.

Current research datasets include:

- **BBBC039** — controlled fluorescence nuclear benchmark.
- **S-BIAD634 / S-BSST265** — heterogeneous human fluorescence nuclear imaging for cross-domain evaluation.
- **BBBC038** — reserved for independent external validation after protocol freeze.
- **ORION-CRC / HTAN** — longer-term multimodal cancer-tissue validation direction.

## Documentation

### Project direction

- [`docs/BIOMCP_MANIFESTO.md`](docs/BIOMCP_MANIFESTO.md) — the project vision, principles and scientific boundary.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — proposed BioFM/BioMCP/BioWF/BioSkills architecture and tool-contract model.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — staged path from BioNuclei research substrate to a usable BioMCP ecosystem.
- [`docs/biomcp/README.md`](docs/biomcp/README.md) — BioMCP technical direction.

### Scientific research

- [`docs/EXPERIMENT_MATRIX.md`](docs/EXPERIMENT_MATRIX.md) — pre-specified experimental sequence and statistical rules.
- [`docs/RESEARCH_PROTOCOL.md`](docs/RESEARCH_PROTOCOL.md) — research and reproducibility protocol.
- [`docs/VALIDATION.md`](docs/VALIDATION.md) — validation and cross-check record.
- [`docs/PROGRESS.md`](docs/PROGRESS.md) — evidence-backed research ledger.
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) — scientific publication/release gates.
- [`docs/DATASETS.md`](docs/DATASETS.md) — dataset roles and acquisition policy.
- [`docs/NOVELTY_AUDIT_2026-08-15.md`](docs/NOVELTY_AUDIT_2026-08-15.md) — provisional novelty/literature audit.

### Public site

The public research site presents the BioMCP vision and ecosystem, while dedicated research pages contain implementation and evidence details.

- [`docs/index.html`](docs/index.html) — public BioMCP research site.
- [`docs/research.html`](docs/research.html) — research/evidence page.
- [`docs/biomcp.html`](docs/biomcp.html) — BioMCP architecture page.

## Repository structure

- `src/` — reusable scientific Python package
- `configs/` — experiment configurations
- `scripts/` — reproducibility and evaluation entry points
- `tests/` — unit/integration tests
- `docs/` — research protocols, architecture, validation and public documentation
- `data/` — local-only dataset mount points; raw data are gitignored
- `outputs/` — local experiment outputs and intentionally curated evidence

## Scientific boundary

BioMCP is **not** an LLM that independently performs or invents scientific measurements. The intended architecture requires explicit tool execution, structured outputs, provenance and human review.

The project is also **not affiliated with Harvard University or any other institution whose architecture may have inspired comparable ecosystem thinking**. BioMCP is an independent research direction.

## Status policy

**No fabricated metrics. No hidden data leakage. No unsupported novelty claims. No scientific completion marks without executable evidence.**

## License

Code in this repository is released under the MIT License. Third-party datasets retain their original licenses and access conditions.

## Repository

[GitHub](https://github.com/BurhanAbdullah/BioNuclei-DomainRobust)

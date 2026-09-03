# BioMCP — Research Documentation

> **AI orchestrates. Scientific software measures.**

This documentation describes the transition from the **BioNuclei-DomainRobust** scientific research substrate toward the broader **BioMCP** ecosystem for agentic, reproducible bioimaging science.

## What we are building

BioMCP explores an open interoperability layer between AI agents and existing bioimage-analysis tools, models, datasets, workflows and provenance systems.

```text
Researcher
   ↓
AI agent / LLM
   ↓
BioMCP
   ↓
Scientific tools + models + data
   ↓
BioWF workflows
   ↓
Evidence + provenance
   ↓
Human review
```

The project deliberately separates **planning and explanation** from **scientific measurement**. The LLM may coordinate a task; executable scientific software produces the measurements.

## The ecosystem

- **BioFM** — domain-aware vision and multimodal model research.
- **BioMCP** — typed agent-to-scientific-tool interoperability.
- **BioWF** — reproducible workflow composition and execution.
- **BioSkills** — reusable scientific procedures, validation rules and domain guidance.

These are staged research directions. Proposed components are not described as implemented until executable code and validation evidence exist.

## BioNuclei research substrate

The current repository provides the concrete scientific environment for the architecture:

**BBBC039 → boundary-aware segmentation → source evaluation → S-BIAD634 zero-shot transfer → domain-shift diagnosis → evidence-driven robustness → ablations → few-shot adaptation → external validation.**

The segmentation research remains governed by the repository's leakage controls, experiment matrix, statistical rules, provenance requirements and release gates.

## Documentation map

### Direction and architecture

- [BioMCP Manifesto](BIOMCP_MANIFESTO.md) — vision, principles, boundaries and research question.
- [Architecture](ARCHITECTURE.md) — BioFM/BioMCP/BioWF/BioSkills design and proposed tool contracts.
- [Roadmap](ROADMAP.md) — staged implementation programme.
- [BioMCP technical README](biomcp/README.md) — implementation direction.

### Scientific research

- [About](ABOUT.md) — project identity and BioNuclei/BioMCP relationship.
- [Experimental Matrix](EXPERIMENT_MATRIX.md) — pre-specified scientific sequence and statistical rules.
- [Research Protocol](RESEARCH_PROTOCOL.md) — reproducibility and evaluation protocol.
- [Validation](VALIDATION.md) — software, dataset and scientific cross-check record.
- [Progress Ledger](PROGRESS.md) — evidence-backed development history.
- [Release Checklist](RELEASE_CHECKLIST.md) — publication/release gates.
- [Datasets](DATASETS.md) — roles, acquisition and data policy.

## Public website

The HTML site is intentionally **vision/ecosystem focused**. Detailed scientific evidence belongs on the research pages rather than the homepage.

- `index.html` — public BioMCP home.
- `architecture.html` — ecosystem architecture.
- `biomcp.html` — BioMCP layer.
- `biofm.html` — BioFM direction.
- `biowf.html` — BioWF direction.
- `bioskills.html` — BioSkills direction.
- `research.html` — BioNuclei scientific research and evidence.

## Reproducibility policy

No fabricated metrics. No hidden data leakage. No unsupported novelty claims. No scientific completion marks without executable evidence.

Third-party datasets are not redistributed. Raw data must be obtained from authoritative providers under their applicable terms.

## Independence

BioMCP is an independent research initiative. It is not affiliated with Harvard University or any other institution.

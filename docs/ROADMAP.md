# BioMCP Roadmap

This roadmap turns the BioMCP manifesto into an executable research programme. The repository should advance from a validated BioNuclei scientific substrate to a reusable agent-accessible bioimaging ecosystem.

## Stage 0 — Scientific foundation

**Purpose:** establish trustworthy scientific operations before exposing them to agents.

- maintain leakage-controlled BioNuclei experiments;
- freeze dataset roles and evaluation rules before final claims;
- preserve manifests, configurations, checkpoints and artifacts;
- complete the planned robustness, ablation, adaptation and external-validation gates;
- document failure modes and limitations.

**Exit condition:** scientific operations used by future tools are independently reproducible and auditable.

## Stage 1 — BioMCP tool contracts

**Purpose:** turn existing BioNuclei capabilities into explicit machine-readable operations.

Initial tool families:

1. dataset discovery and verification;
2. image inspection and preprocessing;
3. model loading and inference;
4. segmentation metrics;
5. domain-shift diagnostics;
6. provenance and artifact inspection;
7. experiment execution and validation.

Each tool requires input/output schemas, validation, error semantics and provenance requirements.

**Exit condition:** a human can execute every registered operation without an LLM, and the resulting artifact is sufficient to audit the operation.

## Stage 2 — BioWF

**Purpose:** compose tools into reproducible workflows.

- define workflow schemas;
- represent dependencies and intermediate artifacts;
- support deterministic replay;
- capture configuration and environment identity;
- make validation gates executable;
- expose workflow lineage to agents and humans.

**Exit condition:** a complete BioNuclei analysis can be represented and replayed as an inspectable workflow.

## Stage 3 — BioSkills

**Purpose:** encode scientific procedures around the tools.

Examples include:

- microscopy quality control;
- segmentation evaluation protocol;
- domain-shift diagnosis;
- baseline comparison;
- statistical reporting;
- provenance validation;
- failure triage.

Skills must state prerequisites and interpretation boundaries. They should guide tool use, not replace computation.

**Exit condition:** common bioimaging tasks have reusable, testable procedures with explicit validation requirements.

## Stage 4 — Agent integration

**Purpose:** allow an AI agent to use BioMCP safely.

The agent should:

- inspect available tools;
- plan a task;
- request only valid operations;
- pass structured arguments;
- observe tool outputs;
- recover from explicit failures;
- maintain provenance;
- produce evidence-linked explanations.

**Exit condition:** benchmarked agent execution meets pre-registered reliability thresholds on both valid and invalid scientific tasks.

## Stage 5 — BioFM integration

**Purpose:** connect domain-aware models without coupling the ecosystem to one model family.

- register model metadata and provenance;
- expose inference through standard tool contracts;
- support model comparison;
- evaluate robustness across datasets;
- preserve model/checkpoint identity in outputs.

**Exit condition:** models can be swapped or compared without changing the surrounding workflow contract.

## Stage 6 — Broader bioimaging ecosystem

After the core system is validated, expand toward additional open tools and datasets for visualization, segmentation, tracking, quantification, spatial analysis and multimodal imaging.

Integration should be evidence-driven: each connector needs a tested contract, provenance behaviour and failure semantics.

## Stage 7 — Scientific memory

A later direction is persistent scientific memory: reusable records of validated workflows, datasets, models, prior analyses, failures and evidence.

Memory should never become an unverified source of scientific truth. Stored knowledge must retain provenance and validation state.

## Cross-cutting release gates

No stage is considered complete merely because a demo works. Each stage should satisfy:

- reproducible implementation;
- automated tests;
- explicit schemas/contracts;
- provenance capture;
- negative/error-path testing;
- security and permission review;
- scientific validation where applicable;
- documentation sufficient for independent use.

## Identity

The repository remains named **BioNuclei-DomainRobust** during this transition. Renaming is intentionally deferred until the BioMCP implementation has enough substance to justify the broader identity.

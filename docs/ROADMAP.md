# BioMCP Roadmap

This roadmap turns the BioMCP manifesto into an executable research programme. BioNuclei is the validated scientific substrate; BioMCP is the interoperability layer that lets humans and agents invoke deterministic scientific operations without replacing them with language-model reasoning.

## Current state — Stage 1 in implementation

The repository now contains an executable BioMCP MCP server (`src/bionuclei/mcp_server.py`), an HTTP adapter (`webapp/app.py`), a browser console (`docs/use.html`) and CI smoke tests for the MCP/web surface.

The implemented public tool surface currently includes:

1. `inspect_image` — image shape, dtype and intensity statistics;
2. `predict_image` — deterministic BioNuclei inference and result bundle;
3. `evaluate_image` — inference plus package-level evaluation metrics;
4. `compute_instance_metrics` — Dice, IoU, AJI and Boundary-F1 from instance masks;
5. `read_provenance` — machine-readable execution provenance;
6. `load_result_summary` — structured result inspection.

The MCP server exposes the research protocol and dataset documentation as read-only resources. A FastAPI deployment can expose the same computational tools over HTTPS for the browser console and other clients.

The remaining research-only capabilities—authoritative dataset acquisition, registered E6/E7 experiments, domain-shift diagnostics, release-gate workflows and benchmark validation—remain controlled repository workflows. They are intentionally not exposed as arbitrary public execution endpoints.

**Stage 1 exit condition:** every registered operation is callable without an LLM, has explicit input/output/error semantics, and returns or references enough structured evidence to audit the operation. The current six-tool MVP is implemented; security, deployment and broader tool-family validation remain open until verified.

## Stage 0 — Scientific foundation

**Purpose:** establish trustworthy scientific operations before exposing them to agents.

- maintain leakage-controlled BioNuclei experiments;
- freeze dataset roles and evaluation rules before final claims;
- preserve manifests, configurations, checkpoints and artifacts;
- complete robustness, ablation, adaptation and external-validation gates;
- document failure modes and limitations.

**Exit condition:** scientific operations used by future tools are independently reproducible and auditable.

## Stage 1 — BioMCP tool contracts

**Purpose:** turn existing BioNuclei capabilities into explicit machine-readable operations.

Next expansions beyond the current MVP:

- dataset discovery and verification contracts;
- richer image inspection/preprocessing operations;
- model registry and checkpoint identity;
- domain-shift diagnostic tools;
- provenance/artifact search and verification;
- controlled experiment-validation adapters.

Each tool requires input/output schemas, validation, error semantics, security constraints and provenance requirements.

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

Examples include microscopy quality control, segmentation evaluation, domain-shift diagnosis, baseline comparison, statistical reporting, provenance validation and failure triage.

Skills must state prerequisites and interpretation boundaries. They guide tool use; they do not replace computation.

## Stage 4 — Agent integration

**Purpose:** allow an AI agent to use BioMCP safely.

The agent should inspect tools, plan a task, request only valid operations, pass structured arguments, observe tool outputs, recover from explicit failures, maintain provenance and produce evidence-linked explanations.

**Exit condition:** benchmarked agent execution meets preregistered reliability thresholds on valid and invalid scientific tasks.

## Stage 5 — BioFM integration

**Purpose:** connect domain-aware models without coupling the ecosystem to one model family.

- register model metadata and provenance;
- expose inference through standard tool contracts;
- support model comparison;
- evaluate robustness across datasets;
- preserve model/checkpoint identity in outputs.

## Stage 6 — Broader bioimaging ecosystem

After the core system is validated, expand toward additional open tools and datasets for visualization, segmentation, tracking, quantification, spatial analysis and multimodal imaging.

Each connector needs a tested contract, provenance behaviour, security boundary and failure semantics.

## Stage 7 — Scientific memory

A later direction is persistent scientific memory: reusable records of validated workflows, datasets, models, prior analyses, failures and evidence.

Stored knowledge must retain provenance and validation state and must never become an unverified source of scientific truth.

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

The repository remains named **BioNuclei-DomainRobust** during this transition. A broader BioMCP identity should only be adopted when the implementation, deployment and validation are substantive enough to justify it.

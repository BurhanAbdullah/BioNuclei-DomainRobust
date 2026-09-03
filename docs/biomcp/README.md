# BioMCP

**Agentic AI for Bioimaging**

BioMCP is a proposed open research architecture for connecting language models to deterministic bioimage-analysis tools, reproducible experiments, quantitative evaluation and scientific provenance.

## Architecture

```text
Researcher
    ↓
LLM / AI Agent
    ↓ MCP
BioMCP
    ├── Dataset & provenance tools
    ├── Bioimage preprocessing tools
    ├── Segmentation/model tools
    ├── Quantitative metric tools
    ├── Failure-analysis tools
    └── Experiment/workflow tools
    ↓
Reproducible evidence
    ↓
LLM explanation + human review
```

## Domain ecosystem

The proposed structure follows four layers:

- **BioFM** — future domain-specialized vision/multimodal foundation models.
- **BioMCP** — typed interfaces exposing bioimage and scientific-computing tools.
- **BioWF** — auditable workflows chaining tools into complete studies.
- **BioSkills** — reusable domain instructions for bioimage analysis and scientific validation.

## Current BioNuclei connection

The current E4 experiment is the scientific substrate: BBBC039 source-domain training, Boundary U-Net segmentation, source-only intensity/domain randomization, zero-shot transfer to S-BIAD634, 79-image target evaluation and versioned provenance.

The Bio-MCP layer is **not yet a completed experimental result**. It is the next research direction: implement the tool contracts around the existing workflow, then benchmark agent reliability, scientific correctness, reproducibility and failure modes.

## LLM role

The LLM is intended to plan, select tools, interpret structured outputs and communicate results. It is **not** the segmentation model. The current E4 segmentation model is Boundary U-Net. The separation is intentional: measurements should come from executable scientific tools, while language models provide orchestration and explanation.

## Research goal

Move from “chat with a microscopy image” toward an **auditable scientific agent** that can answer questions such as:

> Evaluate this segmentation model on an unseen microscopy domain, identify the failure modes, compare it against the baseline, and return the exact evidence supporting the conclusion.

The agent should achieve this through explicit tool calls, fixed protocols and provenance—not generated claims.

# BioMCP

**Agentic AI for Bioimaging Science**

> **AI orchestrates. Scientific software measures.**

BioMCP is an independent, open research architecture for connecting AI agents to deterministic bioimage-analysis tools, models, datasets, workflows and scientific provenance.

## Core problem

Bioimage analysis has a rich ecosystem of mature software, but scientific workflows often require manual coordination between applications, scripts, models and datasets. BioMCP explores a common machine-readable interface through which an AI agent can discover capabilities, construct a plan, invoke tools, inspect structured results and preserve provenance.

## Reference architecture

```text
Researcher
    │
    ▼
AI agent / LLM
    │  plan • select • explain
    ▼
┌───────────────────────────────┐
│             BioMCP            │
│ typed tools • schemas         │
│ validation • provenance       │
└───────────────┬───────────────┘
                │
     ┌──────────┼──────────┐
     ▼          ▼          ▼
  Images     Models     Datasets
  metadata   inference  provenance
     │          │          │
     └──────────┼──────────┘
                ▼
             BioWF
       reproducible workflows
                │
                ▼
       structured evidence
                │
                ▼
         human review
```

## Four-layer ecosystem

### BioFM — model layer

Domain-aware vision and multimodal foundation models for biological imagery. BioFM is a research direction, not a claim that a general-purpose foundation model is already implemented here.

### BioMCP — interoperability layer

Typed interfaces for exposing scientific operations to agents. A BioMCP tool should have explicit inputs, outputs, validation constraints, errors and provenance requirements.

### BioWF — workflow layer

Auditable composition of tools into complete experiments or analysis pipelines. A workflow should preserve the order of operations, parameters, intermediate artifacts and evaluation context.

### BioSkills — scientific procedure layer

Reusable instructions for valid scientific analysis: protocol selection, quality checks, failure handling, interpretation boundaries and domain-specific best practices.

## Tool contract principle

A future BioMCP tool should be closer to a scientific API than a conversational prompt:

```text
Tool name
  ├── purpose
  ├── input schema
  ├── output schema
  ├── preconditions
  ├── validation rules
  ├── deterministic / stochastic behaviour
  ├── software + version identity
  ├── dataset / sample provenance
  └── artifact references
```

This makes it possible to audit not only **what the agent said**, but **what the agent actually executed**.

## Example scientific task

A researcher could ask:

> Evaluate this segmentation model on an unseen microscopy domain, diagnose the dominant failure modes, compare it with the registered baseline, and return the evidence supporting the conclusion.

The intended execution is not free-form generation:

```text
question
  ↓
agent planning
  ↓
select dataset tool
  ↓
verify manifest / provenance
  ↓
select model + inference tool
  ↓
run segmentation
  ↓
run metric / failure-analysis tools
  ↓
aggregate structured results
  ↓
validate against protocol
  ↓
return evidence + provenance
```

## BioNuclei connection

**BioNuclei-DomainRobust** is the current scientific substrate. It already contains the type of executable research components that BioMCP is intended to expose: dataset acquisition and verification, segmentation, evaluation metrics, domain-shift analysis, experiment configuration, tests and provenance-oriented release gates.

The current E4 study is therefore a **research foundation**, not evidence that the complete BioMCP platform already exists.

## Reliability requirements

Future BioMCP evaluation should test at least:

- tool-selection accuracy;
- parameter correctness;
- protocol compliance;
- provenance completeness;
- reproducibility of repeated runs;
- resistance to unsupported scientific claims;
- failure detection and recovery;
- correct separation of training, validation and test data;
- agreement between natural-language summaries and machine-readable evidence.

## Explicit boundary

The LLM should not be treated as the measurement engine. It may plan and explain; the scientific tool produces the measurement. A generated answer without a corresponding executable artifact is not sufficient evidence.

## Development status

- **BioNuclei scientific substrate:** implemented and under experimental validation.
- **BioMCP architecture:** defined as the next development direction.
- **BioMCP tool contracts:** to be implemented around validated scientific operations.
- **BioWF:** planned.
- **BioSkills:** planned.
- **BioFM:** research direction.
- **Agent reliability benchmark:** planned after core tool contracts exist.

## Independence

BioMCP is an independent research initiative and is not affiliated with Harvard University or any other institution. The architecture is developed under its own research questions, interfaces, implementation and validation policy.

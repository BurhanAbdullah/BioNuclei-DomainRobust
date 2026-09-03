# BioMCP Research Manifesto

## One sentence

**BioMCP is an open, auditable interoperability layer that lets AI agents use bioimaging science without turning the language model into the scientific measurement engine.**

> **AI orchestrates. Scientific software measures.**

## The problem

Bioimaging researchers already have specialized tools for microscopy data, visualization, segmentation, tracking, quantification, metadata and statistical analysis. The bottleneck is often the coordination between them.

An agent should not need to replace those tools to make them easier to use. It should be able to discover what exists, understand the permitted inputs and outputs, execute a valid operation, preserve context and return evidence that a researcher can inspect.

## The proposition

BioMCP proposes a common scientific interface between an AI agent and the bioimaging software ecosystem.

```text
Human scientific question
          ↓
     AI agent / LLM
          ↓
        BioMCP
          ↓
  Existing scientific tools
          ↓
 Structured measurements
          ↓
 Provenance + validation
          ↓
    Human scientific review
```

## Four pillars

**BioFM** — model and representation research for biological imagery.

**BioMCP** — typed tool interoperability for agents.

**BioWF** — reproducible workflow composition.

**BioSkills** — reusable scientific procedures and validation knowledge.

## Principles

### 1. Measurement is executable

A number should have a computational origin. A segmentation metric, object count, intensity statistic or statistical result must be produced by an executable scientific operation.

### 2. Provenance is part of the result

Dataset identity, sample/image identity, software version, configuration, model/checkpoint identity and relevant parameters should remain associated with the output.

### 3. Agents are bounded

The agent may plan, select tools and explain results. It should not silently invent missing measurements, alter a registered protocol or reinterpret an unavailable artifact as evidence.

### 4. Workflows are inspectable

A useful scientific agent should be able to expose the sequence of operations that produced its answer.

### 5. Failure is first-class

Tool errors, invalid inputs, missing provenance, failed validation and scientific uncertainty should be represented explicitly rather than hidden behind fluent language.

### 6. Existing science is an asset

BioMCP should connect mature open scientific software where possible rather than rebuild every capability inside one platform.

### 7. Evidence precedes claims

A successful demo is not a scientific validation. The project requires reproducible experiments, held-out evaluation, appropriate baselines and independent validation before making performance or novelty claims.

## BioNuclei's role

BioNuclei-DomainRobust is the initial research substrate. Its domain-robust nuclear segmentation study provides real scientific operations that can be formalized as BioMCP tools: data acquisition/verification, image preparation, segmentation, quantitative evaluation, domain-shift diagnosis and provenance capture.

This gives BioMCP a concrete testbed rather than a purely conceptual interface.

## What success would look like

A researcher could provide a scientific question and receive:

1. an inspectable execution plan;
2. explicit tool calls and parameters;
3. machine-readable outputs;
4. validation checks;
5. provenance and artifact references;
6. a concise natural-language interpretation tied to that evidence;
7. clear disclosure of uncertainty and unsupported requests.

The central research question is therefore not “Can an LLM talk about microscopy?” It is:

> **Can an AI agent reliably orchestrate real bioimaging computation while preserving the conditions required for scientific trust?**

## Non-goals

BioMCP is not intended to:

- replace domain scientists;
- make unsupported autonomous scientific claims;
- hide deterministic computation behind an opaque prompt;
- redistribute restricted third-party datasets;
- claim that proposed ecosystem components are already implemented;
- equate an LLM response with experimental evidence.

## Independence

BioMCP is an independent research initiative. It is not affiliated with Harvard University or any other institution. Comparable ideas may exist across scientific-agent research; BioMCP defines its own architecture, implementation and validation programme.

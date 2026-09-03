# BioMCP — About the Project

## Vision

**BioMCP is an independent research direction for agentic AI in bioimaging.** It explores how AI agents can reliably interact with existing bioimage-analysis software, models, datasets and workflows through explicit, typed interfaces while preserving scientific provenance.

> **AI orchestrates. Scientific software measures.**

The goal is not to replace established scientific applications with a language model. The goal is to make their capabilities composable, inspectable and reproducible.

## What the ecosystem means

### BioFM

Domain-aware vision and multimodal foundation-model research for biological imagery. BioFM represents the model layer: perception, representation learning and multimodal scientific reasoning.

### BioMCP

The interoperability layer. BioMCP is intended to expose deterministic scientific capabilities as structured tools that an agent can discover and invoke with explicit inputs, outputs, constraints and provenance.

### BioWF

The workflow layer. BioWF is intended to compose BioMCP operations into reproducible scientific workflows with explicit dependencies, parameters, intermediate artifacts and validation steps.

### BioSkills

The scientific-procedure layer. BioSkills is intended to encode reusable analysis protocols, domain knowledge, validation rules and failure-handling guidance without hiding the underlying computation.

## Architectural boundary

```text
                 Researcher
                     │
                     ▼
              AI agent / LLM
          planning • selection • explanation
                     │
                     ▼
                   BioMCP
       typed tools • schemas • provenance
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   Bioimage       Models       Data/metadata
   software       & inference   & provenance
        │            │            │
        └────────────┼────────────┘
                     ▼
               BioWF workflows
                     │
                     ▼
          structured evidence/artifacts
                     │
                     ▼
              human scientific review
```

The LLM may propose a plan or select a tool, but a claim such as a Dice score, object count, segmentation mask, intensity measurement or statistical test must originate from an executable scientific operation and its recorded output.

## BioNuclei as the research substrate

The current repository, **BioNuclei-DomainRobust**, is the first concrete scientific environment for developing and testing these principles.

Its domain-robust segmentation study asks whether a model trained on a controlled fluorescence domain can generalize to heterogeneous human fluorescence microscopy without leakage or arbitrary architectural changes. The study provides real datasets, reproducibility constraints, segmentation models, quantitative metrics, provenance and failure analysis that can later be exposed through BioMCP tools.

The relationship is therefore:

```text
BioNuclei-DomainRobust
        │
        ├── scientific datasets
        ├── segmentation models
        ├── evaluation metrics
        ├── domain-shift analysis
        ├── provenance / artifacts
        └── reproducible experiments
                 │
                 ▼
              BioMCP
                 │
       agent-accessible interfaces
                 │
          BioWF + BioSkills
                 │
                 ▼
      broader bioimaging ecosystem
```

The repository name is retained for continuity. **BioNuclei is the research/validation component; BioMCP is the longer-term ecosystem identity.**

## Research philosophy

1. **Tools before claims.** Scientific measurements come from executable software.
2. **Explicit interfaces.** Inputs, outputs, schemas and constraints should be machine-readable.
3. **Provenance by construction.** Dataset, software, configuration, model and output identity should travel with an analysis.
4. **Human review remains authoritative.** Agent output is an interface to evidence, not a replacement for scientific judgment.
5. **Failure is evidence.** Failed runs and limitations remain visible.
6. **No benchmark theater.** Held-out evaluation, independent validation and pre-specified protocols matter more than attractive demos.
7. **Open interoperability.** BioMCP should connect existing scientific tools rather than force researchers into a closed stack.

## What is implemented vs proposed

**Implemented research substrate:** BioNuclei code, experiment configurations, reproducibility workflows, dataset acquisition/verification, segmentation and evaluation infrastructure, tests and provenance-oriented release gates.

**Under development / proposed:** the general BioMCP tool contracts, BioWF workflow engine, BioSkills library, BioFM model layer, agent reliability benchmarks and a broader ecosystem of tool servers.

The project will not describe proposed components as completed capabilities until executable implementations and corresponding validation evidence exist.

## Datasets and data policy

Third-party datasets are not redistributed. Acquisition instructions, manifests, integrity checks and processing workflows are maintained in the repository; users obtain data from authoritative providers under their applicable terms.

Current roles include BBBC039 as the controlled source domain, S-BIAD634/S-BSST265 for heterogeneous target-domain evaluation, BBBC038 as a later external validation benchmark, and ORION-CRC/HTAN as a longer-term multimodal direction.

## Validation policy

Software validation, dataset validation and scientific validation are separate gates. A green CI run demonstrates that the tested software path passed; it does not establish generalization or scientific superiority. Experimental results are promoted only when their artifacts, manifests, configurations, provenance and evaluation records are cross-checked.

## Independence

BioMCP is an independent research initiative. It is not affiliated with Harvard University or any other institution. Similar high-level ideas in agentic scientific infrastructure may exist elsewhere; BioMCP defines its own architecture, interfaces, experiments and validation standards.

## Documentation

- [`BIOMCP_MANIFESTO.md`](BIOMCP_MANIFESTO.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`ROADMAP.md`](ROADMAP.md)
- [`EXPERIMENT_MATRIX.md`](EXPERIMENT_MATRIX.md)
- [`VALIDATION.md`](VALIDATION.md)
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)

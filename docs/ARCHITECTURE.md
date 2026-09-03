# BioMCP Architecture

## Architectural goal

Create a composable, auditable path from a human bioimaging question to executable scientific computation and back to evidence.

```text
┌──────────────────────┐
│ Researcher           │
│ question / objective │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ AI agent / LLM       │
│ plan • select •      │
│ explain              │
└──────────┬───────────┘
           ↓
┌──────────────────────────────┐
│ BioMCP                       │
│ typed scientific tool layer  │
└──────────┬───────────────────┘
           ↓
 ┌─────────┼──────────┬─────────┐
 ↓         ↓          ↓         ↓
Data     Image      Models    Metrics /
& meta   operations  & infer.  validation
 └─────────┼──────────┴─────────┘
           ↓
┌──────────────────────┐
│ BioWF                │
│ reproducible         │
│ workflow composition │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Evidence + provenance│
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Human scientific     │
│ review               │
└──────────────────────┘
```

## Four layers

### BioFM

Model layer for domain-aware visual representation and multimodal biological reasoning. It can provide models to BioMCP, but model outputs remain subject to explicit evaluation and provenance.

### BioMCP

Interoperability layer. Each capability is exposed as a typed tool with an explicit contract.

### BioWF

Workflow layer. A workflow records a sequence of tool invocations and their dependencies, parameters and artifacts.

### BioSkills

Scientific knowledge/procedure layer. Skills encode how to choose and validate operations for a scientific task without replacing the underlying executable tools.

## Proposed tool classes

| Class | Example operation | Evidence produced |
|---|---|---|
| Dataset | discover / verify / manifest | dataset identity + manifest |
| Image | read / convert / preprocess | transformed image + parameters |
| Model | load / infer / segment | model identity + prediction artifact |
| Metric | evaluate segmentation | machine-readable metrics |
| Diagnosis | measure domain shift / failure | diagnostic tables + plots |
| Workflow | compose / execute / resume | workflow graph + artifacts |
| Provenance | record / validate lineage | provenance record |

These are architectural categories, not claims that every server or operation already exists.

## Tool contract

Every production-grade tool should specify:

```text
name
purpose
input schema
output schema
preconditions
validation rules
error semantics
software/version identity
randomness / determinism
resource requirements
provenance requirements
artifact references
```

A tool should reject invalid requests rather than relying on the LLM to remember every scientific constraint.

## Provenance model

A minimum analysis record should connect:

```text
Dataset / accession
      ↓
Manifest / sample identity
      ↓
Input artifact
      ↓
Tool + version
      ↓
Configuration / parameters
      ↓
Model + checkpoint (when applicable)
      ↓
Output artifact
      ↓
Validation result
      ↓
Human-facing interpretation
```

The exact schema will be defined during implementation and tested against the BioNuclei experiments.

## BioNuclei as the first implementation testbed

The existing BioNuclei workflow naturally maps to the architecture:

- dataset acquisition and integrity verification → Dataset tools;
- image pairing and preprocessing → Image tools;
- Boundary-aware U-Net inference → Model tools;
- Dice, IoU, AJI and boundary metrics → Metric tools;
- domain-shift and failure-mode analysis → Diagnosis tools;
- experiment manifests and provenance → Provenance tools;
- E1–E7 study protocol → BioWF workflow definitions;
- validation rules and scientific constraints → BioSkills.

The next step is to expose these operations through explicit contracts, then measure whether agents can use them correctly.

## Reliability boundary

The agent must not be the source of truth for scientific measurements. For example, when asked for a Dice score, the agent should invoke the registered metric operation and cite the resulting artifact rather than calculate or invent a value in free-form text.

Similarly, when a dataset is unavailable or a protocol precondition fails, the system should return a structured failure and explain it rather than silently substituting another experiment.

## Evaluation of the architecture

BioMCP should eventually be evaluated on:

- task completion;
- tool-selection accuracy;
- argument/schema correctness;
- protocol compliance;
- provenance completeness;
- reproducibility;
- failure detection;
- unsupported-claim rate;
- evidence-to-summary faithfulness;
- performance across heterogeneous bioimaging tasks.

A benchmark should include both successful tasks and adversarial/invalid requests.

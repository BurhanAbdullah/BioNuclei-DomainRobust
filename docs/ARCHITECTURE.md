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
┌──────────────────────────────┐
│ BioNuclei                    │
│ first scientific foundation  │
│ and implementation testbed   │
└──────────┬───────────────────┘
           ↓
 ┌─────────┼──────────┬────────────┐
 ↓         ↓          ↓            ↓
BioFM     BioWF      BioSkills   Data / tools /
models    workflows  procedures   validation
 └─────────┼──────────┴────────────┘
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

## Ecosystem order

The architecture is intentionally ordered around **BioMCP first, BioNuclei second, then the broader Bio* layers**.

1. **BioMCP** — the interoperability layer that connects agents to scientific capabilities through typed, auditable contracts.
2. **BioNuclei** — the first concrete scientific foundation and implementation testbed, providing real bioimaging data, models, evaluation, failure analysis and provenance.
3. **BioFM** — domain-aware vision and multimodal foundation-model research.
4. **BioWF** — reproducible and auditable workflow composition.
5. **BioSkills** — reusable scientific procedures, validation rules and domain guidance.

This ordering is architectural rather than a claim that every layer is already implemented. BioNuclei is the current scientific base; the other Bio* layers expand around the BioMCP interoperability boundary as they are implemented and validated.

## BioMCP

BioMCP is the central interoperability layer. Each scientific capability is exposed through a typed contract describing its purpose, inputs, outputs, constraints, validation rules, execution semantics and provenance requirements.

The agent plans and selects operations; BioMCP mediates access to them; the underlying scientific software performs the measurement.

## BioNuclei — first scientific foundation

BioNuclei is the first concrete implementation used to test this architecture against a real scientific workload.

Its workflow naturally provides the initial tool surface:

- dataset acquisition and integrity verification;
- image loading and preprocessing;
- Boundary-aware U-Net inference;
- instance separation and post-processing;
- Dice, IoU, AJI and boundary metrics;
- domain-shift and failure-mode diagnosis;
- experiment manifests and provenance;
- E1–E7 controlled research protocol.

This makes BioNuclei the **scientific foundation and testbed** for BioMCP rather than merely another ecosystem page.

## BioFM

BioFM is the model/reasoning layer for domain-aware visual representation and multimodal biological reasoning. It can provide models to BioMCP, but model outputs remain subject to explicit evaluation and provenance.

## BioWF

BioWF is the workflow layer. A workflow records a sequence of tool invocations and their dependencies, parameters and artifacts so that a scientific study can be reproduced and audited.

## BioSkills

BioSkills is the scientific knowledge/procedure layer. Skills encode how to choose and validate operations for a scientific task without replacing the underlying executable tools.

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

# Adaptive Analysis Architecture

BioNuclei can become an adaptive AI-native bioimage analysis system without turning scientific measurements into opaque LLM output. The architecture below separates **decision support** from **scientific computation**.

## Principle

```text
User question + image
        |
        v
Acquisition / input agent
        |
        v
Workflow router
        |
        +-----------------------+
        |                       |
   validated CNN           validated algorithm
        |                       |
        +-----------+-----------+
                    v
          deterministic analysis
                    |
                    v
          QA / uncertainty checks
                    |
                    v
             report builder
                    |
                    v
     human-readable + machine-readable
              + provenance
```

An agent may choose among **released, validated** routes. It must not invent a new model, silently retrain a checkpoint, alter benchmark splits, or manufacture an accuracy metric.

## Planned specialist agents

### 1. Acquisition agent

Reads supported formats such as TIFF and Nikon ND2. For ND2 it records dimensions/axes and requires an explicit or policy-defined choice of channel, Z, time and field before extracting a 2-D plane for the current 2-D model.

### 2. Analysis-planning agent

Translates a user's biological question into available analysis modules. Example: “count nuclei and compare their size” maps to `nuclei + morphology`.

### 3. Model router

Chooses a compatible **released** model from a registry using validated input-domain constraints. At present the repository has one scientific model family, Boundary U-Net; therefore the router must not pretend that multiple specialist CNNs already exist.

### 4. Quality / uncertainty agent

Runs implemented quality checks and reports warnings. It can say that a result is unusual or unsupported, but it must not convert heuristic confidence into a benchmark accuracy claim.

### 5. Report agent

Builds the human-readable report from deterministic outputs: analyzed images, instance counts, measurements, metrics where ground truth exists, warnings, model metadata and provenance.

## Current scientific model

The documented baseline is a Boundary U-Net trained on BBBC039v1 with one input channel and three semantic classes: background, nuclear interior and boundary. The baseline configuration records seed 42, 100 epochs, batch size 8, AdamW, learning rate 3e-4, weight decay 1e-5, boundary loss weight 2.0 and Dice loss weight 1.0, with horizontal/vertical flips and 90-degree rotation augmentation.

## Future model registry

A future registry can contain entries such as:

```json
{
  "id": "bionuclei-boundary-unet-v1",
  "task": "nuclear-instance-segmentation",
  "input": {"formats": ["tiff", "nd2"], "channels": 1},
  "domains_validated": ["source-domain", "independent-external"],
  "checkpoint": "immutable-release-asset",
  "metrics_artifact": "immutable-machine-readable-artifact",
  "status": "released"
}
```

Additional CNNs should only enter the registry after their own training, leakage checks, independent validation, uncertainty/failure analysis and release audit.

## Online learning boundary

User uploads are **inference inputs**, not automatic training data. An optional research-contribution path may retain a copy when the user explicitly consents. Such contributions enter a separate curation pipeline:

```text
consent -> governance -> QC -> de-duplication -> annotation
-> train/validation/test split -> training -> independent evaluation
-> provenance -> release decision
```

No public upload should silently modify the checkpoint used by another user or alter published benchmark evidence.

## Current status

- Boundary U-Net scientific model: implemented.
- Deterministic measurement path: implemented.
- ND2/TIFF input support in the community service: implemented.
- Account-scoped analysis jobs: implemented.
- Nuclei/morphology/intensity report generation: implemented.
- Adaptive multi-model routing: **planned**; only one validated model family is currently registered.
- Advanced specialist CNNs for cells/membranes/organelles/tracking/classification: **planned and validation-gated**.
- Online learning from uploads: **not enabled**.

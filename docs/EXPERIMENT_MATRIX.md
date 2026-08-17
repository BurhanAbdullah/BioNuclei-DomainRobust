# Experimental Matrix

## Objective

Establish a leakage-free source-domain baseline, quantify fluorescence-domain shift, then design the domain-robust method from observed failure modes.

## Dataset roles

| Dataset | Role | Training labels | Evaluation |
|---|---|---:|---|
| BBBC039v1 | Source domain | Official 100 images | Official 50-image validation + 50-image test |
| S-BIAD634 / S-BSST265 | Target domain | None for zero-shot | 79 expert-annotated fluorescence images |
| BBBC038 | External robustness benchmark | Not used until protocol frozen | Held-out external validation |

## Primary experiments

### E1 — Source baseline

Boundary-aware U-Net, single-channel fluorescence input, official BBBC039 train split only.

- Seed: 42 unless the experiment record explicitly changes it.
- Validation: only the official validation split.
- Final test: only once after model selection.
- Metrics: Dice, IoU, AJI, boundary F1.
- Report image-level distributions and 95% bootstrap confidence intervals.

### E2 — Zero-shot domain transfer

Use the E1 checkpoint without target-domain fine-tuning on S-BIAD634.

Report the same segmentation metrics and stratify by available biological/acquisition groups without mixing images across groups.

### E3 — Domain-shift diagnosis

Compare source validation and target performance using:

- intensity distribution shift;
- foreground/background signal statistics;
- nuclear area distribution;
- image geometry and scale;
- boundary quality;
- per-image failure rates;
- uncertainty/error correlation.

### E4 — Domain-robust method

The method is selected only after E3 identifies the dominant failure modes. The first candidate should address the measured mechanism rather than introduce an arbitrary architectural change.

### E5 — Ablation

Compare the full method against each component removed individually and against the strongest conventional baseline available under the same data split.

### E6 — Few-shot adaptation

Pre-register label fractions before reading target test results. Recommended fractions: 1%, 5%, 10%, 25%. Target test images remain isolated from adaptation.

### E7 — External validation

Use BBBC038 or another independent fluorescence dataset only after the primary method and protocol are frozen. No dataset is used to tune hyperparameters after external test evaluation begins.

## Statistical rules

- Never report a test result used to choose a hyperparameter as final test performance.
- Bootstrap confidence intervals must resample at the image level, not individual pixels.
- If multiple biological groups are available, report group-level results and avoid treating pixels as independent biological replicates.
- Record random seed, software commit, dataset manifest hash, configuration, checkpoint hash and exact evaluation command.
- Failed runs remain recorded; they are not silently overwritten.

## Novelty rule

A new architecture is not itself a novelty claim. The manuscript must identify the observed domain failure, explain the mechanism addressed by the proposed method, compare against relevant recent approaches, and demonstrate the improvement on held-out data.

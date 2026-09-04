# Domain-robust method protocol freeze

Status: frozen protocol for downstream ablation and adaptation experiments; not a final claim of superiority.
Date: 2026-09-04

## Evidence used for selection

The corrected E3 zero-shot evaluation on 79 S-BIAD634 images showed a large image-level transfer failure dominated by false-positive instance predictions and heterogeneous performance. The corrected E4 source-only intensity-domain-randomization intervention materially improved matched AJI, Dice, IoU, instance precision/recall/F1, while boundary F1 changed only slightly and with uncertainty. The prespecified matched analysis is archived in `docs/E3_E4_STATISTICAL_VERIFICATION_2026-09-04.md` and `outputs/e3_e4_statistics_2026-09-04.json`.

## Frozen intervention

For all downstream experiments until this protocol is explicitly superseded by a documented release decision, the full candidate method is **source-only photometric domain randomization** applied during source training, with no target images or target labels used for optimization.

Frozen configuration: `configs/domain_robust.yaml`.

- Seed: 42
- Input channels: 1
- Base channels: 32
- Epochs: 20 unless a downstream experiment has a separately preregistered compute budget
- Batch size: 8
- Learning rate: 3e-4
- Weight decay: 1e-5
- Boundary loss weight: 2.0
- Dice loss weight: 1.0
- Augmentation probability: 0.90
- Gain range: 0.70–1.30
- Gamma range: 0.70–1.40
- Bias range: -0.05–0.05
- Noise standard deviation: 0.02
- Contrast probability: 0.80
- Contrast range: 0.70–1.30

The E4 retained checkpoint SHA-256 is `c73ac5e61c7361b44d6db0fde85586d48286e4a4a29a6597a7821cba49061fbd` and the source configuration blob SHA recorded in the repository is `a881da56737ecf165bf165d9e41744bdfd41c4d2`.

## Freeze boundary

This freeze prevents post-hoc tuning of the intervention after observing E3/E4 target-test results. It does **not** close the overall release gate. E5 must still test the contribution of the frozen components and compare against an appropriate conventional baseline. E6 and E7 remain independent downstream gates. Any change to the frozen method requires a new dated protocol record and a new matched evaluation; prior results remain immutable.

No biological-group claim is made because the verified S-BIAD634 profile lacks authoritative biological/acquisition-group metadata.

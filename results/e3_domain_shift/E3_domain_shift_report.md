# E3 Domain-Shift Evidence Report

## Evidence basis

- Workflow run: `32132041272`
- Repository commit: `fcbbab8fad8a1893c8ff8e263d2c2fd0ffd4c580`
- Baseline run: `31995120233`
- Target inventory: 79 raw images + 79 ground-truth files
- Evaluator settings: tile size 512, overlap 32, instance IoU threshold 0.5
- Artifact was independently downloaded and inspected from the GitHub Actions run.

## Verified aggregate results

| Metric | Mean | Median |
|---|---:|---:|
| Dice | 0.318590 | 0.182267 |
| IoU | 0.242899 | 0.100271 |
| Instance precision | 0.134645 | 0.003676 |
| Instance recall | 0.150761 | 0.014925 |
| Instance F1 | 0.130463 | 0.006667 |
| AJI | 0.162513 | 0.074182 |
| Boundary F1 | 0.172483 | 0.130695 |

## Failure-mode evidence

- 39/79 images have instance F1 = 0.
- The mean predicted/target instance-count ratio is 2.824.
- The dominant instance-level failure is therefore not a simple foreground miss: the predictions are substantially over-segmented on several specimen groups, producing many false positives.
- Group-level behavior is strongly heterogeneous; this is evidence of specimen/domain sensitivity rather than a uniform performance collapse.

## Group-level diagnosis

The accompanying CSV contains the full group-level statistics. The most important patterns are:

1. **Normal specimens:** mean instance F1 is 0.027770; predicted/target instance ratio is 2.829. This indicates strong over-segmentation/false-positive pressure.
2. **Neuroblastoma:** mean instance F1 is 0.053664; predicted/target ratio is 2.917.
3. **Ganglioneuroblastoma:** mean instance F1 is 0.479106; predicted/target ratio is 0.889. Most images in this group perform substantially better, but at least one complete instance-matching failure remains.
4. **Other specimen:** mean instance F1 is 0.341105; predicted/target ratio is 5.311, indicating severe over-segmentation despite relatively strong foreground overlap.

## Interpretation

The zero-shot model is demonstrably capable of good foreground and instance matching on some target images, but transfer is unstable across specimen groups. The evidence supports an E3 conclusion of **heterogeneous domain shift with strong instance over-segmentation and group-dependent failure**, rather than a blanket claim that the source model simply fails on the target domain.

## Next experiment

E4 should therefore test robustness mechanisms against these measured failure modes, with fixed zero-shot results retained as the baseline and all adaptation/robustness changes evaluated on the same 79-image target set.

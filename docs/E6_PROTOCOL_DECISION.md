# E6 protocol decision

**Decision date: 2026-09-05**

E6 is not executed yet.

The locked E3/E4 S-BIAD634 test set contains 79 expert-annotated image/ground-truth pairs. No separate authoritative labelled S-BIAD634 adaptation pool has been retained. Therefore the project will not construct an artificial adaptation split from those 79 images.

## Frozen decision

- Preserve the 79-image S-BIAD634 zero-shot evaluation as an untouched historical test set.
- Do not reuse those images for adaptation.
- Do not infer sample/biological groups from filenames.
- Do not report E6 few-shot results until a legitimate labelled adaptation pool with independent provenance is established.
- E7 remains independent of E6 and uses the frozen E4 checkpoint.

## Candidate resolution

If an authoritative independently labelled fluorescence dataset is selected for adaptation, E6 must be explicitly reframed as **cross-dataset few-shot adaptation**. It must not be described as target-domain adaptation to S-BIAD634 unless the adaptation data are genuinely from that target domain and demonstrably disjoint from its evaluation set.

Any future E6 run must freeze its dataset, manifest, label fractions (1%, 5%, 10%, 25%), seed, training procedure, checkpoint-selection rule, and evaluation protocol before test metrics are inspected.

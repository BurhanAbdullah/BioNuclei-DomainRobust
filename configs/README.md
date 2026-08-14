# Configuration conventions

Configurations are intended to be immutable experiment specifications.

Before changing a configuration used for a reported result, create a new configuration name rather than silently modifying the old one.

Recommended naming:

- `bbbc039_baseline.yaml`
- `transfer_zero_shot_v001.yaml`
- `robust_aug_v001.yaml`
- `fewshot_01pct_v001.yaml`

Every result directory should preserve the exact configuration used to produce it.

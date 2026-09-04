# E6 leakage-safe few-shot gate

**Status: BLOCKED — 2026-09-04**

E6 must use a target-domain adaptation pool that is disjoint from the locked 79-image S-BIAD634 zero-shot test set. The current repository verifies the 79-image zero-shot set, but does not yet retain an authoritative adaptation manifest. Reusing those 79 images for adaptation would invalidate the zero-shot evaluation.

## Required evidence before E6 training

1. An authoritative adaptation manifest with stable image identifiers.
2. A retained target-test manifest for the locked zero-shot evaluation set.
3. Zero identifier overlap between the two manifests.
4. SHA-256 hashes for both manifests retained with the E6 run provenance.
5. Every adaptation and test manifest row must explicitly identify an annotation/ground-truth/mask reference; the validator now fails closed when this correspondence field is absent.
6. The E6 workflow must fail closed if either manifest is missing or overlap is non-zero.

The validator is `scripts/verify_e6_split.py`. It checks identifier uniqueness, annotation-reference presence, disjointness, minimum adaptation size, and manifest SHA-256 provenance. It does not inspect biological group labels or infer strata from filenames.

Example validation command once the manifests exist:

```bash
python scripts/verify_e6_split.py \
  --adaptation-manifest data/manifests/s_biad634_e6_adaptation.json \
  --test-manifest data/manifests/s_biad634_zero_shot_test.json
```

The validator does not create or infer an adaptation pool. It only certifies a supplied split; therefore a passing validator is necessary but not sufficient for the full E6 scientific gate.

## Release rule

No E6 metric may be promoted until the split, provenance, training procedure, evaluation set, and adaptation budget are all retained and independently cross-checked. No biological-group inference is permitted from filenames alone.

# BioNuclei output example

This directory demonstrates the **file structure and schema** returned by a local BioNuclei prediction.

These values are intentionally illustrative. They are **not benchmark measurements** and must not be cited as scientific results.

## Files

- `results.json` — run-level structured summary.
- `measurements.csv` — example per-instance measurements.
- `provenance.json` — example provenance fields.

## Real workflow

Run:

```bash
bionuclei predict \
  --input my_fluorescence_image.tif \
  --checkpoint model.pt \
  --output results/
```

The real output also contains `segmentation_mask.tif` and `overlay.tif`.

For retained benchmark evidence, use [`../../results.html`](../../results.html) rather than this example directory.

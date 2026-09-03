# BioNuclei local user guide

BioNuclei can be tested locally from the command line. The scientific model remains local and produces explicit artifacts; the website does not execute PyTorch inference.

## 1. Install

From a clean Python 3.10+ environment:

```bash
python -m pip install -e .
```

Verify the CLI:

```bash
bionuclei --help
bionuclei --version
```

## 2. Obtain a model checkpoint

The CLI requires a BioNuclei `.pt` checkpoint. Do not use an expiring GitHub Actions artifact as a permanent release asset. A versioned checkpoint must be published with a release before a public one-command installation workflow is advertised as Release 1.0.

## 3. Segment an image

```bash
bionuclei predict \
  --input my_fluorescence_image.tif \
  --checkpoint model.pt \
  --output results/
```

The output directory contains:

```text
results/
├── segmentation_mask.tif
├── overlay.tif
├── measurements.csv
├── results.json
└── provenance.json
```

`results.json` reports the number of detected instances and image shape. `measurements.csv` contains per-instance area, centroid and bounding-box measurements.

## 4. Evaluate when ground truth is available

Accuracy metrics are only meaningful when a ground-truth instance mask is supplied:

```bash
bionuclei evaluate \
  --input my_fluorescence_image.tif \
  --ground-truth ground_truth.png \
  --checkpoint model.pt \
  --output evaluation/
```

The evaluation bundle reports Dice, IoU and Boundary-F1. The research evaluation pipeline remains the authoritative path for the full benchmark protocol and AJI analysis.

## 5. Reproducibility boundary

User images are not silently treated as benchmark data. For arbitrary images, BioNuclei reports segmentation outputs and measurements, not unsupported accuracy claims. Benchmark results require a defined dataset, ground truth, frozen protocol and traceable artifacts.

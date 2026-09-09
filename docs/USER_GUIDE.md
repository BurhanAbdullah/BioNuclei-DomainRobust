# BioNuclei user guide

BioNuclei is the executable scientific product in this repository: it loads a compatible checkpoint, segments a fluorescence image, measures instances, evaluates against ground truth when supplied, and records structured provenance.

BioMCP is a separate optional interoperability layer. BioFM, BioWF and BioSkills are separate research/product directions. They are not required to use BioNuclei.

## 1. Fastest local path

Use Python 3.10+ in a clean environment:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux:      source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Verify the installation:

```bash
bionuclei --help
bionuclei --version
```

## 2. Get a compatible checkpoint

BioNuclei requires a compatible `.pt` checkpoint for prediction/evaluation. The repository does **not** advertise an expiring GitHub Actions artifact as a permanent model download.

Before Release 1.0, the project must publish a versioned checkpoint/release asset with an immutable SHA-256 digest and matching provenance. Until that exists, users should treat any locally supplied checkpoint as an explicit input rather than an official public model release.

## 3. Predict on your own fluorescence image

Input: one 2-D fluorescence TIFF image.

```bash
bionuclei predict \
  --input my_fluorescence_image.tif \
  --checkpoint model.pt \
  --output results/
```

BioNuclei produces:

```text
results/
├── segmentation_mask.tif
├── overlay.tif
├── measurements.csv
├── results.json
└── provenance.json
```

### What each file means

`segmentation_mask.tif` contains integer-labelled predicted instances, with background label 0.

`overlay.tif` is a visual inspection image.

`measurements.csv` contains one row per predicted instance with area, centroid and bounding-box measurements.

`results.json` contains structured run-level summary fields such as the image shape and number of detected instances.

`provenance.json` records the command, input/checkpoint locations, device, package identity, Python version and execution timestamp.

## 4. Evaluate against ground truth

When a ground-truth instance mask is available:

```bash
bionuclei evaluate \
  --input my_fluorescence_image.tif \
  --ground-truth ground_truth.png \
  --checkpoint model.pt \
  --output evaluation/
```

The local CLI reports:

- Dice;
- IoU;
- Boundary-F1.

The research benchmark pipeline remains authoritative for the complete experimental protocol and AJI analysis. Do not treat a local evaluation on an arbitrary image as evidence for a benchmark claim.

## 5. Use the browser console

The static public console is:

`docs/use.html`

It can connect to a separately deployed BioNuclei Web API and provides browser forms for:

1. image inspection;
2. prediction;
3. evaluation;
4. instance metrics;
5. provenance inspection;
6. structured result-summary inspection.

A GitHub Pages site cannot execute PyTorch inference by itself. The browser console therefore requires an explicitly configured HTTPS API endpoint for live inference.

The deployable backend is `webapp/app.py`, with deployment instructions in `docs/BIOMCP_DEPLOYMENT.md` and a Render recipe in `webapp/render.yaml`.

## 6. Example result bundle

See [`docs/examples/bionuclei-output/README.md`](examples/bionuclei-output/README.md) for a small text-only example of the result schema. Example values in that directory are illustrative unless a file is explicitly identified as a retained benchmark artifact.

For verified benchmark samples, see [`docs/results.html`](results.html).

## 7. Reproducibility and scientific interpretation

For any published claim, preserve together:

```text
repository commit
+ experiment configuration
+ dataset identity / manifest
+ checkpoint identity
+ random seed
+ evaluation command
+ machine-readable result
+ statistical analysis
+ provenance
```

A segmentation produced on a user image is a useful software output but is not automatically a scientific benchmark result. Accuracy claims require defined data, ground truth, protocol and traceable evidence.

## 8. Troubleshooting

### `Expected a 2-D fluorescence image`
The current inference path expects a 2-D TIFF. Convert or select a single 2-D image rather than a 3-D stack.

### `BIONUCLEI_CHECKPOINT is not configured`
This message is for the hosted web adapter. Configure the server-side `BIONUCLEI_CHECKPOINT` path to a compatible checkpoint; do not upload a checkpoint through the public web form.

### CUDA is unavailable
Use the default CPU path:

```bash
bionuclei predict --device cpu ...
```

### Prediction and ground truth shapes differ
The image and ground-truth mask must describe the same field of view and have identical spatial dimensions.

### I only have an Actions artifact
Actions artifacts are temporary evidence containers, not permanent public model releases. Follow the release/provenance records before treating a checkpoint as an official downloadable model.

## 9. Optional BioMCP use

BioMCP is separate from BioNuclei itself. Install it only when an agent/client needs the typed interoperability layer:

```bash
python -m pip install -e '.[mcp]'
bionuclei-mcp
```

For hosted Streamable HTTP, see [`docs/BIOMCP_DEPLOYMENT.md`](BIOMCP_DEPLOYMENT.md).

# BioNuclei user guide

BioNuclei is the executable scientific product in this repository: it loads a compatible checkpoint, segments fluorescence images, measures detected instances, and records structured provenance.

BioMCP is a separate optional interoperability layer. BioFM, BioWF and BioSkills are separate research/product directions and are not required to use BioNuclei.

## 1. Use BioNuclei in the browser

The public user-facing entry point is [`bionuclei-lab.html`](bionuclei-lab.html).

The intended workflow is:

```text
choose an ND2 or TIFF
→ see the selected image
→ choose the analysis
→ analyze
→ inspect original / overlay / segmentation
→ review measurements
→ download the result bundle
```

The browser interface does not expose developer-only API operations. Live inference still requires the deployed BioNuclei service to be configured by the project; GitHub Pages alone cannot run PyTorch inference.

## 2. Supported public inputs

The Lab accepts Nikon ND2 and TIFF files.

TIFF images can be previewed locally in the browser before upload. ND2 files are handled by the BioNuclei service so acquisition dimensions and selected planes can be retained explicitly.

The current scientific model is a 2-D, 1-channel fluorescence nuclear-segmentation model. Multidimensional ND2 data therefore requires an explicit 2-D analysis plane.

## 3. Get a compatible checkpoint

BioNuclei requires a compatible `.pt` checkpoint for prediction/evaluation. The project must publish a versioned checkpoint/release asset with an immutable SHA-256 digest before claiming an official public model release.

## 4. Local prediction

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

`segmentation_mask.tif` contains integer-labelled predicted instances.

`overlay.tif` is a visual inspection image.

`measurements.csv` contains one row per predicted instance with area, centroid and bounding-box measurements.

`results.json` contains the run-level result summary.

`provenance.json` records execution metadata and lineage.

## 5. Evaluation and benchmark evidence

When matching ground truth is available, the local evaluation path can calculate Dice, IoU and Boundary-F1.

The research benchmark pipeline remains authoritative for the complete experimental protocol and independent scientific evidence, including AJI and the registered E6/E7 workflows. An arbitrary user upload is not automatically benchmark evidence.

## 6. Example result bundle

See [`docs/examples/bionuclei-output/README.md`](examples/bionuclei-output/README.md) for the result schema. Example values are illustrative unless explicitly identified as retained benchmark artifacts.

For verified benchmark evidence, see [`results.html`](results.html).

## 7. Reproducibility

For a scientific claim, retain together:

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

A segmentation produced on a user image is a software output. Accuracy and generalization claims require defined data, ground truth, protocol and traceable evidence.

## 8. Troubleshooting

### The browser says the analysis service is not connected
The GitHub Pages interface is only the client. A deployed BioNuclei Web API with a validated checkpoint must be configured for live inference.

### `Expected a 2-D fluorescence image`
The current scientific inference path expects a 2-D image plane. For multidimensional ND2 acquisitions, select a specific 2-D plane before inference.

### `BIONUCLEI_CHECKPOINT is not configured`
This is a server-side deployment error. Configure the service with a validated checkpoint; do not upload a checkpoint through the public interface.

### Prediction and ground truth shapes differ
The image and ground-truth mask must describe the same field of view and have identical spatial dimensions.

## 9. Optional BioMCP use

BioMCP is separate from BioNuclei itself. Install it only when an agent/client needs the typed interoperability layer:

```bash
python -m pip install -e '.[mcp]'
bionuclei-mcp
```

For hosted Streamable HTTP, see [`BIOMCP_DEPLOYMENT.md`](BIOMCP_DEPLOYMENT.md).

# Dataset Registry

## BBBC039v1

**Role:** supervised source-domain benchmark for nuclear instance segmentation.

**Authoritative source:** Broad Bioimage Benchmark Collection (BBBC).

Official page: https://bbbc.broadinstitute.org/BBBC039

The current BBBC page identifies BBBC039 as version 1, with 200 fluorescence fields of view from the Hoechst DNA channel of U2OS cells. The published page specifies 520 x 696 pixels, 16-bit TIFF images, manually annotated nuclei, and separate image, mask, and metadata archives. It also provides the recommended train/validation/test partitions and asks users to preserve those partitions for comparability.

Repository policy:

- Record the exact download date and archive SHA-256/MD5 values in the local acquisition manifest.
- Download the official `images.zip`, `masks.zip`, and `metadata.zip` archives from the Broad data host.
- Store raw data outside Git.
- Preserve original filenames and annotations.
- Decode color-coded PNG instance masks into integer-labelled matrices without changing object identities.
- Do not alter the official train/validation/test assignment.
- Run `scripts/verify_bbbc039.py` before any training run.
- Do not report the dataset as acquired until the verifier passes on the actual files.

Expected dataset-level checks (to be verified from local files, not assumed):

- 200 image fields
- 520 x 696 pixels
- 16-bit image data
- 200 corresponding ground-truth masks
- official split counts of 100/50/50 images

## S-BIAD634

**Role:** heterogeneous human target domain for zero-shot and few-shot transfer.

**Authoritative source:** EMBL-EBI BioImage Archive.

Accession: `S-BIAD634`

Official information page: https://www.ebi.ac.uk/bioimage-archive/

Repository policy:

- Record the accession and download date.
- Preserve source metadata needed to define biological-group splits.
- Do not randomly split dependent images or patches.
- Verify annotation/image correspondence before training.

## ORION-CRC / HTAN (later phase)

**Role:** independent high-dimensional colorectal-cancer tissue validation.

Official project repository: https://github.com/labsyspharm/orion-crc

Use only after the source-to-target domain-shift study is functioning and the exact external validation question is pre-specified. The project must record the public release/accession and the terms of use for every downloaded component.

## Local directory convention

```text
data/
├── raw/
├── interim/
├── processed/
├── manifests/
└── README.md
```

No raw third-party data are committed to this repository.

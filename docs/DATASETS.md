# Dataset Registry

## BBBC039

**Role:** supervised source-domain benchmark.

**Authoritative source:** Broad Bioimage Benchmark Collection.

Official page: https://bbbc.broadinstitute.org/BBBC039

Repository policy:

- Record the exact downloaded release/version in `data/registry.json` when acquired.
- Store raw data outside Git.
- Preserve the original filenames and annotations.
- Do not alter the official train/validation/test assignment.

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

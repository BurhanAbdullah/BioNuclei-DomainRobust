# BBBC039 dataset record

## Authoritative source

- Broad Bioimage Benchmark Collection: https://bbbc.broadinstitute.org/BBBC039
- Accession: **BBBC039**
- Modality: fluorescence
- Biological system: U2OS nuclei in a chemical screen

The Broad BBBC image-set index currently lists BBBC039 as 200 fluorescence images. A published evaluation study reports 200 fields of view, 520 × 696-pixel images, and approximately 23,165 expert-annotated nuclei, with the commonly used 100/50/50 train/validation/test partition. We will verify all of these properties from the downloaded files before using them as experimental facts.

## Why it is the source domain

BBBC039 is deliberately used as the controlled/source domain. The first experiment is not intended to demonstrate cancer diagnosis. It is intended to establish a reproducible nuclear-instance-segmentation baseline before measuring transfer to a heterogeneous human fluorescence dataset.

## Acquisition

Do not commit the dataset to Git. Download it locally and record the archive digest in `download_manifest.json`.

The repository includes:

```bash
python scripts/download_bbbc039.py \
  --url '<EXACT_ARCHIVE_URL>'
```

A provenance-preserving Zenodo copy is documented in the acquisition script. If that copy is used, verify its checksum before analysis.

## Validation checklist

- [ ] Source URL recorded
- [ ] Archive checksum recorded
- [ ] ZIP integrity verified
- [ ] Image count verified from files
- [ ] Mask count verified from files
- [ ] Image dimensions verified from files
- [ ] Image dtype verified from files
- [ ] One-to-one image/mask mapping verified
- [ ] Instance IDs verified
- [ ] No empty/corrupt files
- [ ] Official partition recovered or justified
- [ ] No source-image leakage between splits

## Scientific caution

The dataset is U2OS cells from a chemical screen. It should not be described as a general human-cancer-tissue dataset. Its role in this project is controlled fluorescence nuclear segmentation and source-domain training.

# Preliminary Novelty Audit

**Status:** preliminary only. This is not a final novelty claim.

## What is already established

Recent nuclei-segmentation literature already contains substantial work on domain adaptation and domain generalization, including:

- unsupervised domain adaptation for nuclei segmentation;
- heterogeneous/open-compound domain adaptation;
- domain-generalized nuclei segmentation with foundation-model/SAM components;
- self-prompt/domain-adaptive universal nuclei segmentation.

Therefore, the following are **not sufficient novelty claims by themselves**:

- using a U-Net for nuclei segmentation;
- adding a boundary loss;
- generic stain/intensity augmentation;
- generic adversarial domain adaptation;
- generic SAM fine-tuning;
- reporting cross-dataset segmentation without a new methodological contribution.

## Specific opportunity to investigate

The proposed experimental setting is deliberately narrower than many existing histopathology domain-adaptation studies:

**source:** BBBC039v1, fluorescence/Hoechst U2OS nuclei from a controlled high-throughput experiment

**target:** S-BIAD634, heterogeneous human fluorescence nuclei spanning tissue/cell origins, preparation types, magnification, signal-to-noise, and imaging conditions.

The first scientific question is whether a source-domain model fails under this *fluorescence-to-fluorescence technical and biological shift*, and which failure modes dominate.

Only after those failure modes are measured should the method be designed. The final contribution must be differentiated from existing domain-adaptation/domain-generalization approaches and tested against strong baselines.

## Evidence checked

- Broad BBBC039 page: https://bbbc.broadinstitute.org/BBBC039
- S-BIAD634 BioImage Archive record: https://www.ebi.ac.uk/bioimage-archive/
- 2024 IJCV work on heterogeneous/open-compound domain adaptation for nuclei segmentation.
- 2025 Knowledge-Based Systems work on NuSegDG domain-generalized nuclei segmentation.
- 2025 Medical Image Analysis work on UN-SAM domain-adaptive self-prompt nuclei segmentation.
- 2023 NuSegDA work on unsupervised domain adaptation for nuclei segmentation.

## Rule for the paper

Do not use phrases such as “first”, “novel”, “state of the art”, or “foundation model” in the manuscript until the final method, datasets, baselines, and complete literature search have been frozen and independently checked.

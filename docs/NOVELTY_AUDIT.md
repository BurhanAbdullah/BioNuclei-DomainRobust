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

A fresh exact-phrase web search on 14 August 2026 for the pair `BBBC039 + S-BIAD634` returned no direct result. This is only a search observation, **not evidence that the pairing has never been studied**. The final audit must include bibliographic databases, citation chaining, code repositories, and dataset-specific papers before any novelty statement.

BBBC038 is also a useful later external benchmark because the Broad Institute describes it as a deliberately diverse fluorescence/histology nuclear dataset spanning organisms, imaging conditions, magnifications, tissue/culture contexts, and image quality. It should be considered for independent validation rather than substituted for S-BIAD634 in the first experiment.

## Current literature constraints

- Fan et al., *International Journal of Computer Vision* (2024), explicitly addresses heterogeneous/open-compound domain adaptation for nuclei segmentation and includes fluorescence-to-histopathology transfer. This makes generic cross-domain adaptation insufficient as a contribution.
- Lou et al., *Knowledge-Based Systems* (2025), NuSegDG, addresses domain-generalized nuclei segmentation using a heterogeneous-space adapter, Gaussian-kernel prompts, and a SAM-based architecture.
- Chen et al., *Medical Image Analysis* (2025), UN-SAM, addresses domain-adaptive self-prompt segmentation for universal nuclei images.
- Haq et al., *Frontiers in Big Data* (2023), NuSegDA, addresses unsupervised and semi-supervised domain adaptation for nuclei segmentation.

## Method-selection rule

Do not choose the final proposed method before the source-only baseline and zero-shot target-domain failure modes are measured. Candidate mechanisms must be selected because they address observed failure modes, not because they are fashionable components.

The final method must be compared against strong conventional and published baselines, with controlled ablations and statistical analysis across biological groups/images.

## Evidence checked

- Broad BBBC039: https://bbbc.broadinstitute.org/BBBC039
- Broad BBBC038: https://bbbc.broadinstitute.org/BBBC038
- S-BIAD634 BioImage Archive: https://www.ebi.ac.uk/bioimage-archive/galleries/S-BIAD634-ai.html
- Fan et al. (2024), IJCV: https://link.springer.com/article/10.1007/s11263-024-02004-y
- Lou et al. (2025), Knowledge-Based Systems: https://www.sciencedirect.com/science/article/pii/S0950705125006872
- Chen et al. (2025), Medical Image Analysis: https://www.sciencedirect.com/science/article/abs/pii/S1361841525001549
- Haq et al. (2023), Frontiers in Big Data: https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2023.1108659/full

## Rule for the paper

Do not use phrases such as “first”, “novel”, “state of the art”, or “foundation model” in the manuscript until the final method, datasets, baselines, and complete literature search have been frozen and independently checked.

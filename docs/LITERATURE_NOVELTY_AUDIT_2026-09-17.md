# Literature / Novelty Audit — 2026-09-17

## Scope

This audit covers recent work relevant to domain-robust nuclei/cellular instance segmentation, domain adaptation/generalization, and few-shot adaptation. It is a claim-scope audit, not a declaration of novelty.

## Recent directly relevant literature

1. **Fan et al., International Journal of Computer Vision (2024)** — *Learning to Generalize over Subpartitions for Heterogeneity-Aware Domain Adaptive Nuclei Segmentation*. The paper explicitly addresses cross-domain nuclei instance segmentation, heterogeneity, domain adaptation and style randomization. It demonstrates that domain-shift handling for nuclei segmentation is an established research area. DOI: 10.1007/s11263-024-02004-y.

2. **Keaton et al., WACV (2023)** — *CellTranspose: Few-Shot Domain Adaptation for Cellular Instance Segmentation*. The work studies few-shot adaptation for cellular instance segmentation and explicitly motivates annotation-efficient adaptation under distribution shift. This establishes that few-shot domain adaptation for cellular/nuclear instance segmentation predates the current BioNuclei work.

3. **Lou et al., arXiv (2024), Knowledge-Based Systems (2025)** — *NuSegDG: Integration of Heterogeneous Space and Gaussian Kernel for Domain-Generalized Nuclei Segmentation*. The work targets domain-generalized nuclei segmentation across multiple nuclei datasets and uses a foundation-model-based adaptation strategy. It establishes a strong recent domain-generalization baseline and makes broad 'domain-generalizable' claims in the nuclei segmentation literature. DOI: 10.1016/j.knosys.2025.113641; arXiv:2408.11787.

4. **Chen et al., Medical Image Analysis (2025)** — *UN-SAM: Domain-adaptive self-prompt segmentation for universal nuclei images*. The work addresses domain-adaptive nuclei segmentation using self-prompting and domain-aware representation components. This further reinforces that recent nuclei segmentation research includes explicit cross-domain/generalization mechanisms. DOI: 10.1016/j.media.2025.103607.

5. **Guo et al., Journal of Computer Science and Technology (2025)** — *Unsupervised Adversarial Domain Adaptation with Hierarchical Semantic Consistency for Cross-Modal Nuclei Detection*. This work addresses cross-modal nuclei detection using unsupervised domain adaptation and semantic consistency. DOI: 10.1007/s11390-025-4324-4.

## Implications for BioNuclei claims

- Do **not** claim that BioNuclei is the first domain-generalization, domain-adaptation, or few-shot nuclei segmentation method.
- Do **not** claim that style/intensity randomization itself is a new concept for domain robustness; recent nuclei-domain work already uses style randomization and related appearance perturbation strategies.
- The defensible contribution must instead be stated in terms of the exact BioNuclei experimental protocol and implementation: a frozen source-domain segmentation workflow, controlled photometric/intensity-domain randomization, locked target evaluation, matched image-level comparisons, explicit ablations, few-shot target adaptation, and independent BBBC038 validation, subject to the retained evidence.
- E6 should be described as annotation-budget evaluation under the declared protocol, not as proof that more annotations monotonically improve performance. The retained E6 results are non-monotonic and should be reported as observed.
- E7 should be described as independent validation on BBBC038. It should not be generalized to universal biological or cross-modality robustness.
- The paper should explicitly position BioNuclei against both classical domain-adaptation methods and recent foundation-model/domain-generalization approaches such as NuSegDG and UN-SAM.

## Remaining novelty work

This audit narrows unsupported novelty language but does not establish a unique literature gap by itself. Before submission, the manuscript should include a final database-search audit covering 2023–2026 publications/preprints, exact terminology for photometric/intensity randomization in nuclei segmentation, and the closest experimental protocols. Any novelty statement should be limited to what that final search and the retained BioNuclei evidence jointly support.

## Primary sources

- Fan et al. (2024), IJCV, DOI 10.1007/s11263-024-02004-y.
- Keaton et al. (2023), WACV, *CellTranspose: Few-Shot Domain Adaptation for Cellular Instance Segmentation*.
- Lou et al. (2024/2025), NuSegDG, arXiv:2408.11787; Knowledge-Based Systems, DOI 10.1016/j.knosys.2025.113641.
- Chen et al. (2025), UN-SAM, Medical Image Analysis, DOI 10.1016/j.media.2025.103607.
- Guo et al. (2025), JCST, DOI 10.1007/s11390-025-4324-4.

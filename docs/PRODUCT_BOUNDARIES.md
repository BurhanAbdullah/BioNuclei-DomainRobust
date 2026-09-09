# Product boundaries

BioNuclei-DomainRobust contains five related but explicitly separate product/research tracks. They share the repository infrastructure but must not be presented as one implemented system.

## 1. BioNuclei

**Role:** the active scientific research and executable bioimage-analysis package.

**Owns:**
- Boundary U-Net model and inference code;
- dataset manifests and scientific protocols;
- E1–E7 experiments and their gates;
- uncertainty/failure/statistical analysis;
- reproducibility and provenance checks;
- user-facing CLI and deterministic result bundles;
- verified scientific results and release evidence.

**Primary pages:** `bionuclei.html`, `research.html`, `datasets.html`, `results.html`.

**Scientific boundary:** BioNuclei is the measurement engine. Scientific numbers must come from executable code and retained evidence, not from an LLM or the ecosystem products below.

## 2. BioMCP

**Role:** an interoperability layer for exposing validated BioNuclei/scientific operations to agents through typed tools and structured resources.

**Owns:**
- MCP tool contracts;
- local/hosted MCP transport;
- schema and protocol integration;
- tool discovery and structured invocation.

**Does not own:** scientific claims, model training, benchmark truth, or experiment tuning.

**Primary pages:** `biomcp.html`, `use.html`, `docs/BIOMCP_DEPLOYMENT.md`.

## 3. BioFM

**Role:** a separate future/research direction for domain-aware biological vision/foundation models.

**Owns:** model-family research questions, registration concepts, and model interoperability plans.

**Does not own:** the current BioNuclei model or its benchmark results.

**Primary page:** `biofm.html`.

## 4. BioWF

**Role:** a separate workflow-composition direction for versioned, replayable and auditable scientific workflows.

**Owns:** workflow schemas, lineage, orchestration concepts and deterministic replay design.

**Does not own:** the current BioNuclei experiment results.

**Primary page:** `biowf.html`.

## 5. BioSkills

**Role:** a separate scientific-procedure direction for reusable, validated analysis procedures and failure-handling rules.

**Owns:** protocol guidance, prerequisites, interpretation boundaries and procedure contracts.

**Does not own:** the measurement implementation or benchmark metrics.

**Primary page:** `bioskills.html`.

## Presentation rule

The public website and documentation should always use the five names as distinct headings/products. Shared branding is acceptable; merged claims are not.

A statement such as “BioNuclei implements X” must refer to the BioNuclei code and retained evidence. A statement such as “BioMCP enables X” must refer to the MCP interface. Planned BioFM/BioWF/BioSkills capabilities must be labeled as planned until their implementation and validation gates are actually complete.

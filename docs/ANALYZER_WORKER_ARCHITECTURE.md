# BioNuclei Analyzer Worker Architecture

## Decision status

**Proposed target; not deployed.**

The production analyzer currently executes the scientific worker inside the web service process. This document records the evidence-based target architecture so a future migration can be reviewed without implying that a provider has already been configured or deployed.

## Current reliability boundary

The public analyzer API creates asynchronous jobs, but the current implementation still relies on the `community` service's in-process worker path. The production API also replaces failure cleanup at import time so a failed job remains queryable while transient artifacts are removed.

The intended failure contract is:

1. accept and validate the upload;
2. create an ownership-scoped job;
3. execute the existing scientific pipeline;
4. persist truthful job state/progress;
5. on failure, delete transient image/result artifacts but retain a minimal `failed` job record long enough for polling to return the actual failure state;
6. on success, expose the report/preview/download artifacts;
7. delete or expire transient artifacts according to the existing retention policy.

A polling timeout must never be used as a substitute for a known backend failure.

## Preferred target: independent Cloud Run Job worker

Cloud Run Jobs is the current preferred candidate because Google's current pricing documentation lists a free monthly allowance of **240,000 vCPU-seconds** and **450,000 GiB-seconds** for Jobs, with Mumbai, Delhi and Singapore among the listed regions. New Google Cloud customers currently receive **$300 in free credits**. These facts are provider limits, not evidence that BioNuclei is deployed there.

The proposed separation is:

```text
GitHub Pages analyzer
        |
        v
Supabase account/guest identity
        |
        v
lightweight job API / durable job state
        |
        +---- transient input/result storage
        |
        v
Cloud Run Job worker
        |
        +--> validation
        +--> ND2 selection
        +--> QC / adaptive gate
        +--> verified Boundary U-Net inference
        +--> deterministic instance separation
        +--> measurements
        +--> supported QC / uncertainty
        +--> evidence-constrained expert agents
        +--> report packaging
        |
        v
truthful job completion/failure state
```

The worker must receive an explicit job identifier and an authenticated/authorized reference to the transient input. It must not receive or infer another user's job data.

## Why not move Boundary U-Net into Supabase Edge Functions

Current Supabase hosted Edge Function limits are **256 MB memory**, **150 seconds wall-clock on the Free plan**, and **2 seconds CPU time per request**. Those limits are not an appropriate execution boundary for the existing PyTorch Boundary U-Net pipeline.

Edge Functions can remain useful for lightweight authentication/job-control operations if needed; they should not own the scientific inference workload.

## Why ZeroGPU is not the primary production API

Current Hugging Face documentation describes free personal ZeroGPU Spaces as Gradio-only, with up to two free personal ZeroGPU Spaces and approximately **5 minutes/day** of visitor quota. That can be useful for experiments, but it does not match the analyzer's authenticated asynchronous API contract or predictable production execution needs.

## Modal alternative

Modal remains a credible alternative. Its current Starter plan includes **$30/month free compute**, and its academic program advertises grants of up to **$10,000** for graduate students, labs, and researchers. Actual use still requires an eligible Modal workspace/credit grant; no BioNuclei deployment is implied here.

## Non-negotiable migration invariants

A worker migration must preserve all of the following:

- Supabase account and guest authentication semantics;
- strict `job_id + owner` authorization on every job/file operation;
- transient image handling;
- one-hour result retention unless the product policy changes explicitly;
- truthful queued/running/completed/failed states;
- durable progress based on real pipeline milestones rather than elapsed-time estimates;
- verified released Boundary U-Net checkpoint provenance;
- no user-analysis update of model weights;
- deterministic instance separation and measurement behavior;
- existing report/preview/download semantics;
- explicit deletion and expiry behavior;
- failure-state retention sufficient for the client to display the actual backend error;
- no fallback to an unverified checkpoint when the released checkpoint is unavailable.

## Required deployment evidence before calling the migration complete

A future implementation is not considered deployed until all of these are directly verified:

1. provider project/workspace exists and is eligible for the claimed free/free-credit allowance;
2. worker image/build completes from a pinned repository commit;
3. deployed worker revision/job configuration identifies that exact commit/image;
4. job API and worker exchange authenticated ownership-safe job references;
5. TIFF and ND2 jobs complete successfully using the verified released checkpoint;
6. progress transitions correspond to actual pipeline artifacts/states;
7. failed inference leaves a queryable failed job and removes transient artifacts;
8. unauthorized and cross-owner access is rejected;
9. deletion and expiry remove transient artifacts;
10. concurrent jobs do not corrupt another job's state or files;
11. live endpoint behavior and the GitHub Pages frontend are tested against the deployed commit;
12. no claim is made about datasets, training corpus size, metrics, or model provenance without repository evidence.

## External prerequisite

The main repository can be prepared without provider credentials. Actual Cloud Run deployment requires an eligible Google Cloud project/account with billing enabled or otherwise eligible to use the documented free credits/free tier. Until that external prerequisite is available, repository-side worker packaging, contract tests, and migration documentation can proceed, but deployment must remain explicitly unclaimed.

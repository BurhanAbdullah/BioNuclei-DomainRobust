# Deploy BioNuclei for public use

This deploys the **BioNuclei Web API** used by the public website. It does not deploy BioMCP, BioFM, BioWF or BioSkills.

## One-click Render deployment

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/BurhanAbdullah/BioNuclei-DomainRobust)

Render reads the repository Blueprint and creates the `bionuclei-api` Docker web service.

## Required model checkpoint

The service deliberately starts in a degraded state until `BIONUCLEI_CHECKPOINT` points to a **validated permanent BioNuclei checkpoint**. Do not invent or substitute a checkpoint — only publish one that a CI run already produced and that `docs/PROGRESS.md` records as verified.

### Promote a verified CI artifact to a permanent release

CI baseline runs (`bbbc039-baseline-*`) produce trained checkpoints, but Actions artifacts expire and are not treated as permanent releases. Promote a verified artifact only through the repository release procedure:

```bash
gh auth login
scripts/publish_checkpoint_release.sh <run-id> checkpoint-bbbc039-v1
```

The script downloads `last.pt`, records its SHA-256, and publishes the checkpoint as a versioned GitHub Release asset.

### Configure the Render service

Set:

```text
BIONUCLEI_CHECKPOINT=/opt/models/bionuclei.pt
BIONUCLEI_CHECKPOINT_URL=https://github.com/<repo>/releases/download/checkpoint-bbbc039-v1/bionuclei_bbbc039.pt
BIONUCLEI_CHECKPOINT_SHA256=<sha256 printed by the publish script>
```

The container startup entrypoint fetches and verifies the checkpoint when it is not already mounted at `BIONUCLEI_CHECKPOINT`.

Redeploy and verify:

```text
https://YOUR-SERVICE.onrender.com/health
```

with:

```json
{
  "status": "ok",
  "scientific_engine": "bionuclei-domainrobust",
  "checkpoint_configured": true
}
```

## Connect the website

The public user experience is the **BioNuclei Lab** at [`bionuclei-lab.html`](bionuclei-lab.html). Users should not enter API URLs or call individual developer operations.

The static GitHub Pages site is the client. The deployed BioNuclei Web API performs the PyTorch inference and returns the analysis result.

## Security and scientific boundary

The public adapter accepts bounded image uploads and exposes only the supported BioNuclei analysis workflow. It does not accept arbitrary shell commands, arbitrary checkpoint uploads, or mutation of authoritative benchmark evidence.

Registered E6/E7 research workflows remain controlled scientific experiments and are not exposed as public buttons.

# Deploy BioNuclei for public use

This deploys the **BioNuclei Web API** used by the public website. It does not deploy BioMCP, BioFM, BioWF or BioSkills.

## One-click Render deployment

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/BurhanAbdullah/BioNuclei-DomainRobust)

Render reads the repository Blueprint and creates the `bionuclei-api` Docker web service.

## Required model checkpoint

The service deliberately starts in a degraded state until `BIONUCLEI_CHECKPOINT` points to a **validated permanent BioNuclei checkpoint**. The repository does not currently ship a permanent `.pt` release asset, so do not invent or substitute a checkpoint.

In Render, set:

```text
BIONUCLEI_CHECKPOINT=/opt/models/bionuclei.pt
```

Then provide the validated checkpoint at that path using the deployment mechanism selected for the service. Keep the checkpoint hash in the release manifest and verify `/health` reports `checkpoint_configured: true` before connecting the public console.

## Connect the website

After the service is live, copy its HTTPS URL and paste it into the **API base URL** field on [`use.html`](use.html).

The static GitHub Pages site cannot run PyTorch by itself. It is the client interface; the deployed BioNuclei Web API performs the deterministic computation.

## Health check

Open:

```text
https://YOUR-SERVICE.onrender.com/health
```

Expected healthy response shape:

```json
{
  "status": "ok",
  "scientific_engine": "bionuclei-domainrobust",
  "checkpoint_configured": true
}
```

## Security and scientific boundary

The public adapter accepts bounded image/JSON uploads and exposes only the defined BioNuclei operations. It does not accept arbitrary shell commands, arbitrary checkpoint uploads, or mutation of authoritative benchmark evidence.

Registered E6/E7 research workflows remain controlled scientific experiments and are not exposed as public buttons.

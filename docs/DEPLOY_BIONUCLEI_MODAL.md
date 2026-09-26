# BioNuclei production analyzer — Modal

The production analyzer now has a Modal deployment path for the expensive scientific workload. This is designed to replace the memory-constrained Render community worker after validation.

## Architecture

```text
GitHub Pages
    |
    | Supabase account bearer token / ephemeral guest token
    v
Modal FastAPI web function
    |
    | asynchronous FunctionCall.spawn()
    v
Modal L4 GPU worker
    |
    +--> Boundary U-Net inference
    +--> instance measurements
    +--> 8 deterministic evidence-constrained specialist agents
    +--> HTML/JSON/PDF report + downloadable result bundle
```

The browser never receives a Modal credential. Supabase remains the account identity provider. Guest identity is a high-entropy token kept by the browser and represented server-side only by a SHA-256-derived owner id.

## One-time Modal setup

Install the current Modal CLI and authenticate locally:

```bash
python -m pip install -U modal
modal setup
```

Create a secret containing the existing Supabase project values:

```bash
modal secret create bionuclei-supabase \
  SUPABASE_URL="https://YOUR-PROJECT.supabase.co" \
  SUPABASE_PUBLISHABLE_KEY="YOUR-PUBLISHABLE-KEY"
```

Do **not** place a Supabase service-role key in this repository or in the browser.

## Deploy

From the repository root:

```bash
modal deploy modal_app.py
```

The deployment builds the scientific image and verifies the immutable public checkpoint by SHA-256 before the worker can run. The current pinned checkpoint is:

```text
release: checkpoint-bbbc039-v1
asset: bionuclei_bbbc039.pt
sha256: 7209a6990514380804210292ac208b0f3b0b0a054338a145e1916044762d7c92
```

The app exposes a public Modal web URL. Record that URL; it is the only value that must be placed into the static website configuration when the migration is accepted.

## Verify before switching the website

Run:

```bash
curl -fsS https://YOUR-MODAL-ENDPOINT.modal.run/health
```

Expected essentials:

```json
{
  "status": "ok",
  "scientific_engine": "bionuclei-domainrobust",
  "checkpoint_configured": true,
  "gpu_worker": "L4"
}
```

Then perform an end-to-end browser test with a small known TIFF fixture and verify all of the following:

1. `/guest-session` returns an ephemeral token.
2. `/analyze` returns a job id immediately rather than holding the HTTP request open for inference.
3. `/jobs/{id}/progress` advances through planning, GPU inference, measurements, expert review and packaging.
4. `/jobs/{id}` returns the completed result for the same owner and returns 404 for a different owner.
5. `expert_agents.json` contains all eight deterministic specialist outputs.
6. The segmentation mask, overlay, CSV and HTML/JSON/PDF report are downloadable.
7. The ZIP archive contains results only; it must **not** contain the uploaded TIFF/ND2 input.
8. The source image is deleted from the Modal Volume after processing.
9. DELETE removes the job, archive and result files.
10. Expiry cleanup removes result artifacts and job metadata.
11. An intentionally invalid/blocked input produces a truthful `failed` job state rather than a polling 404 or a generic "connection interrupted" message.

Only after these checks pass should `docs/assets/bionuclei-config.js` be switched from the Render endpoint to the Modal endpoint. Keep Render available until the complete Modal path has passed these checks.

## Operational notes

- The GPU worker is asynchronous and uses Modal FunctionCall semantics, so browser polling is independent of inference execution.
- The worker is configured with an L4 GPU, 4 CPU cores, 16 GiB memory, 30-minute timeout and one retry.
- A durable Modal Dict holds job metadata. The attached Volume holds transient input/result files.
- Result retention is one hour by default; the scheduled cleanup function runs hourly.
- Uploaded source images are never included in result ZIP archives.
- The public checkpoint is downloaded and SHA-256 verified during image build; users cannot upload or replace model weights.
- The model weights are not updated during user analysis.

## Cost expectation

Modal's Starter plan currently includes $30/month of free compute credit; GPU usage consumes that credit according to actual usage. This is a credit allowance, not unlimited free GPU compute. Check current Modal pricing before production launch.

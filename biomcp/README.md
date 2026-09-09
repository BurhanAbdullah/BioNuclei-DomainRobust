# BioMCP

BioMCP is the interoperability product for connecting AI agents and developer tools to validated biomedical/bioimaging capabilities.

**BioNuclei is a separate scientific product.** BioMCP does not reimplement segmentation, measurement, evaluation, training, or benchmark logic; it launches and exposes those capabilities through MCP.

## Quick start

Install the BioNuclei backend with its MCP extra, then install/use the BioMCP CLI:

```bash
python -m pip install -e '.[mcp]'
biomcp --version
biomcp list
biomcp doctor
biomcp install --dry-run
biomcp install
```

Launch the BioNuclei MCP server over stdio:

```bash
biomcp run bionuclei
```

The generated client configuration uses:

```json
{
  "mcpServers": {
    "biomcp_bionuclei": {
      "command": "bionuclei-mcp",
      "args": []
    }
  }
}
```

## Canonical MCP surface

BioMCP keeps a small canonical surface rather than duplicating every underlying implementation detail:

| Tool | Purpose |
|---|---|
| `inspect_image` | Inspect image shape, dtype and intensity statistics |
| `predict_image` | Run the validated BioNuclei inference bundle |
| `evaluate_image` | Run inference and supported image-level metrics |
| `compute_instance_metrics` | Compute Dice, IoU, AJI and Boundary-F1 from masks |
| `read_provenance` | Read machine-readable provenance |
| `load_result_summary` | Read structured result summaries |

Read-only resources expose the research protocol and dataset-role documentation.

## Transports

- **stdio** for local MCP clients.
- **Streamable HTTP** for hosted agent clients.

The two transports expose the same tool registry.

## Client configuration

`biomcp install` writes or updates an `mcpServers` entry without deleting unrelated configuration keys. Use `--dry-run` to preview and `--path` to target an explicit JSON file.

The installer is intentionally lightweight: it configures the BioNuclei server rather than hiding the scientific engine inside BioMCP.

## Runtime boundary

BioMCP can orchestrate tools; it must not invent metrics, select benchmark images, tune a test set, change registered experiment protocols, or mutate authoritative scientific evidence.

For public deployment, run the BioNuclei backend behind HTTPS and apply authentication, upload limits, CORS restrictions and resource controls appropriate to the environment.

## Versioning

The BioMCP product version is independent of the BioNuclei scientific package version. Release metadata must record both versions plus the exact backend commit/checkpoint identity used by the server.

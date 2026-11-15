# BioMCP Deployment

BioMCP has two supported execution modes.

## Local agent mode

Install the optional MCP dependency and run the server over stdio:

```bash
python -m pip install -e '.[mcp]'
bionuclei-mcp
```

The MCP SDK handles protocol framing; scientific computation remains inside the BioNuclei package.

## Hosted MCP mode

Streamable HTTP binds to loopback by default. This is suitable for a local agent or a
trusted process on the same machine:

```bash
python -m pip install -e '.[mcp]'
BIOMCP_MCP_HOST=127.0.0.1 \
BIOMCP_MCP_PORT=8001 \
BIOMCP_STREAMABLE_HTTP_PATH=/mcp \
bionuclei-mcp-http
```

A non-loopback bind is refused unless a strong bearer token is configured. Generate
a fresh secret and keep it out of source control, command history, and logs:

```bash
export BIOMCP_MCP_BEARER_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
BIOMCP_MCP_HOST=0.0.0.0 \
BIOMCP_MCP_PORT=8001 \
BIOMCP_STREAMABLE_HTTP_PATH=/mcp \
bionuclei-mcp-http
```

Remote clients must send `Authorization: Bearer <token>` on every HTTP request.
The server rejects missing, duplicate, or invalid Authorization headers with HTTP 401.
The token must contain at least 32 ASCII characters and no whitespace.

For internet-facing deployments, terminate TLS at a trusted reverse proxy and forward the
Authorization header. Do not expose the raw HTTP port over an untrusted network.

**Trust boundary:** MCP tool arguments currently contain paths on the server host, not
uploaded client files. An authenticated caller can therefore access files available to
the server process through the registered path-based tools. Only share the bearer token
with trusted clients; do not expose this server as a public multi-tenant service. Use
separate isolated workers and per-user authorization before serving mutually untrusted
users.

The current MCP Python SDK documents Streamable HTTP as the deployment transport; SSE
is retained only for legacy clients. The repository therefore does not build new
deployment paths on SSE.

## Browser website

The GitHub Pages console is [`docs/use.html`](use.html). It talks to the separate web adapter in `webapp/app.py` through HTTPS. Configure the console with the deployed API base URL.

The web adapter exposes the same six implemented operations:

- inspect image;
- predict image;
- evaluate image;
- compute instance metrics;
- read provenance;
- read structured result summaries.

A server must set `BIONUCLEI_CHECKPOINT` to a validated checkpoint before prediction/evaluation endpoints are enabled. The API does not accept arbitrary checkpoint uploads or arbitrary shell commands.

## Deployment recipe

A Docker image is provided at `webapp/Dockerfile`, with a Render service template at `webapp/render.yaml`. These files are deployment recipes, not evidence that a hosted endpoint is already live.

## Research boundary

Registered E6/E7 benchmark workflows remain controlled scientific experiments. They are not exposed as unrestricted public web actions. This keeps the public interface useful while preserving the experiment and provenance boundaries of the research release.

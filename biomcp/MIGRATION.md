# BioMCP consolidation

## Source repository check

The requested source repository is `BurhanAbdullah/Bio-MCP-`.

At the time of consolidation it is public but empty: GitHub reports no files, no commits and no branches. There was therefore no source implementation to copy from that repository.

## Canonical BioMCP implementation in this repository

BioMCP is maintained here as an independent interoperability product. The canonical implementation is split by responsibility:

- `src/biomcp/` — registry, installer and client-facing orchestration.
- `src/bionuclei/mcp_server.py` — first scientific MCP server exposed by BioMCP.
- `biomcp/registry.json` — machine-readable server-pack registry.
- `biomcp/config.json` — example MCP client configuration.
- `biomcp/README.md` — user/developer entry point.
- `docs/BIOMCP_MANIFESTO.md` — research scope and principles.
- `docs/ARCHITECTURE.md` — architecture and tool-contract model.
- `docs/ROADMAP.md` — staged implementation roadmap.
- `.github/workflows/biomcp-ci.yml` — automated BioMCP validation.
- `.github/workflows/biomcp_web_validation.yml` — web/registry validation.
- `tests/test_biomcp_cli.py` — CLI regression tests.
- `tests/test_biomcp_registry.py` — registry integrity tests.

## Product boundary

BioMCP is the interoperability layer. It does not replace the underlying scientific software and must not invent scientific measurements or benchmark claims.

The first installable server pack is `bionuclei`. Planned integrations such as ImageJ/Fiji and CellProfiler are represented in the registry as non-installable until concrete adapters and validation suites exist.

## Intended A-to-Z flow

```text
research question
      -> agent / LLM
      -> BioMCP registry
      -> validated server pack
      -> typed scientific tool
      -> structured artifact
      -> provenance
      -> human review
```

A server is eligible for the installable registry only when its runtime command, tool contract, scientific boundary and validation status are explicitly represented in machine-readable metadata.

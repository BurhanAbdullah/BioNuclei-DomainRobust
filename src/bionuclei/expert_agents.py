"""Evidence constrained specialist agents for BioNuclei reporting.

These agents are deterministic scientific reviewers over measured outputs. They
must not be described as trained on a dataset unless a verified training
manifest is supplied. This prevents unsupported training claims in reports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentFinding:
    agent: str
    observations: tuple[str, ...]
    limitations: tuple[str, ...]


SPECIALIST_AGENTS = (
    "image_quality_agent",
    "segmentation_quality_agent",
    "morphology_agent",
    "intensity_agent",
    "population_agent",
    "biological_interpretation_agent",
    "scientific_review_agent",
    "report_agent",
)


def training_manifest_status(manifest: dict[str, Any] | None) -> dict[str, Any]:
    """Return auditable training status without inventing dataset counts."""
    manifest = manifest or {}
    count = int(manifest.get("validated_images", 0) or 0)
    return {
        "verified": bool(manifest.get("verified", False) and count >= 1000),
        "validated_images": count,
        "training_reference": manifest.get("training_reference", "Not established"),
        "claim_allowed": bool(manifest.get("verified", False) and count >= 1000),
    }


def run_expert_agents(results: dict[str, Any]) -> dict[str, Any]:
    """Generate evidence constrained findings from existing quantitative results."""
    reports = results.get("reports", {})
    plan = results.get("adaptive_plan", {})
    morphology = reports.get("morphology", {})
    intensity = reports.get("intensity", {})
    findings: list[AgentFinding] = []

    findings.append(AgentFinding(
        "image_quality_agent",
        (f"Analysis status: {plan.get('status', 'UNKNOWN')}.",),
        tuple(plan.get("warnings", [])),
    ))
    findings.append(AgentFinding(
        "segmentation_quality_agent",
        (f"Detected nuclei: {reports.get('nuclei_count', 'Not available')}.",),
        ("Segmentation quality should be interpreted together with the CNN diagnostics and visual overlay.",),
    ))
    findings.append(AgentFinding(
        "morphology_agent",
        tuple(f"{k}: {v}" for k, v in morphology.items()),
        ("Morphology alone does not establish a biological mechanism or phenotype.",),
    ))
    findings.append(AgentFinding(
        "intensity_agent",
        tuple(f"{k}: {v}" for k, v in intensity.items()),
        ("Fluorescence intensity depends on acquisition, staining, exposure, background, and normalization.",),
    ))
    findings.append(AgentFinding(
        "population_agent",
        (f"Population size available for analysis: {reports.get('nuclei_count', 'Not available')} nuclei.",),
        ("Population comparisons require appropriate experimental controls and biological replicates.",),
    ))
    findings.append(AgentFinding(
        "biological_interpretation_agent",
        ("Interpretation is restricted to patterns supported by the measured image features.",),
        ("No disease, diagnostic, mechanistic, or causal conclusion is generated from morphology or intensity measurements alone.",),
    ))
    findings.append(AgentFinding(
        "scientific_review_agent",
        ("All report conclusions must remain traceable to recorded measurements and quality checks.",),
        ("Unsupported confidence, invented training provenance, and unmeasured biological claims are prohibited.",),
    ))
    findings.append(AgentFinding(
        "report_agent",
        ("The report should preserve the analysis provenance and specialist findings.",),
        (),
    ))

    return {
        "agent_version": "1.0",
        "agents": [
            {"agent": f.agent, "observations": list(f.observations), "limitations": list(f.limitations)}
            for f in findings
        ],
        "training_status": training_manifest_status(results.get("agent_training_manifest")),
        "evidence_policy": "Agents interpret measured evidence; they do not invent measurements or training provenance.",
    }

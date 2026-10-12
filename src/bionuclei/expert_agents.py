"""Evidence constrained specialist agents for BioNuclei reporting.

These agents are deterministic scientific reviewers over measured outputs. They
must not be described as trained on a dataset unless a verified training
manifest is supplied. This prevents unsupported training claims in reports.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentFinding:
    agent: str
    observations: tuple[str, ...]
    limitations: tuple[str, ...]
    evidence_references: tuple[str, ...] = ()


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
    raw_count = manifest.get("validated_images")
    try:
        count = int(raw_count) if raw_count is not None and str(raw_count).strip() else None
    except (TypeError, ValueError):
        count = None
    verified = bool(manifest.get("verified", False) and count is not None and count >= 1000)
    return {
        "verified": verified,
        "validated_images": count,
        "training_reference": manifest.get("training_reference", "Not established"),
        "claim_allowed": verified,
    }


def _evidence_for(results: dict[str, Any], references: tuple[str, ...]) -> tuple[list[str], str | None]:
    """Hash only evidence fields that actually exist in the deterministic result."""
    evidence: dict[str, Any] = {}
    for reference in references:
        value: Any = results
        found = True
        for key in reference.split("."):
            if not isinstance(value, dict) or key not in value:
                found = False
                break
            value = value[key]
        if found:
            evidence[reference] = value
    if not evidence:
        return [], None
    payload = json.dumps(
        evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")
    return list(evidence), hashlib.sha256(payload).hexdigest()


def run_expert_agents(results: dict[str, Any]) -> dict[str, Any]:
    """Generate evidence constrained findings from existing quantitative results."""
    reports = results.get("reports", {})
    plan = results.get("adaptive_plan", {})
    morphology = reports.get("morphology", {})
    intensity = reports.get("intensity", {})
    profile = plan.get("profile", {})
    profile_keys = (
        "shape", "dtype", "min", "p01", "median", "p995", "max", "mean", "std",
        "saturation_fraction", "zero_fraction", "finite",
    )
    profile_observations = tuple(
        f"Raw image {key}: {profile[key]}"
        for key in profile_keys
        if isinstance(profile, dict) and key in profile
    )
    findings: list[AgentFinding] = []

    findings.append(AgentFinding(
        "image_quality_agent",
        (f"Analysis status: {plan.get('status', 'UNKNOWN')}.",),
        tuple(plan.get("warnings", [])),
        ("adaptive_plan.status", "adaptive_plan.warnings", "adaptive_plan.profile"),
    ))
    findings.append(AgentFinding(
        "segmentation_quality_agent",
        (f"Detected nuclei: {reports.get('nuclei_count', 'Not available')}.",),
        ("Segmentation quality should be interpreted together with the CNN diagnostics and visual overlay.",),
        ("reports.nuclei_count", "adaptive_plan.cnn_pattern_check"),
    ))
    findings.append(AgentFinding(
        "morphology_agent",
        tuple(f"{k}: {v}" for k, v in morphology.items()),
        ("Morphology alone does not establish a biological mechanism or phenotype.",),
        ("reports.morphology",),
    ))
    findings.append(AgentFinding(
        "intensity_agent",
        tuple([*(f"{k}: {v}" for k, v in intensity.items()), *profile_observations]),
        ("Fluorescence intensity depends on acquisition, staining, exposure, background, and normalization.",),
        ("reports.intensity", "adaptive_plan.profile"),
    ))
    findings.append(AgentFinding(
        "population_agent",
        (f"Population size available for analysis: {reports.get('nuclei_count', 'Not available')} nuclei.",),
        ("Population comparisons require appropriate experimental controls and biological replicates.",),
        ("reports.nuclei_count",),
    ))
    findings.append(AgentFinding(
        "biological_interpretation_agent",
        ("Interpretation is restricted to patterns supported by the measured image features.",),
        ("No disease, diagnostic, mechanistic, or causal conclusion is generated from morphology or intensity measurements alone.",),
        ("reports.nuclei_count", "reports.morphology", "reports.intensity"),
    ))
    findings.append(AgentFinding(
        "scientific_review_agent",
        ("All report conclusions must remain traceable to recorded measurements and quality checks.",),
        ("Unsupported confidence, invented training provenance, and unmeasured biological claims are prohibited.",),
        ("input_sha256", "adaptive_plan", "reports"),
    ))
    findings.append(AgentFinding(
        "report_agent",
        ("The report should preserve the analysis provenance and specialist findings.",),
        (),
        ("input_sha256", "analysis_modules", "reports"),
    ))

    return {
        "agent_version": "1.0",
        "agents": [
            {
                "agent": f.agent,
                "observations": list(f.observations),
                "limitations": list(f.limitations),
                "evidence_references": (evidence := _evidence_for(results, f.evidence_references))[0],
                "evidence_sha256": evidence[1],
            }
            for f in findings
        ],
        "training_status": training_manifest_status(results.get("agent_training_manifest")),
        "evidence_policy": "Agents interpret measured evidence; they do not invent measurements or training provenance.",
    }

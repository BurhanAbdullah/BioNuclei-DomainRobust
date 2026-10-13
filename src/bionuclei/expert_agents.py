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

    agent_outputs: list[dict[str, Any]] = []
    for finding in findings:
        evidence_references, evidence_sha256 = _evidence_for(results, finding.evidence_references)
        missing_references = [
            reference for reference in finding.evidence_references
            if reference not in evidence_references
        ]
        # Do not label a reviewer complete when any declared evidence is absent.
        status = "completed" if evidence_references and not missing_references else "incomplete"
        agent_outputs.append({
            "agent": finding.agent,
            "status": status,
            "observations": list(finding.observations),
            "limitations": list(finding.limitations),
            "evidence_references": evidence_references,
            "missing_evidence_references": missing_references,
            "evidence_sha256": evidence_sha256,
        })

    input_sha256 = results.get("input_sha256")
    input_hash_valid = (
        isinstance(input_sha256, str)
        and len(input_sha256) == 64
        and all(character in "0123456789abcdefABCDEF" for character in input_sha256)
    )
    completed_count = sum(agent["status"] == "completed" for agent in agent_outputs)
    execution_payload = {
        "agent_version": "1.1",
        "input_sha256": input_sha256 if input_hash_valid else None,
        "agents": [
            {
                "agent": agent["agent"],
                "status": agent["status"],
                "evidence_references": agent["evidence_references"],
                "evidence_sha256": agent["evidence_sha256"],
                "missing_evidence_references": agent["missing_evidence_references"],
            }
            for agent in agent_outputs
        ],
    }
    execution_sha256 = hashlib.sha256(
        json.dumps(
            execution_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
    all_complete = input_hash_valid and completed_count == len(agent_outputs)

    return {
        "agent_version": "1.1",
        "execution": {
            "status": "completed" if all_complete else "incomplete",
            "input_sha256": input_sha256 if input_hash_valid else None,
            "agent_count": len(agent_outputs),
            "completed_agent_count": completed_count,
            "incomplete_agents": [
                agent["agent"] for agent in agent_outputs if agent["status"] != "completed"
            ],
            "execution_sha256": execution_sha256,
        },
        "agents": agent_outputs,
        "training_status": training_manifest_status(results.get("agent_training_manifest")),
        "evidence_policy": (
            "Deterministic reviewers interpret measured evidence; they do not invent "
            "measurements or training provenance. A reviewer is incomplete when any "
            "declared evidence reference is missing or the input hash is invalid."
        ),
    }

"""Evidence constrained specialist agents for BioNuclei reporting.

These agents are deterministic scientific reviewers over measured outputs. They
must not be described as trained on a dataset unless a verified training
manifest is supplied. This prevents unsupported training claims in reports.
"""
from __future__ import annotations

import hashlib
import json
import math
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


def _resolve_reference(results: dict[str, Any], reference: str) -> tuple[bool, Any]:
    value: Any = results
    for key in reference.split("."):
        if not isinstance(value, dict) or key not in value:
            return False, None
        value = value[key]
    return True, value


def _evidence_for(
    results: dict[str, Any], references: tuple[str, ...]
) -> tuple[list[str], str | None, str | None]:
    """Return exact evidence bytes so browser verification never reserializes floats."""
    evidence: dict[str, Any] = {}
    for reference in references:
        found, value = _resolve_reference(results, reference)
        if found:
            evidence[reference] = value
    if not evidence:
        return [], None, None
    payload = json.dumps(
        evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    payload_bytes = payload.encode("utf-8")
    return list(evidence), hashlib.sha256(payload_bytes).hexdigest(), payload


def _numeric_claims(
    results: dict[str, Any], references: tuple[str, ...]
) -> list[dict[str, Any]]:
    """Expose numeric evidence as typed claims tied to exact result paths."""
    claims: dict[str, dict[str, Any]] = {}

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key in sorted(value):
                visit(value[key], f"{path}.{key}")
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return
        if isinstance(value, float) and not math.isfinite(value):
            return
        field = path.rsplit(".", 1)[-1]
        if field == "shape":
            return
        if field in {"nuclei_count", "instance_count"}:
            unit = "nuclei"
        elif field.endswith("_px") or "distance_px" in field or "perimeter" in field:
            unit = "pixels"
        elif "area" in field:
            unit = "pixels^2"
        elif field.endswith("_fraction"):
            unit = "fraction"
        elif "adaptive_plan.profile." in path and field in {"min", "p01", "median", "p995", "max", "mean", "std"}:
            unit = "raw_intensity_units"
        elif "intensity" in field:
            unit = "raw_intensity_units"
        else:
            unit = "unitless"
        claims[path] = {"reference": path, "value": value, "unit": unit}

    for reference in references:
        found, value = _resolve_reference(results, reference)
        if found:
            visit(value, reference)
    return [claims[path] for path in sorted(claims)]


def run_expert_agents(results: dict[str, Any]) -> dict[str, Any]:
    """Generate evidence constrained findings from existing quantitative results."""
    reports = results.get("reports", {})
    plan = results.get("adaptive_plan", {})
    morphology = reports.get("morphology", {})
    intensity = reports.get("intensity", {})
    spatial = reports.get("spatial", {})
    profile = plan.get("profile", {})
    profile_keys = (
        "shape", "dtype", "min", "p01", "median", "p995", "max", "mean", "std",
        "saturation_fraction", "zero_fraction", "finite",
    )
    profile_observations = tuple(
        [f"Raw image dtype: {profile['dtype']}"]
        if isinstance(profile, dict) and isinstance(profile.get("dtype"), str)
        else []
    ) + (
        ("Raw-image intensity statistics are provided as structured quantitative claims.",)
        if isinstance(profile, dict) and any(key in profile for key in profile_keys if key not in {"shape", "dtype", "finite"})
        else ()
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
        ("The detected instance count is provided as a structured quantitative claim.",),
        ("Segmentation quality should be interpreted together with the CNN diagnostics and visual overlay.",),
        ("reports.nuclei_count", "adaptive_plan.cnn_pattern_check"),
    ))
    findings.append(AgentFinding(
        "morphology_agent",
        ("Morphology summaries are provided as structured quantitative claims.",),
        ("Morphology alone does not establish a biological mechanism or phenotype.",),
        ("reports.morphology",),
    ))
    findings.append(AgentFinding(
        "intensity_agent",
        tuple([*profile_observations, "Nuclear intensity summaries are provided as structured quantitative claims."]),
        ("Fluorescence intensity depends on acquisition, staining, exposure, background, and normalization.",),
        ("reports.intensity", "adaptive_plan.profile"),
    ))
    spatial_observations: list[str] = []
    if isinstance(spatial, dict):
        if spatial.get("mean_nearest_neighbor_distance_px") is None:
            spatial_observations.append("Nearest-neighbour distance summary is unavailable for fewer than two measured instances or missing centroids.")
        else:
            spatial_observations.append("Nearest-neighbour distance summaries are provided as structured quantitative claims.")
    findings.append(AgentFinding(
        "population_agent",
        ("Population size is provided as a structured quantitative claim.", *spatial_observations),
        ("Population comparisons require appropriate experimental controls and biological replicates.",),
        ("reports.nuclei_count", "reports.spatial.instance_count", "reports.spatial.mean_nearest_neighbor_distance_px"),
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
        ("input_sha256", "adaptive_plan", "reports", "reports.spatial"),
    ))
    findings.append(AgentFinding(
        "report_agent",
        ("The report should preserve the analysis provenance and specialist findings.",),
        (),
        ("input_sha256", "analysis_modules", "reports", "reports.spatial"),
    ))

    agent_outputs: list[dict[str, Any]] = []
    for finding in findings:
        evidence_references, evidence_sha256, evidence_payload = _evidence_for(results, finding.evidence_references)
        quantitative_claims = _numeric_claims(results, finding.evidence_references)
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
            "evidence_payload": evidence_payload,
            "quantitative_claims": quantitative_claims,
        })

    input_sha256 = results.get("input_sha256")
    input_hash_valid = (
        isinstance(input_sha256, str)
        and len(input_sha256) == 64
        and all(character in "0123456789abcdefABCDEF" for character in input_sha256)
    )
    completed_count = sum(agent["status"] == "completed" for agent in agent_outputs)
    job_id = results.get("job_id")
    job_id_valid = isinstance(job_id, str) and bool(job_id.strip())
    training_status = training_manifest_status(results.get("agent_training_manifest"))
    execution_payload = {
        "agent_version": "1.1",
        "job_id": job_id if job_id_valid else None,
        "job_id_valid": job_id_valid,
        "input_sha256": input_sha256 if input_hash_valid else None,
        "input_hash_valid": input_hash_valid,
        "agents": [
            {
                "agent": agent["agent"],
                "status": agent["status"],
                "observations": agent["observations"],
                "limitations": agent["limitations"],
                "evidence_references": agent["evidence_references"],
                "evidence_sha256": agent["evidence_sha256"],
                "evidence_payload": agent["evidence_payload"],
                "quantitative_claims": agent["quantitative_claims"],
                "missing_evidence_references": agent["missing_evidence_references"],
            }
            for agent in agent_outputs
        ],
        "training_status": training_status,
    }
    execution_payload_json = json.dumps(
        execution_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    execution_sha256 = hashlib.sha256(execution_payload_json.encode("utf-8")).hexdigest()
    all_complete = input_hash_valid and job_id_valid and completed_count == len(agent_outputs)
    incomplete_reasons = []
    if not job_id_valid:
        incomplete_reasons.append("missing_or_invalid_job_id")
    if not input_hash_valid:
        incomplete_reasons.append("missing_or_invalid_input_sha256")
    if completed_count != len(agent_outputs):
        incomplete_reasons.append("one_or_more_reviewers_missing_declared_evidence")

    return {
        "agent_version": "1.1",
        "execution": {
            "status": "completed" if all_complete else "incomplete",
            "job_id": job_id if job_id_valid else None,
            "job_id_valid": job_id_valid,
            "input_sha256": input_sha256 if input_hash_valid else None,
            "input_hash_valid": input_hash_valid,
            "incomplete_reasons": incomplete_reasons,
            "agent_count": len(agent_outputs),
            "completed_agent_count": completed_count,
            "incomplete_agents": [
                agent["agent"] for agent in agent_outputs if agent["status"] != "completed"
            ],
            "execution_sha256": execution_sha256,
            "execution_payload_json": execution_payload_json,
        },
        "agents": agent_outputs,
        "training_status": training_status,
        "evidence_policy": (
            "Deterministic reviewers interpret measured evidence; they do not invent "
            "measurements or training provenance. A reviewer is incomplete when any "
            "declared evidence reference is missing or the input hash is invalid."
        ),
    }

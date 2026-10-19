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
    """Execute deterministic specialist reviewers over this job's computed evidence.

    Each reviewer derives observations from measured result/QC fields and records
    exact evidence references. These are rule-based reviewers, not generative
    biological interpretation and not a claim of model training.
    """
    def is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))

    def display_number(value: Any) -> str:
        if is_number(value) and float(value).is_integer():
            return str(int(value))
        return str(value)

    reports = results.get("reports")
    reports = reports if isinstance(reports, dict) else {}
    plan = results.get("adaptive_plan")
    plan = plan if isinstance(plan, dict) else {}
    morphology = reports.get("morphology")
    morphology = morphology if isinstance(morphology, dict) else {}
    intensity = reports.get("intensity")
    intensity = intensity if isinstance(intensity, dict) else {}
    spatial = reports.get("spatial")
    spatial = spatial if isinstance(spatial, dict) else {}
    profile = plan.get("profile")
    profile = profile if isinstance(profile, dict) else {}
    cnn = plan.get("cnn_pattern_check")
    cnn = cnn if isinstance(cnn, dict) else {}
    raw_warnings = plan.get("warnings", [])
    warnings = [str(item) for item in raw_warnings] if isinstance(raw_warnings, (list, tuple)) else []
    raw_modules = results.get("analysis_modules", [])
    modules = sorted({item for item in raw_modules if isinstance(item, str)}) if isinstance(raw_modules, (list, tuple)) else []
    module_set = set(modules)

    profile_observations: list[str] = []
    if isinstance(profile.get("dtype"), str):
        profile_observations.append(f"Raw image dtype: {profile['dtype']}")
    shape = profile.get("shape")
    if isinstance(shape, (list, tuple)) and all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in shape):
        profile_observations.append("Raw image shape: " + "x".join(str(value) for value in shape))
    for key in ("min", "p01", "median", "p995", "max", "mean", "std", "saturation_fraction", "zero_fraction"):
        value = profile.get(key)
        if is_number(value):
            profile_observations.append(f"Raw image {key}: {display_number(value)}")
    if is_number(profile.get("min")) and is_number(profile.get("max")):
        profile_observations.append(f"Raw image dynamic range: {display_number(profile['max'] - profile['min'])} raw intensity units.")
    if profile.get("dtype") == "uint16" and is_number(profile.get("max")) and profile["max"] > 255:
        profile_observations.append(f"Raw uint16 intensities exceed the 8-bit range; maximum recorded value: {display_number(profile['max'])}.")

    nuclei_count = reports.get("nuclei_count", results.get("n_instances"))
    count_valid = isinstance(nuclei_count, int) and not isinstance(nuclei_count, bool) and nuclei_count >= 0
    cnn_observations: list[str] = []
    if cnn:
        if isinstance(cnn.get("status"), str):
            cnn_observations.append(f"CNN pattern-gate status: {cnn['status']}.")
        for key, label in (("foreground_fraction", "CNN foreground fraction"), ("mean_class_confidence", "CNN mean class confidence"), ("mean_entropy", "CNN mean entropy")):
            value = cnn.get(key)
            if is_number(value):
                cnn_observations.append(f"{label}: {display_number(value)}.")
        if isinstance(cnn.get("connected_components"), int) and not isinstance(cnn.get("connected_components"), bool):
            cnn_observations.append(f"CNN foreground connected components: {cnn['connected_components']}.")

    image_observations = [f"Analysis status: {plan.get('status', 'UNKNOWN')}."]
    image_observations.extend(profile_observations)
    if profile.get("finite") is False:
        image_observations.append("The raw image profile marks the input as containing non-finite values.")
    if not profile_observations:
        image_observations.append("No structured raw-image profile was available for this job.")
    findings: list[AgentFinding] = [
        AgentFinding(
            "image_quality_agent",
            tuple(image_observations),
            tuple(warnings) or ("No QC warnings were emitted; visual inspection is still recommended.",),
            ("adaptive_plan.status", "adaptive_plan.warnings", "adaptive_plan.profile", "adaptive_plan.cnn_pattern_check"),
        ),
    ]

    segmentation_observations: list[str] = []
    segmentation_observations.append(f"Measured nuclear instance count: {nuclei_count}." if count_valid else "A valid measured nuclear instance count is unavailable.")
    segmentation_observations.extend(cnn_observations)
    if count_valid and nuclei_count == 0:
        segmentation_observations.append("No nuclear instances were detected; object-level summaries may be unavailable.")
    reported_instances = results.get("n_instances")
    if count_valid and isinstance(reported_instances, int) and not isinstance(reported_instances, bool):
        if reported_instances != nuclei_count:
            segmentation_observations.append(f"Instance-count consistency warning: inference reported {reported_instances}, measurements reported {nuclei_count}.")
        else:
            segmentation_observations.append("Inference and measurement instance counts agree.")
    findings.append(AgentFinding(
        "segmentation_quality_agent",
        tuple(segmentation_observations),
        ("The foreground count is not an accuracy metric; no per-upload ground-truth comparison was performed.",
         "Review the returned mask and overlay before interpreting the detected instances."),
        ("reports.nuclei_count", "adaptive_plan.cnn_pattern_check", "reports.spatial.instance_count"),
    ))

    morphology_observations: list[str] = []
    for key, label, unit in (
        ("mean_area", "Measured mean area", "pixels^2"),
        ("median_area", "Measured median area", "pixels^2"),
        ("mean_perimeter", "Measured mean perimeter", "pixels"),
        ("mean_eccentricity", "Measured mean eccentricity", "unitless"),
        ("mean_solidity", "Measured mean solidity", "unitless"),
        ("mean_circularity", "Measured mean circularity", "unitless"),
    ):
        value = morphology.get(key)
        if is_number(value):
            morphology_observations.append(f"{label}: {display_number(value)} {unit}.")
    if not morphology_observations:
        morphology_observations.append("No finite morphology summary was produced for this run.")
    findings.append(AgentFinding(
        "morphology_agent",
        tuple(morphology_observations),
        ("Morphology describes measured geometry only; it does not establish a biological mechanism or phenotype.",),
        ("reports.morphology", "reports.nuclei_count"),
    ))

    intensity_observations = list(profile_observations)
    intensity_value_count = 0
    for key, label in (
        ("mean_nuclear_intensity", "Measured mean nuclear intensity"),
        ("median_nuclear_intensity", "Measured median nuclear intensity"),
        ("mean_max_intensity", "Mean per-instance maximum intensity"),
        ("max_nuclear_intensity", "Maximum per-instance nuclear intensity"),
    ):
        value = intensity.get(key)
        if is_number(value):
            intensity_observations.append(f"{label}: {display_number(value)} raw intensity units.")
            intensity_value_count += 1
    if intensity_value_count == 0:
        intensity_observations.append("No finite per-nucleus intensity summary was produced; confirm that instances were detected and the intensity module ran.")
    findings.append(AgentFinding(
        "intensity_agent",
        tuple(intensity_observations),
        ("Fluorescence intensity depends on acquisition, staining, exposure, background, detector response, and segmentation boundaries.",),
        ("reports.intensity", "adaptive_plan.profile"),
    ))

    population_observations: list[str] = []
    population_observations.append(f"Measured population size: {nuclei_count} detected nuclei." if count_valid else "Measured population size is unavailable.")
    distance_fields = (
        ("mean_nearest_neighbor_distance_px", "Mean nearest-neighbour distance"),
        ("median_nearest_neighbor_distance_px", "Median nearest-neighbour distance"),
        ("min_nearest_neighbor_distance_px", "Minimum nearest-neighbour distance"),
        ("max_nearest_neighbor_distance_px", "Maximum nearest-neighbour distance"),
    )
    for key, label in distance_fields:
        value = spatial.get(key)
        if is_number(value):
            population_observations.append(f"{label}: {display_number(value)} pixels.")
    if not any(is_number(spatial.get(key)) for key, _ in distance_fields):
        population_observations.append("Nearest-neighbour distances are unavailable for this measured population or lack valid centroids.")
    findings.append(AgentFinding(
        "population_agent",
        tuple(population_observations),
        ("Population comparisons require appropriate experimental controls and biological replicates.",),
        ("reports.nuclei_count", "reports.spatial.instance_count", "reports.spatial.mean_nearest_neighbor_distance_px"),
    ))

    biological_observations: list[str] = []
    if count_valid:
        biological_observations.append(f"The computational pipeline detected {nuclei_count} nuclear instances in this field.")
    measured_sections = []
    if any(is_number(value) for value in morphology.values()):
        measured_sections.append("morphology")
    if any(is_number(value) for value in intensity.values()):
        measured_sections.append("intensity")
    if measured_sections:
        biological_observations.append("Finite quantitative summaries are available for: " + ", ".join(measured_sections) + ".")
    else:
        biological_observations.append("No finite morphology or intensity summary is available for biological interpretation.")
    biological_observations.append("These measurements do not identify cell type or establish disease, mechanism, treatment response, or causality.")
    findings.append(AgentFinding(
        "biological_interpretation_agent",
        tuple(biological_observations),
        ("Biological interpretation requires validated context, controls, replicates, and domain-specific evidence.",),
        ("reports.nuclei_count", "reports.morphology", "reports.intensity"),
    ))

    input_sha256 = results.get("input_sha256")
    input_hash_valid = isinstance(input_sha256, str) and len(input_sha256) == 64 and all(character in "0123456789abcdefABCDEF" for character in input_sha256)
    job_id = results.get("job_id")
    job_id_valid = isinstance(job_id, str) and bool(job_id.strip())
    model = results.get("model")
    model = model if isinstance(model, dict) else {}
    weights_frozen = model.get("weights_updated_during_analysis") is False
    training_status = training_manifest_status(results.get("agent_training_manifest"))
    review_observations = [
        "Input SHA-256 binding: " + ("valid." if input_hash_valid else "missing or malformed."),
        "Job identifier binding: " + ("valid." if job_id_valid else "missing or malformed."),
        "Model weights updated during analysis: " + ("no." if weights_frozen else "not verified."),
        "Training provenance status: " + ("verified." if training_status["verified"] else "Not established."),
    ]
    findings.append(AgentFinding(
        "scientific_review_agent",
        tuple(review_observations),
        ("Unsupported confidence, invented training provenance, and unmeasured biological claims are prohibited.",),
        ("input_sha256", "adaptive_plan", "reports", "reports.spatial", "model"),
    ))

    available_sections = [name for name in ("morphology", "intensity", "spatial") if isinstance(reports.get(name), dict)]
    report_observations = [
        f"Report input is bound to job {job_id}." if job_id_valid else "Report input has no valid job identifier.",
        f"Configured analysis modules: {', '.join(modules) if modules else 'not recorded'}.",
        "Computed report sections available: " + (", ".join(available_sections) if available_sections else "none recorded") + ".",
    ]
    if count_valid:
        report_observations.append(f"The report input contains a measured count of {nuclei_count} detected nuclei.")
    findings.append(AgentFinding(
        "report_agent",
        tuple(report_observations),
        ("The report summarizes computed evidence; it does not create new measurements or validate model accuracy.",),
        ("input_sha256", "analysis_modules", "reports", "reports.spatial", "model"),
    ))

    module_requirements = {
        "morphology_agent": {"morphology"},
        "intensity_agent": {"intensity"},
        "biological_interpretation_agent": {"morphology", "intensity"},
    }
    not_applicable_limitation = (
        "This reviewer did not execute because its required modules were not selected; "
        "no findings or quantitative claims are asserted."
    )
    agent_outputs: list[dict[str, Any]] = []
    for finding in findings:
        unselected = sorted(module_requirements.get(finding.agent, set()) - module_set)
        if unselected:
            evidence_payload = "{}"
            agent_outputs.append({
                "agent": finding.agent,
                "status": "not_applicable",
                "observations": ["Not applicable: required analysis module(s) not selected: " + ", ".join(unselected) + "."],
                "limitations": [not_applicable_limitation],
                "evidence_references": [],
                "missing_evidence_references": [],
                "evidence_sha256": hashlib.sha256(evidence_payload.encode("utf-8")).hexdigest(),
                "evidence_payload": evidence_payload,
                "quantitative_claims": [],
            })
            continue
        evidence_references, evidence_sha256, evidence_payload = _evidence_for(results, finding.evidence_references)
        quantitative_claims = _numeric_claims(results, finding.evidence_references)
        missing_references = [reference for reference in finding.evidence_references if reference not in evidence_references]
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

    completed_count = sum(agent["status"] == "completed" for agent in agent_outputs)
    not_applicable_count = sum(agent["status"] == "not_applicable" for agent in agent_outputs)
    resolved_count = completed_count + not_applicable_count
    incomplete_agents = [agent["agent"] for agent in agent_outputs if agent["status"] not in {"completed", "not_applicable"}]
    execution_payload = {
        "agent_version": "1.2",
        "analysis_modules": modules,
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
    execution_payload_json = json.dumps(execution_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    execution_sha256 = hashlib.sha256(execution_payload_json.encode("utf-8")).hexdigest()
    all_complete = input_hash_valid and job_id_valid and resolved_count == len(agent_outputs)
    incomplete_reasons = []
    if not job_id_valid:
        incomplete_reasons.append("missing_or_invalid_job_id")
    if not input_hash_valid:
        incomplete_reasons.append("missing_or_invalid_input_sha256")
    if incomplete_agents:
        incomplete_reasons.append("one_or_more_reviewers_missing_declared_evidence")

    return {
        "agent_version": "1.2",
        "execution": {
            "status": "completed" if all_complete else "incomplete",
            "analysis_modules": modules,
            "job_id": job_id if job_id_valid else None,
            "job_id_valid": job_id_valid,
            "input_sha256": input_sha256 if input_hash_valid else None,
            "input_hash_valid": input_hash_valid,
            "incomplete_reasons": incomplete_reasons,
            "agent_count": len(agent_outputs),
            "completed_agent_count": completed_count,
            "not_applicable_agent_count": not_applicable_count,
            "resolved_agent_count": resolved_count,
            "incomplete_agents": incomplete_agents,
            "execution_sha256": execution_sha256,
            "execution_payload_json": execution_payload_json,
        },
        "agents": agent_outputs,
        "training_status": training_status,
        "evidence_policy": (
            "Deterministic specialist reviewers derive observations from computed QC, segmentation, morphology, "
            "intensity, and spatial measurements. They do not invent measurements, training provenance, or biological "
            "conclusions. A reviewer is incomplete when any declared evidence reference is missing or the input "
            "hash/job binding is invalid."
        ),
    }

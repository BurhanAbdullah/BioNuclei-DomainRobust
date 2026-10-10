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
    """Report only training provenance supported by an explicitly verified manifest."""
    if not isinstance(manifest, dict) or not manifest:
        return {
            "status": "unknown",
            "verified": False,
            "validated_images": None,
            "training_reference": None,
            "claim_allowed": False,
        }

    raw_count = manifest.get("validated_images")
    count_valid = type(raw_count) is int and raw_count >= 0
    manifest_verified = manifest.get("verified") is True and count_valid
    raw_reference = manifest.get("training_reference")
    reference = raw_reference.strip() if isinstance(raw_reference, str) else ""
    reference = reference or None
    if not manifest_verified:
        reference = None

    return {
        "status": "verified" if manifest_verified else "unverified",
        "verified": manifest_verified,
        "validated_images": raw_count if manifest_verified else None,
        "training_reference": reference,
        "claim_allowed": bool(
            manifest_verified and raw_count >= 1000 and reference is not None
        ),
    }


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _path_value(payload: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = payload
    for component in path.split("."):
        if not isinstance(current, dict) or component not in current:
            return False, None
        current = current[component]
    return True, current


_EVIDENCE_PATHS: dict[str, tuple[str, ...]] = {
    "image_quality_agent": (
        "adaptive_plan.status",
        "adaptive_plan.warnings",
        "adaptive_plan.profile",
    ),
    "segmentation_quality_agent": (
        "reports.nuclei_count",
        "n_instances",
        "adaptive_plan.cnn_pattern_check",
    ),
    "morphology_agent": ("reports.morphology",),
    "intensity_agent": ("reports.intensity", "adaptive_plan.profile"),
    "population_agent": ("reports.nuclei_count", "reports.population"),
    "biological_interpretation_agent": (
        "reports.morphology",
        "reports.intensity",
    ),
    "scientific_review_agent": (
        "scientific_execution",
        "input_sha256",
        "adaptive_plan.status",
        "model.weights_updated_during_analysis",
        "reports.nuclei_count",
    ),
    "report_agent": (
        "input_sha256",
        "analysis_modules",
        "reports.nuclei_count",
        "reports.measurement_file",
    ),
}


def _evidence_snapshot(results: dict[str, Any], agent: str) -> tuple[dict[str, Any], str]:
    references: dict[str, Any] = {}
    for path in _EVIDENCE_PATHS[agent]:
        present, value = _path_value(results, path)
        if present:
            references[path] = value
    canonical = json.dumps(
        references, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    return references, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _image_quality(results: dict[str, Any]) -> AgentFinding:
    plan = _mapping(results.get("adaptive_plan"))
    profile = _mapping(plan.get("profile"))
    observations: list[str] = []
    if plan.get("status") is not None:
        observations.append(f"Analysis status: {plan['status']}.")
    for key in ("dtype", "min", "p01", "median", "p995", "max", "saturation_fraction"):
        if key in profile:
            observations.append(f"Raw input profile {key}: {profile[key]}")
    warnings = plan.get("warnings", [])
    limitations = tuple(str(item) for item in warnings) if isinstance(warnings, list) else ()
    return AgentFinding("image_quality_agent", tuple(observations), limitations)


def _segmentation_quality(results: dict[str, Any]) -> AgentFinding:
    reports = _mapping(results.get("reports"))
    plan = _mapping(results.get("adaptive_plan"))
    observations: list[str] = []
    count = reports.get("nuclei_count", results.get("n_instances"))
    if count is not None:
        observations.append(f"Detected instance count: {count}.")
    qc = _mapping(plan.get("cnn_pattern_check"))
    for key in sorted(qc):
        observations.append(f"CNN quality gate {key}: {qc[key]}")
    return AgentFinding(
        "segmentation_quality_agent",
        tuple(observations),
        ("Segmentation quality should be interpreted with the computed diagnostics and visual overlay.",),
    )


def _morphology(results: dict[str, Any]) -> AgentFinding:
    values = _mapping(_mapping(results.get("reports")).get("morphology"))
    observations = tuple(f"{key}: {values[key]}" for key in sorted(values))
    return AgentFinding(
        "morphology_agent",
        observations,
        ("Morphology alone does not establish a biological mechanism or phenotype.",),
    )


def _intensity(results: dict[str, Any]) -> AgentFinding:
    reports = _mapping(results.get("reports"))
    measured = _mapping(reports.get("intensity"))
    plan = _mapping(results.get("adaptive_plan"))
    profile = _mapping(plan.get("profile"))
    observations = [f"{key}: {measured[key]}" for key in sorted(measured)]
    for key in ("dtype", "min", "p01", "median", "p995", "max", "saturation_fraction"):
        if key in profile:
            observations.append(f"Raw input profile {key}: {profile[key]}")
    return AgentFinding(
        "intensity_agent",
        tuple(observations),
        ("Fluorescence intensity depends on acquisition, staining, exposure, background, and detector response.",),
    )


def _population(results: dict[str, Any]) -> AgentFinding:
    reports = _mapping(results.get("reports"))
    observations: list[str] = []
    count = reports.get("nuclei_count", results.get("n_instances"))
    if count is not None:
        observations.append(f"Detected instance count: {count}.")
    population = _mapping(reports.get("population"))
    observations.extend(f"{key}: {population[key]}" for key in sorted(population))
    return AgentFinding(
        "population_agent",
        tuple(observations),
        ("Population comparisons require appropriate controls and biological replicates.",),
    )


def _biological_interpretation(results: dict[str, Any]) -> AgentFinding:
    reports = _mapping(results.get("reports"))
    morphology = _mapping(reports.get("morphology"))
    intensity = _mapping(reports.get("intensity"))
    observations: list[str] = []
    if morphology:
        observations.append("Measured morphology summaries are available for descriptive interpretation.")
    if intensity:
        observations.append("Measured intensity summaries are available for descriptive interpretation.")
    return AgentFinding(
        "biological_interpretation_agent",
        tuple(observations),
        ("No disease, diagnostic, mechanistic, or causal conclusion is inferred from morphology or intensity alone.",),
    )


def _scientific_review(results: dict[str, Any]) -> AgentFinding:
    observations: list[str] = []
    if results.get("scientific_execution") is not None:
        observations.append(f"Scientific execution flag recorded: {results['scientific_execution']}.")
    if results.get("input_sha256"):
        observations.append("Input SHA-256 provenance is recorded.")
    model = _mapping(results.get("model"))
    if "weights_updated_during_analysis" in model:
        observations.append(
            f"Model weight update flag: {model['weights_updated_during_analysis']}."
        )
    plan = _mapping(results.get("adaptive_plan"))
    if plan.get("status") is not None:
        observations.append(f"Recorded analysis status: {plan['status']}.")
    return AgentFinding(
        "scientific_review_agent",
        tuple(observations),
        ("Accuracy, training history, and biological claims must not be asserted without their own verified evidence.",),
    )


def _report(results: dict[str, Any]) -> AgentFinding:
    reports = _mapping(results.get("reports"))
    observations: list[str] = []
    count = reports.get("nuclei_count", results.get("n_instances"))
    if count is not None:
        observations.append(f"Report input includes the computed instance count: {count}.")
    measurement_file = reports.get("measurement_file")
    if measurement_file:
        observations.append(f"Report input references the measurement artifact: {measurement_file}.")
    if results.get("input_sha256"):
        observations.append("Report input includes the source-image SHA-256 digest.")
    return AgentFinding(
        "report_agent",
        tuple(observations),
        ("This specialist runs before report packaging; it does not claim that files have already been generated.",),
    )


_SPECIALIST_FUNCTIONS = {
    "image_quality_agent": _image_quality,
    "segmentation_quality_agent": _segmentation_quality,
    "morphology_agent": _morphology,
    "intensity_agent": _intensity,
    "population_agent": _population,
    "biological_interpretation_agent": _biological_interpretation,
    "scientific_review_agent": _scientific_review,
    "report_agent": _report,
}


def run_expert_agents(results: dict[str, Any]) -> dict[str, Any]:
    """Dispatch deterministic specialists and retain evidence for each execution.

    Each specialist is invoked separately. Findings are descriptive summaries of
    existing computed outputs, not new measurements or independently trained AI.
    A failed specialist emits no observation and is reported as failed.
    """
    records: list[dict[str, Any]] = []
    for name in SPECIALIST_AGENTS:
        references, digest = _evidence_snapshot(results, name)
        try:
            finding = _SPECIALIST_FUNCTIONS[name](results)
            status = "completed" if finding.observations else "insufficient_evidence"
            error_type = None
        except Exception as exc:
            finding = AgentFinding(
                name,
                (),
                ("Specialist execution failed; no scientific finding was emitted.",),
            )
            status = "failed"
            error_type = type(exc).__name__

        observations = list(finding.observations)
        limitations = list(finding.limitations)
        summary = (
            "Observations: " + "; ".join(observations)
            if observations
            else "No finding emitted because the required measured evidence was unavailable."
        )
        if limitations:
            summary += " Limitations: " + "; ".join(limitations)
        record = {
            "agent": name,
            "status": status,
            "observations": observations,
            "limitations": limitations,
            "evidence": {
                "references": references,
                "sha256": digest,
            },
            "summary": summary,
        }
        if error_type is not None:
            record["error_type"] = error_type
        records.append(record)

    failed = sum(item["status"] == "failed" for item in records)
    insufficient = sum(item["status"] == "insufficient_evidence" for item in records)
    completed = sum(item["status"] == "completed" for item in records)
    overall = "completed" if completed == len(SPECIALIST_AGENTS) else (
        "failed" if failed == len(SPECIALIST_AGENTS) else "partial"
    )
    return {
        "agent_version": "1.1",
        "execution_mode": "deterministic_evidence_review",
        "status": overall,
        "execution": {
            "expected": len(SPECIALIST_AGENTS),
            "executed": len(records),
            "completed": completed,
            "insufficient_evidence": insufficient,
            "failed": failed,
        },
        "agents": records,
        "training_status": training_manifest_status(results.get("agent_training_manifest")),
        "evidence_policy": (
            "Specialists interpret existing measured evidence; they do not invent measurements, "
            "biological conclusions, accuracy, or training provenance."
        ),
    }

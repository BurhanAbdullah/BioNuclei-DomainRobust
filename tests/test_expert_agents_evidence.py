from __future__ import annotations

import hashlib
import json

from bionuclei.expert_agents import run_expert_agents, training_manifest_status


def _result(raw_max: int = 65535) -> dict:
    profile = {
        "shape": [512, 512],
        "dtype": "uint16",
        "min": 0,
        "p01": 1200,
        "median": 1200,
        "p995": 1200,
        "max": raw_max,
        "mean": 1200.01,
        "std": 11.0,
        "saturation_fraction": 2 / 262144,
        "zero_fraction": 1 / 262144,
        "finite": True,
    }
    return {
        "input_sha256": "a" * 64,
        "analysis_modules": ["nuclei", "morphology", "intensity"],
        "adaptive_plan": {
            "status": "PASS",
            "warnings": [],
            "profile": profile,
            "cnn_pattern_check": {"executed": True, "status": "PASS"},
        },
        "reports": {
            "nuclei_count": 2,
            "morphology": {"mean_area": 122},
            "intensity": {"mean_nuclear_intensity": 1200, "mean_max_intensity": 30000, "max_nuclear_intensity": raw_max},
            "spatial": {
                "instance_count": 2,
                "unit": "pixels",
                "mean_nearest_neighbor_distance_px": 100.0,
                "median_nearest_neighbor_distance_px": 100.0,
                "min_nearest_neighbor_distance_px": 100.0,
                "max_nearest_neighbor_distance_px": 100.0,
            },
        },
        "model": {
            "architecture": "Boundary U-Net",
            "training_reference": "Not established",
            "weights_updated_during_analysis": False,
        },
    }


def test_uint16_raw_profile_reaches_intensity_agent_and_is_evidence_bound() -> None:
    result = _result()
    output = run_expert_agents(result)
    assert len(output["agents"]) == 8

    intensity = next(agent for agent in output["agents"] if agent["agent"] == "intensity_agent")
    assert "Raw image max: 65535" in intensity["observations"]
    assert "Maximum per-instance nuclear intensity: 65535 raw intensity units." in intensity["observations"]
    assert "Raw image dtype: uint16" in intensity["observations"]
    assert "reports.intensity.max_nuclear_intensity" in intensity["evidence_references"]
    assert any(claim["reference"] == "reports.intensity.max_nuclear_intensity" and claim["value"] == 65535 for claim in intensity["quantitative_claims"])
    assert "adaptive_plan.profile" in intensity["evidence_references"]
    assert "reports.intensity" in intensity["evidence_references"]
    assert len(intensity["evidence_sha256"]) == 64

    evidence = {
        "reports.intensity": result["reports"]["intensity"],
        "adaptive_plan.profile": result["adaptive_plan"]["profile"],
    }
    expected = hashlib.sha256(
        json.dumps(
            evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
        ).encode("utf-8")
    ).hexdigest()
    assert intensity["evidence_sha256"] == expected

    changed = run_expert_agents(_result(raw_max=65534))
    changed_intensity = next(agent for agent in changed["agents"] if agent["agent"] == "intensity_agent")
    assert changed_intensity["evidence_sha256"] != intensity["evidence_sha256"]


def test_missing_or_invalid_training_counts_remain_unknown() -> None:
    missing = training_manifest_status(None)
    assert missing["validated_images"] is None
    assert missing["verified"] is False
    assert missing["claim_allowed"] is False

    invalid = training_manifest_status({"verified": True, "validated_images": "unknown"})
    assert invalid["validated_images"] is None
    assert invalid["verified"] is False
    assert invalid["claim_allowed"] is False



def test_execution_manifest_binds_job_and_spatial_measurements() -> None:
    result = _result()
    result["job_id"] = "job-512-uint16"
    result["reports"]["spatial"] = {
        "instance_count": 2,
        "unit": "pixels",
        "mean_nearest_neighbor_distance_px": 100.0,
        "median_nearest_neighbor_distance_px": 100.0,
        "min_nearest_neighbor_distance_px": 100.0,
        "max_nearest_neighbor_distance_px": 100.0,
    }
    output = run_expert_agents(result)
    assert output["execution"]["status"] == "completed"
    assert output["execution"]["job_id"] == "job-512-uint16"
    assert output["execution"]["input_sha256"] == result["input_sha256"]
    assert output["execution"]["job_id_valid"] is True
    population = next(agent for agent in output["agents"] if agent["agent"] == "population_agent")
    assert "Mean nearest-neighbour distance: 100 pixels." in population["observations"]
    morphology = next(agent for agent in output["agents"] if agent["agent"] == "morphology_agent")
    assert "Measured mean area: 122 pixels^2." in morphology["observations"]
    assert "reports.spatial.mean_nearest_neighbor_distance_px" in population["evidence_references"]
    assert len(population["evidence_sha256"]) == 64


def test_execution_manifest_fails_closed_without_job_binding() -> None:
    output = run_expert_agents(_result())
    assert output["execution"]["status"] == "incomplete"
    assert output["execution"]["job_id"] is None
    assert "missing_or_invalid_job_id" in output["execution"]["incomplete_reasons"]

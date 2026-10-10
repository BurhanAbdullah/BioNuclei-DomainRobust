from __future__ import annotations

from copy import deepcopy
from typing import Any

from bionuclei import expert_agents


def _measured_payload() -> dict[str, Any]:
    return {
        "adaptive_plan": {
            "status": "READY",
            "warnings": [],
            "profile": {
                "shape": [512, 512],
                "dtype": "uint16",
                "min": 0,
                "p01": 18,
                "median": 1200,
                "p995": 65535,
                "max": 65535,
                "saturation_fraction": 1 / (512 * 512),
            },
            "cnn_pattern_check": {"status": "PASS", "score": 0.91},
        },
        "reports": {
            "nuclei_count": 3,
            "morphology": {"mean_area": 4600.0, "mean_eccentricity": 0.42},
            "intensity": {"mean_nuclear_intensity": 28100.0},
            "population": {"quadrants": {"top_left": 2, "bottom_right": 1}},
            "measurement_file": "nuclei_analysis.csv",
        },
        "n_instances": 3,
        "scientific_execution": "completed",
        "input_sha256": "fixture-input-sha256",
        "model": {"weights_updated_during_analysis": False},
    }


def test_dispatches_each_specialist_separately(monkeypatch: Any) -> None:
    calls: list[str] = []

    def make_specialist(name: str):
        def specialist(_results: dict[str, Any]) -> expert_agents.AgentFinding:
            calls.append(name)
            return expert_agents.AgentFinding(name, ("fixture observation",), ())
        return specialist

    for name in expert_agents.SPECIALIST_AGENTS:
        monkeypatch.setitem(
            expert_agents._SPECIALIST_FUNCTIONS, name, make_specialist(name)
        )

    output = expert_agents.run_expert_agents(_measured_payload())

    assert calls == list(expert_agents.SPECIALIST_AGENTS)
    assert output["status"] == "completed"
    assert output["execution"] == {
        "expected": 8,
        "executed": 8,
        "completed": 8,
        "insufficient_evidence": 0,
        "failed": 0,
    }
    assert [item["agent"] for item in output["agents"]] == list(
        expert_agents.SPECIALIST_AGENTS
    )


def test_uint16_full_range_reaches_intensity_specialist_and_evidence() -> None:
    payload = _measured_payload()
    output = expert_agents.run_expert_agents(payload)
    intensity = next(
        item for item in output["agents"] if item["agent"] == "intensity_agent"
    )

    assert any("Raw input profile max: 65535" in text for text in intensity["observations"])
    assert intensity["evidence"]["references"]["adaptive_plan.profile"]["max"] == 65535
    assert len(intensity["evidence"]["sha256"]) == 64

    changed = deepcopy(payload)
    changed["adaptive_plan"]["profile"]["max"] = 65534
    changed_output = expert_agents.run_expert_agents(changed)
    changed_intensity = next(
        item for item in changed_output["agents"] if item["agent"] == "intensity_agent"
    )
    assert changed_intensity["evidence"]["sha256"] != intensity["evidence"]["sha256"]


def test_evidence_digest_is_reproducible() -> None:
    payload = _measured_payload()
    first = expert_agents.run_expert_agents(payload)
    second = expert_agents.run_expert_agents(payload)

    assert [x["evidence"]["sha256"] for x in first["agents"]] == [
        x["evidence"]["sha256"] for x in second["agents"]
    ]


def test_missing_training_manifest_remains_unknown() -> None:
    status = expert_agents.training_manifest_status(None)

    assert status == {
        "status": "unknown",
        "verified": False,
        "validated_images": None,
        "training_reference": None,
        "claim_allowed": False,
    }


def test_unverified_training_manifest_does_not_leak_claims() -> None:
    status = expert_agents.training_manifest_status(
        {"verified": False, "validated_images": 50000, "training_reference": "invented"}
    )

    assert status["status"] == "unverified"
    assert status["verified"] is False
    assert status["validated_images"] is None
    assert status["training_reference"] is None
    assert status["claim_allowed"] is False


def test_verified_training_claim_requires_manifest_and_threshold() -> None:
    verified = expert_agents.training_manifest_status(
        {"verified": True, "validated_images": 1200, "training_reference": "BBBC039v1"}
    )
    below_threshold = expert_agents.training_manifest_status(
        {"verified": True, "validated_images": 999, "training_reference": "BBBC039v1"}
    )

    assert verified["verified"] is True
    assert verified["validated_images"] == 1200
    assert verified["training_reference"] == "BBBC039v1"
    assert verified["claim_allowed"] is True
    assert below_threshold["verified"] is True
    assert below_threshold["claim_allowed"] is False


def test_failed_specialist_has_no_fabricated_finding_or_exception_text(
    monkeypatch: Any,
) -> None:
    def fail(_results: dict[str, Any]) -> expert_agents.AgentFinding:
        raise RuntimeError("sensitive internal details")

    monkeypatch.setitem(expert_agents._SPECIALIST_FUNCTIONS, "morphology_agent", fail)
    output = expert_agents.run_expert_agents(_measured_payload())
    morphology = next(
        item for item in output["agents"] if item["agent"] == "morphology_agent"
    )

    assert output["status"] == "partial"
    assert output["execution"]["failed"] == 1
    assert morphology["status"] == "failed"
    assert morphology["observations"] == []
    assert morphology["error_type"] == "RuntimeError"
    assert "sensitive internal details" not in morphology["summary"]
    assert "sensitive internal details" not in str(output)


def test_missing_measurements_produce_insufficient_evidence_not_biology() -> None:
    output = expert_agents.run_expert_agents({})

    assert output["status"] == "partial"
    assert output["execution"]["insufficient_evidence"] == 8
    for item in output["agents"]:
        assert item["status"] == "insufficient_evidence"
        assert item["observations"] == []
        assert "No finding emitted" in item["summary"]

from __future__ import annotations

import json
import os
import subprocess
import re
import zipfile
from pathlib import Path

import pytest
import yaml

from scripts.validate_tiled_checkpoint import (
    persist_cgroup_memory_evidence,
    persist_validation_evidence,
    resolve_revision_provenance,
    sha256_file,
    validation_revision_provenance,
)


def _sources(root: Path) -> tuple[Path, Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "results.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("results/results.json", "{}")
        zipped.writestr("results/expert_agents.json", "[]")
    result = root / "results.json"
    result.write_text('{"status":"completed"}', encoding="utf-8")
    specialists = root / "expert_agents.json"
    specialists.write_text('{"agents":[1,2,3,4,5,6,7,8]}', encoding="utf-8")
    return archive, result, specialists


def test_persist_validation_evidence_copies_only_verified_derived_outputs(tmp_path: Path) -> None:
    temporary_root = tmp_path / "disposable-job"
    archive, result, specialists = _sources(temporary_root)
    evidence_dir = tmp_path / "runner-evidence"
    manifest = {
        "specialist_count": 8,
        "source_image_excluded": True,
        "checkpoint_unchanged": True,
        "public_inference": False,
    }

    persisted = persist_validation_evidence(
        evidence_dir,
        temporary_root,
        archive,
        result,
        specialists,
        manifest,
    )

    assert {path.name for path in evidence_dir.iterdir()} == {
        "analysis-results.zip",
        "results.json",
        "expert_agents.json",
        "manifest.json",
    }
    assert sha256_file(evidence_dir / "analysis-results.zip") == sha256_file(archive)
    assert sha256_file(evidence_dir / "results.json") == sha256_file(result)
    assert sha256_file(evidence_dir / "expert_agents.json") == sha256_file(specialists)
    saved = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    assert saved["source_image_excluded"] is True
    assert saved["public_inference"] is False
    assert saved["files"]["analysis-results.zip"]["sha256"] == sha256_file(archive)
    assert persisted["manifest_sha256"] == sha256_file(evidence_dir / "manifest.json")


def test_persist_validation_evidence_rejects_disposable_job_subdirectory(tmp_path: Path) -> None:
    temporary_root = tmp_path / "disposable-job"
    archive, result, specialists = _sources(temporary_root)
    manifest = {
        "specialist_count": 8,
        "source_image_excluded": True,
        "checkpoint_unchanged": True,
        "public_inference": False,
    }

    with pytest.raises(AssertionError, match="outside disposable job storage"):
        persist_validation_evidence(
            temporary_root / "evidence",
            temporary_root,
            archive,
            result,
            specialists,
            manifest,
        )


def test_constrained_memory_validation_uses_production_image_thread_defaults() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github" / "workflows" / "tiled-checkpoint-validation.yml").read_text(
            encoding="utf-8"
        ),
        Loader=yaml.BaseLoader,
    )
    triggers = workflow["on"]
    for event in ("pull_request", "push"):
        paths = set(triggers[event]["paths"])
        assert "webapp/Dockerfile" in paths
        assert "webapp/community.Dockerfile" in paths
        assert "deploy/render-cpu-constraints.txt" in paths

    steps = workflow["jobs"]["released-checkpoint"]["steps"]
    api_build_step = next(
        step for step in steps
        if step.get("name") == "Build production API image and verify CPU-only PyTorch"
    )
    assert "docker build --file webapp/Dockerfile" in api_build_step["run"]

    build_step = next(
        step for step in steps
        if step.get("name") == "Build production community image for constrained-memory validation"
    )
    assert "--file webapp/community.Dockerfile" in build_step["run"]
    assert steps.index(api_build_step) < steps.index(build_step)

    memory_step = next(
        step for step in steps
        if step.get("name") == "Run real checkpoint worker with a 480 MiB hard memory limit"
    )
    command = memory_step["run"]
    # Keep the validation harness outside the production image while mounting
    # only the single read-only validator at the path it expects under /app.
    assert 'VALIDATOR_DIR="$RUNNER_TEMP/bionuclei-validation-scripts"' in command
    assert 'cp scripts/validate_tiled_checkpoint.py "$VALIDATOR_DIR/validate_tiled_checkpoint.py"' in command
    assert '--volume "$VALIDATOR_DIR:/app/scripts:ro"' in command
    assert "python scripts/validate_tiled_checkpoint.py" in command
    for variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        assert f"--env {variable}=1" not in command
    assert "for variable in OMP_NUM_THREADS MKL_NUM_THREADS OPENBLAS_NUM_THREADS NUMEXPR_NUM_THREADS; do" in command
    assert 'value="$(printenv "$variable" 2>/dev/null || true)"' in command
    assert 'if [ "$value" != "1" ]; then' in command
    assert "--memory=503316480" in command
    assert '[ "$memory_peak" -le 492830720 ]' in command


def test_both_production_images_use_the_same_single_thread_defaults() -> None:
    root = Path(__file__).resolve().parents[1]
    variables = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")
    for relative in ("webapp/Dockerfile", "webapp/community.Dockerfile"):
        env_block = (root / relative).read_text(encoding="utf-8").split("\n\n", 2)[1]
        for variable in variables:
            assert f"{variable}=1" in env_block, f"{relative} is missing {variable}=1"


def test_both_production_images_pin_cpu_only_pytorch() -> None:
    root = Path(__file__).resolve().parents[1]
    constraints = (root / "deploy" / "render-cpu-constraints.txt").read_text(encoding="utf-8")
    assert "--extra-index-url https://download.pytorch.org/whl/cpu" in constraints
    assert "torch==2.14.0+cpu" in constraints
    assert "torchvision==0.29.0+cpu" in constraints

    for relative in ("webapp/Dockerfile", "webapp/community.Dockerfile"):
        dockerfile = (root / relative).read_text(encoding="utf-8")
        assert "COPY deploy/render-cpu-constraints.txt ./deploy/render-cpu-constraints.txt" in dockerfile
        assert 'pip install --constraint deploy/render-cpu-constraints.txt -e ".[web]"' in dockerfile
        assert "torch.version.cuda is None" in dockerfile

    workflow = yaml.load(
        (root / ".github" / "workflows" / "tiled-checkpoint-validation.yml").read_text(
            encoding="utf-8"
        ),
        Loader=yaml.BaseLoader,
    )
    install = next(
        step for step in workflow["jobs"]["released-checkpoint"]["steps"]
        if step.get("name") == "Install production web dependencies"
    )
    assert "--constraint deploy/render-cpu-constraints.txt" in install["run"]
    assert "torch.version.cuda is None" in install["run"]


@pytest.mark.parametrize(
    ("exit_codes", "expected_status", "expected_calls"),
    [
        ("0", 0, 1),
        ("17,0", 0, 2),
        ("17,23", 23, 2),
    ],
)
def test_constrained_memory_gate_retries_only_after_a_failed_docker_run(
    tmp_path: Path,
    exit_codes: str,
    expected_status: int,
    expected_calls: int,
) -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github" / "workflows" / "tiled-checkpoint-validation.yml").read_text(
            encoding="utf-8"
        ),
        Loader=yaml.BaseLoader,
    )
    memory_step = next(
        step for step in workflow["jobs"]["released-checkpoint"]["steps"]
        if step.get("name") == "Run real checkpoint worker with a 480 MiB hard memory limit"
    )
    command = memory_step["run"]
    assert "if docker run --rm" in command
    assert 'exit "$last_status"' in command

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    counter = tmp_path / "docker-calls.txt"
    docker = fake_bin / "docker"
    docker.write_text(
        "#!/usr/bin/env python3\n"
        "import os\n"
        "import sys\n"
        "from pathlib import Path\n"
        "counter = Path(os.environ['DOCKER_CALL_COUNTER'])\n"
        "calls = int(counter.read_text()) + 1 if counter.exists() else 1\n"
        "counter.write_text(str(calls))\n"
        "codes = [int(value) for value in os.environ['DOCKER_EXIT_CODES'].split(',')]\n"
        "sys.exit(codes[min(calls - 1, len(codes) - 1)])\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)

    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"immutable-checkpoint-placeholder")
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{env.get('PATH', '')}",
            "RUNNER_TEMP": str(runner_temp),
            "BIONUCLEI_CHECKPOINT": str(checkpoint),
            "EXPECTED_SHA256": "0" * 64,
            "DOCKER_CALL_COUNTER": str(counter),
            "DOCKER_EXIT_CODES": exit_codes,
        }
    )

    completed = subprocess.run(
        ["bash", "-c", command],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == expected_status, completed.stdout + completed.stderr
    assert int(counter.read_text(encoding="utf-8")) == expected_calls
    assert "Constrained-memory validation attempt 1/2" in completed.stdout
    if expected_calls == 2:
        assert "Constrained-memory validation attempt 2/2" in completed.stdout
    else:
        assert "Constrained-memory validation attempt 2/2" not in completed.stdout


def test_production_api_image_runs_health_with_the_pinned_checkpoint() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github" / "workflows" / "tiled-checkpoint-validation.yml").read_text(
            encoding="utf-8"
        ),
        Loader=yaml.BaseLoader,
    )
    steps = workflow["jobs"]["released-checkpoint"]["steps"]
    api_build = next(
        step for step in steps
        if step.get("name") == "Build production API image and verify CPU-only PyTorch"
    )
    api_health = next(
        step for step in steps
        if step.get("name") == "Run production API image health check with the pinned checkpoint"
    )
    community_build = next(
        step for step in steps
        if step.get("name") == "Build production community image for constrained-memory validation"
    )

    assert steps.index(api_build) < steps.index(api_health) < steps.index(community_build)
    command = api_health["run"]
    for required in (
        "docker run --detach",
        "--volume \"$BIONUCLEI_CHECKPOINT:/opt/models/bionuclei.pt:ro\"",
        "http://127.0.0.1:18000/health",
        "checkpoint_available",
        "checkpoint_verified",
        "checkpoint_sha256",
        "docker logs",
        "docker rm -f",
    ):
        assert required in command
    assert api_health["env"]["EXPECTED_SHA256"] == (
        "7209a6990514380804210292ac208b0f3b0b0a054338a145e1916044762d7c92"
    )


def test_pull_request_manifest_binds_source_base_and_tested_merge_commits() -> None:
    source_sha = "a" * 40
    base_sha = "b" * 40
    merge_sha = "c" * 40

    provenance = resolve_revision_provenance(
        "pull_request",
        merge_sha,
        {
            "pull_request": {
                "head": {"sha": source_sha},
                "base": {"sha": base_sha},
            }
        },
    )

    assert provenance == {
        "event_name": "pull_request",
        "head_sha": source_sha,
        "base_sha": base_sha,
        "tested_sha": merge_sha,
    }


def test_push_manifest_uses_the_pushed_commit_as_source_and_tested_sha() -> None:
    pushed_sha = "d" * 40

    provenance = resolve_revision_provenance("push", pushed_sha)

    assert provenance == {
        "event_name": "push",
        "head_sha": pushed_sha,
        "base_sha": None,
        "tested_sha": pushed_sha,
    }


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"pull_request": {"head": {"sha": "a" * 40}}},
        {
            "pull_request": {
                "head": {"sha": "not-a-sha"},
                "base": {"sha": "b" * 40},
            }
        },
    ],
)
def test_pull_request_provenance_fails_closed_without_valid_head_and_base(payload) -> None:
    with pytest.raises(ValueError):
        resolve_revision_provenance("pull_request", "c" * 40, payload)


def test_revision_provenance_rejects_invalid_workflow_sha() -> None:
    with pytest.raises(ValueError, match="GITHUB_SHA"):
        resolve_revision_provenance("push", "not-a-sha")


def test_validation_revision_provenance_reads_pull_request_event_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_sha = "e" * 40
    base_sha = "f" * 40
    merge_sha = "1" * 40
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "pull_request": {
                    "head": {"sha": source_sha},
                    "base": {"sha": base_sha},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_SHA", merge_sha)
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))

    assert validation_revision_provenance() == {
        "event_name": "pull_request",
        "head_sha": source_sha,
        "base_sha": base_sha,
        "tested_sha": merge_sha,
    }


def test_cgroup_memory_evidence_is_bound_to_runner_manifest(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    manifest = {
        "evidence_scope": "github_actions_checkpoint_validation_runner_only_not_public_inference",
        "public_inference": False,
        "files": {},
    }
    (evidence_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    memory_evidence = {
        "limit_bytes": 503316480,
        "peak_bytes": 243752960,
        "accounting_source": "cgroup_v2",
    }
    memory_path = evidence_dir / "cgroup-memory.json"
    memory_path.write_text(json.dumps(memory_evidence), encoding="utf-8")

    persisted = persist_cgroup_memory_evidence(
        evidence_dir,
        memory_evidence["limit_bytes"],
        memory_evidence["peak_bytes"],
        memory_evidence["accounting_source"],
    )

    updated = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    assert updated["cgroup_memory_limit_bytes"] == 503316480
    assert updated["cgroup_memory_peak_bytes"] == 243752960
    assert updated["cgroup_memory_headroom_bytes"] == 259563520
    assert updated["cgroup_memory_safety_target_bytes"] == 492830720
    assert updated["cgroup_memory_accounting_source"] == "cgroup_v2"
    assert updated["cgroup_memory_gate"] == "passed"
    assert updated["files"]["cgroup-memory.json"] == {
        "sha256": sha256_file(memory_path),
        "size_bytes": memory_path.stat().st_size,
    }
    assert persisted["manifest_sha256"] == sha256_file(evidence_dir / "manifest.json")


@pytest.mark.parametrize(
    ("limit_bytes", "peak_bytes", "accounting_source", "message"),
    [
        (503316479, 243752960, "cgroup_v2", "480 MiB"),
        (503316480, 492830721, "cgroup_v2", "470 MiB safety target"),
        (503316480, 243752960, "unknown", "cgroup v1 or v2"),
        (True, 243752960, "cgroup_v2", "must be an integer"),
    ],
)
def test_cgroup_memory_evidence_rejects_unverified_or_over_budget_values(
    tmp_path: Path,
    limit_bytes: object,
    peak_bytes: object,
    accounting_source: object,
    message: str,
) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "manifest.json").write_text(
        json.dumps(
            {
                "evidence_scope": "github_actions_checkpoint_validation_runner_only_not_public_inference",
                "public_inference": False,
                "files": {},
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "cgroup-memory.json").write_text(
        json.dumps(
            {
                "limit_bytes": limit_bytes,
                "peak_bytes": peak_bytes,
                "accounting_source": accounting_source,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match=message):
        persist_cgroup_memory_evidence(
            evidence_dir,
            limit_bytes,
            peak_bytes,
            accounting_source,
        )


def test_constrained_memory_peak_is_persisted_before_artifact_upload() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github" / "workflows" / "tiled-checkpoint-validation.yml").read_text(
            encoding="utf-8"
        ),
        Loader=yaml.BaseLoader,
    )
    steps = workflow["jobs"]["released-checkpoint"]["steps"]
    memory = next(
        step for step in steps
        if step.get("name") == "Run real checkpoint worker with a 480 MiB hard memory limit"
    )
    persist = next(
        step for step in steps
        if step.get("name") == "Persist constrained-memory evidence in the runner manifest"
    )
    upload = next(
        step for step in steps
        if step.get("name") == "Upload verified runner-only checkpoint evidence"
    )

    assert memory.get("id") == "memory_validation"
    assert steps.index(memory) < steps.index(persist) < steps.index(upload)
    assert '--volume "$EVIDENCE_DIR:/evidence"' in memory["run"]
    assert "/evidence/cgroup-memory.json" in memory["run"]
    assert 'printf "{\\"limit_bytes\\":%s,\\"peak_bytes\\":%s,\\"accounting_source\\":\\"%s\\"}\\n"' in memory["run"]
    shell_match = re.search(
        r"sh -lc '\\n(.*?)\\n[ \\t]*'\\n[ \\t]*then(?:\\n|$)",
        memory["run"],
        flags=re.DOTALL,
    )
    assert shell_match is not None, "could not isolate the constrained-memory shell script"
    inner_script = shell_match.group(1)
    syntax = subprocess.run(
        ["sh", "-n"],
        input=inner_script,
        capture_output=True,
        text=True,
        check=False,
    )
    assert syntax.returncode == 0, syntax.stderr
    assert 'memory_source="cgroup_v2"' in memory["run"]
    assert 'memory_source="cgroup_v1"' in memory["run"]
    assert "persist_cgroup_memory_evidence" in persist["run"]
    assert "steps.memory_validation.outcome == 'success'" in upload["if"]
    assert "steps.persist_memory_evidence.outcome == 'success'" in upload["if"]

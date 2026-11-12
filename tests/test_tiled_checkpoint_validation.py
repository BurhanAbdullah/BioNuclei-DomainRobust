from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml

from scripts.validate_tiled_checkpoint import persist_validation_evidence, sha256_file


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


@pytest.mark.parametrize(
    ("exit_codes", "expected_status", "expected_calls"),
    [
        ("17,0", 0, 2),
        ("17,23", 23, 2),
    ],
)
def test_constrained_memory_gate_retries_failed_docker_attempts(
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
    assert "Constrained-memory validation attempt 2/2" in completed.stdout

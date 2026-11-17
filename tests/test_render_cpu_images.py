from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CPU_CONSTRAINTS = ROOT / "deploy" / "render-cpu-constraints.txt"


def test_render_images_install_cpu_only_pytorch_and_limit_thread_pools() -> None:
    constraints = CPU_CONSTRAINTS.read_text(encoding="utf-8")
    assert "--extra-index-url https://download.pytorch.org/whl/cpu" in constraints
    assert "torch==2.14.0+cpu" in constraints
    assert "torchvision==0.29.0+cpu" in constraints

    for relative, label in (
        ("webapp/Dockerfile", "API"),
        ("webapp/community.Dockerfile", "community"),
    ):
        dockerfile = (ROOT / relative).read_text(encoding="utf-8")
        assert "COPY deploy/render-cpu-constraints.txt ./deploy/render-cpu-constraints.txt" in dockerfile
        assert '--constraint deploy/render-cpu-constraints.txt -e ".[web]"' in dockerfile
        assert "torch.version.cuda is None" in dockerfile
        for variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            assert f"{variable}=1" in dockerfile, f"{relative} is missing {variable}=1"
        assert f"Render {label} image must use CPU-only PyTorch" in dockerfile


def test_checkpoint_validation_uses_the_same_cpu_only_runtime_constraints() -> None:
    workflow_path = ROOT / ".github" / "workflows" / "tiled-checkpoint-validation.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    for event in ("pull_request", "push"):
        paths = set(workflow["on"][event]["paths"])
        assert "webapp/Dockerfile" in paths
        assert "webapp/community.Dockerfile" in paths
        assert "deploy/render-cpu-constraints.txt" in paths

    steps = workflow["jobs"]["released-checkpoint"]["steps"]
    install = next(step for step in steps if step.get("name") == "Install production web dependencies")
    assert "--constraint deploy/render-cpu-constraints.txt" in install["run"]
    assert "torch.version.cuda is None" in install["run"]

    memory = next(step for step in steps if step.get("name") == "Run real checkpoint worker with a 480 MiB hard memory limit")
    assert "for attempt in 1 2" not in memory["run"]
    assert "Constrained-memory validation attempt" not in memory["run"]
    assert memory["run"].count("docker run --rm") == 1

    api_build = next(
        step for step in steps
        if step.get("name") == "Build production API image and verify CPU-only PyTorch"
    )
    community_build = next(
        step for step in steps
        if step.get("name") == "Build production community image for constrained-memory validation"
    )
    assert "docker build --file webapp/Dockerfile --tag bionuclei-api-image ." in api_build["run"]
    assert "docker build --file webapp/community.Dockerfile --tag bionuclei-memory-gate ." in community_build["run"]
    assert steps.index(api_build) < steps.index(community_build) < steps.index(memory)

    command = memory["run"]
    assert 'VALIDATOR_DIR="$RUNNER_TEMP/bionuclei-validation-scripts"' in command
    assert 'cp scripts/validate_tiled_checkpoint.py "$VALIDATOR_DIR/validate_tiled_checkpoint.py"' in command
    assert '--volume "$VALIDATOR_DIR:/app/scripts:ro"' in command
    assert "bionuclei-memory-gate" in command
    assert "for variable in OMP_NUM_THREADS MKL_NUM_THREADS OPENBLAS_NUM_THREADS NUMEXPR_NUM_THREADS; do" in command
    assert 'if [ "$value" != "1" ]; then' in command
    assert command.count("docker run --rm") == 1
    assert "--memory=503316480" in command
    assert '[ "$memory_limit" -eq 503316480 ]' in command
    assert '[ "$memory_peak" -le 492830720 ]' in command
    workflow_text = workflow_path.read_text(encoding="utf-8")
    assert "Dockerfile.bionuclei-memory" not in workflow_text
    assert "COPY . /app" not in workflow_text

import yaml
from pathlib import Path


def test_constrained_memory_validation_uses_production_image_thread_defaults() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github" / "workflows" / "tiled-checkpoint-validation.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    triggers = workflow["on"]
    for event in ("pull_request", "push"):
        assert "webapp/community.Dockerfile" in triggers[event]["paths"]
        assert "webapp/Dockerfile" in triggers[event]["paths"]

    steps = workflow["jobs"]["released-checkpoint"]["steps"]
    build = next(step for step in steps if step.get("name") == "Build production community image for constrained-memory validation")
    assert "docker build --file webapp/community.Dockerfile" in build["run"]
    memory_step = next(step for step in steps if step.get("name") == "Run real checkpoint worker with a 480 MiB hard memory limit")
    command = memory_step["run"]
    assert 'VALIDATOR_DIR="$RUNNER_TEMP/bionuclei-validation-scripts"' in command
    assert 'cp scripts/validate_tiled_checkpoint.py "$VALIDATOR_DIR/validate_tiled_checkpoint.py"' in command
    assert '--volume "$VALIDATOR_DIR:/app/scripts:ro"' in command
    assert "for variable in OMP_NUM_THREADS MKL_NUM_THREADS OPENBLAS_NUM_THREADS NUMEXPR_NUM_THREADS; do" in command
    assert 'if [ "$value" != "1" ]; then' in command
    assert "--memory=503316480" in command
    assert '[ "$memory_peak" -le 492830720 ]' in command


def test_production_dockerfiles_cap_thread_pools() -> None:
    root = Path(__file__).resolve().parents[1]
    variables = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")
    for relative in ("webapp/Dockerfile", "webapp/community.Dockerfile"):
        content = (root / relative).read_text(encoding="utf-8")
        for variable in variables:
            assert f"{variable}=1" in content, f"{relative} is missing {variable}=1"

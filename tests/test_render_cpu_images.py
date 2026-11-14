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
        assert "--constraint deploy/render-cpu-constraints.txt -e \".[web]\"" in dockerfile
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

    build = next(step for step in steps if step.get("name") == "Build isolated image for constrained-memory validation")
    assert "COPY . /app" in build["run"]
    assert "deploy/render-cpu-constraints.txt" in build["run"]
    assert "torch.version.cuda is None" in build["run"]
    assert "OMP_NUM_THREADS=1" in build["run"]


def test_biomcp_and_clean_reproduction_workflows_use_cpu_only_pytorch() -> None:
    bio_path = ROOT / ".github" / "workflows" / "biomcp_web_validation.yml"
    bio = yaml.load(bio_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    for event in ("push", "pull_request"):
        assert "deploy/render-cpu-constraints.txt" in bio["on"][event]["paths"]

    for job_name in ("mcp", "web"):
        steps = bio["jobs"][job_name]["steps"]
        install = next(step for step in steps if step.get("name") in ("Install package with MCP extra", "Install web extra"))
        assert "--constraint deploy/render-cpu-constraints.txt" in install["run"]
        verify = next(step for step in steps if step.get("name") == "Verify CPU-only PyTorch")
        assert "torch.version.cuda is None" in verify["run"]

    clean_path = ROOT / ".github" / "workflows" / "clean_environment_reproduction.yml"
    clean = yaml.load(clean_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    steps = clean["jobs"]["reproduce"]["steps"]
    install = next(step for step in steps if step.get("name") == "Install project and all test/runtime extras")
    assert "--constraint deploy/render-cpu-constraints.txt" in install["run"]
    verify = next(step for step in steps if step.get("name") == "Verify clean environment")
    assert "torch.version.cuda is None" in verify["run"]

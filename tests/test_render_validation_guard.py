from pathlib import Path

import yaml


def test_live_render_validation_requires_explicit_upstream_opt_in() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github/workflows/community_analyzer_validation.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert inputs["allow_live_render"]["default"] == "false"
    assert "ephemeral guest-session creation" in inputs["allow_live_render"]["description"]
    assert workflow["jobs"]["live"]["if"] == (
        "${{ github.event_name == 'workflow_dispatch' "
        "&& github.repository == 'BurhanAbdullah/BioNuclei-DomainRobust' "
        "&& github.ref == 'refs/heads/main' && inputs.allow_live_render == true }}"
    )

def test_memory_gate_tracks_and_builds_cpu_only_community_image() -> None:
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "webapp/community.Dockerfile").read_text(encoding="utf-8")
    assert "COPY deploy/render-cpu-constraints.txt ./deploy/render-cpu-constraints.txt" in dockerfile
    assert "--constraint deploy/render-cpu-constraints.txt -e \".[web]\"" in dockerfile
    assert "torch.version.cuda is None" in dockerfile
    for variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        assert f"{variable}=1" in dockerfile

    workflow = yaml.load(
        (root / ".github/workflows/tiled-checkpoint-validation.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    for event in ("pull_request", "push"):
        paths = set(workflow["on"][event]["paths"])
        assert "webapp/community.Dockerfile" in paths
        assert "deploy/render-cpu-constraints.txt" in paths

    steps = workflow["jobs"]["released-checkpoint"]["steps"]
    install = next(step for step in steps if step.get("name") == "Install production web dependencies")
    assert "--constraint deploy/render-cpu-constraints.txt" in install["run"]
    assert "torch.version.cuda is None" in install["run"]
    build = next(step for step in steps if step.get("name") == "Build production community image for constrained-memory validation")
    assert "docker build --file webapp/community.Dockerfile" in build["run"]

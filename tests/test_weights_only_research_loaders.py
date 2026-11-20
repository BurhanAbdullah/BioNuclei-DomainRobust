"""Research checkpoint loaders must reject arbitrary pickle globals."""
from __future__ import annotations

import ast
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
EVALUATORS = (
    "scripts/evaluate_bbbc039.py",
    "scripts/evaluate_bbbc038.py",
    "scripts/evaluate_instance_manifest.py",
    "scripts/audit_bbbc039_instances.py",
    "scripts/evaluate_s_biad634.py",
)
E6_WORKFLOWS = (
    ".github/workflows/e6_25pct_recovery.yml",
    ".github/workflows/e6_external_few_shot.yml",
)



def test_research_evaluators_use_restricted_checkpoint_unpickling() -> None:
    for relative in EVALUATORS:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"), filename=relative)
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "load"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "torch"
        ]
        assert len(calls) == 1, f"{relative} should have exactly one torch.load call"
        kwargs = {keyword.arg: keyword.value for keyword in calls[0].keywords}
        assert isinstance(kwargs.get("weights_only"), ast.Constant)
        assert kwargs["weights_only"].value is True, f"{relative} must use weights_only=True"


def test_e6_workflow_checkpoint_loads_are_weights_only() -> None:
    for relative in E6_WORKFLOWS:
        workflow = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
        run_texts = [
            step.get("run", "")
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
        ]
        loaders = [run for run in run_texts if "torch.load" in run]
        assert loaders, f"{relative} must retain a checkpoint loader"
        assert all("weights_only=True" in run and "weights_only=False" not in run for run in loaders), relative

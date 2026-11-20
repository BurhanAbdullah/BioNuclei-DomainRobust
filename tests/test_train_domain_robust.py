import hashlib
import json
from pathlib import Path

import pytest
import torch
import yaml

from scripts.train_domain_robust import build_training_metadata, resolve_device


def test_resolve_device_auto_falls_back_to_cpu(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert resolve_device("auto").type == "cpu"


def test_resolve_device_auto_uses_cuda_when_available(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert resolve_device("auto").type == "cuda"


def test_training_metadata_matches_source_manifest_and_config(tmp_path):
    config = {"experiment": "e5_full_frozen_e4", "seed": 42}
    manifest = {"dataset": "BBBC039v1", "partitions": {"train": ["image_1.tif"]}}
    config_path = tmp_path / "config.yaml"
    manifest_path = tmp_path / "split.json"
    source_download_manifest_path = tmp_path / "download_manifest.json"
    source_download_manifest_path.write_text(json.dumps({"dataset": "BBBC039v1", "archives": {}}), encoding="utf-8")
    config_path.write_text("experiment: e5_full_frozen_e4\nseed: 42\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    metadata = build_training_metadata(
        config,
        manifest,
        config_path,
        manifest_path,
        tmp_path / "BBBC039",
        None,
        epochs=20,
        source_download_manifest_path=source_download_manifest_path,
    )

    assert metadata["method"] == "source_manifest_training"
    assert metadata["training_dataset"] == "BBBC039v1"
    assert metadata["source_split_manifest_sha256"] == hashlib.sha256(
        manifest_path.read_bytes()
    ).hexdigest()
    assert metadata["config_sha256"] == hashlib.sha256(config_path.read_bytes()).hexdigest()
    assert metadata["source_download_manifest_sha256"] == hashlib.sha256(source_download_manifest_path.read_bytes()).hexdigest()
    assert metadata["initialization"] == "random_initialization"
    assert metadata["init_checkpoint"] is None
    assert metadata["init_checkpoint_sha256"] is None
    assert "adaptation_dataset" not in metadata
    assert "target_data_used_for_training" not in metadata


def test_training_metadata_hashes_initial_checkpoint(tmp_path):
    config_path = tmp_path / "config.yaml"
    manifest_path = tmp_path / "split.json"
    checkpoint_path = tmp_path / "initial.pt"
    config = {"experiment": "fine_tune", "seed": 7}
    manifest = {"dataset": "BBBC039v1", "partitions": {"train": ["image_1.tif"]}}
    config_path.write_text("experiment: fine_tune\nseed: 7\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    checkpoint_path.write_bytes(b"initial checkpoint bytes")

    metadata = build_training_metadata(
        config,
        manifest,
        config_path,
        manifest_path,
        tmp_path / "BBBC039",
        checkpoint_path,
        epochs=3,
    )

    assert metadata["method"] == "source_manifest_training"
    assert metadata["initialization"] == "checkpoint_finetuning"
    assert metadata["init_checkpoint"] == str(checkpoint_path)
    assert metadata["init_checkpoint_sha256"] == hashlib.sha256(
        checkpoint_path.read_bytes()
    ).hexdigest()
    assert metadata["source_download_manifest_sha256"] is None


def test_e5_gate_validates_per_variant_hashes_and_shared_protocol():
    workflow_path = Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'e5_ablations.yml'
    workflow = yaml.load(workflow_path.read_text(encoding='utf-8'), Loader=yaml.BaseLoader)
    gate = next(step for step in workflow['jobs']['e5_gate']['steps'] if step.get('name') == 'Verify all preregistered variants and provenance')
    assert gate['env']['EXPECTED_COMMIT'] == '${{ github.sha }}'
    assert gate['env']['EXPECTED_RUN_ID'] == '${{ github.run_id }}'
    for required in ('verify_variant_evidence', 'source_split_identity', 'source_acquisition_identity', 'target_manifest_identity', 'shared_training_identity'):
        assert required in gate['run']
    helper_path = Path(__file__).resolve().parents[1] / 'scripts' / 'e5_run_ablation.py'
    helper = helper_path.read_text(encoding='utf-8')
    runner_path = Path(__file__).resolve().parents[1] / 'scripts' / 'e5_run_ablation.py'
    runner = runner_path.read_text(encoding='utf-8')
    assert runner.count("'metrics_sha256': sha256(eval_out / 'metrics.json')") == 1
    for required in ('source_split_manifest.json', 'source_download_manifest.json', 'target_download_manifest.json'):
        assert required in runner
    for required in ('source_split_manifest.json', 'target_download_manifest.json', 'metrics_sha256', 'checkpoint_sha256', 'method_record_sha256', 'random_initialization'):
        assert required in helper

def test_expensive_research_workflows_only_auto_run_on_main():
    root = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    for name in ("e4_domain_robust.yml", "e5_ablations.yml"):
        workflow = yaml.load((root / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        assert workflow["on"]["push"]["branches"] == ["main"]


def test_training_metadata_rejects_mismatched_source_acquisition_dataset(tmp_path):
    config = {"experiment": "e4_domain_robust", "seed": 42}
    manifest = {"dataset": "BBBC039v1", "partitions": {"train": ["image_1.tif"]}}
    config_path = tmp_path / "config.yaml"
    manifest_path = tmp_path / "split.json"
    source_download_manifest_path = tmp_path / "download_manifest.json"
    config_path.write_text("experiment: e4_domain_robust\nseed: 42\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    source_download_manifest_path.write_text(
        json.dumps({"dataset": "S-BIAD634", "archives": {}}), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="identify different datasets"):
        build_training_metadata(
            config,
            manifest,
            config_path,
            manifest_path,
            tmp_path / "BBBC039",
            None,
            epochs=20,
            source_download_manifest_path=source_download_manifest_path,
        )


def test_e5_provenance_records_workflow_commit_and_run(monkeypatch):
    from scripts.e5_run_ablation import workflow_identity

    monkeypatch.setenv("GITHUB_SHA", "abc123commit")
    monkeypatch.setenv("GITHUB_RUN_ID", "123456789")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    assert workflow_identity() == {
        "commit": "abc123commit",
        "workflow_run_id": "123456789",
        "ref": "refs/heads/main",
    }


def test_e5_gate_requires_exact_commit_and_run_identity():
    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "e5_ablations.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    gate = next(step for step in workflow["jobs"]["e5_gate"]["steps"] if step.get("name") == "Verify all preregistered variants and provenance")
    assert gate["env"]["EXPECTED_COMMIT"] == "${{ github.sha }}"
    assert gate["env"]["EXPECTED_RUN_ID"] == "${{ github.run_id }}"
    assert "verify_variant_evidence(root,name,expected_commit,expected_run_id)" in gate["run"]
    helper_path = Path(__file__).resolve().parents[1] / "scripts" / "e5_run_ablation.py"
    helper = helper_path.read_text(encoding="utf-8")
    assert "assert provenance['commit'] == expected_commit" in helper
    assert "assert provenance['workflow_run_id'] == expected_run_id" in helper


def test_e5_epochs_are_fixed_to_preregistered_protocol():
    workflow_path = Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'e5_ablations.yml'
    workflow = yaml.load(workflow_path.read_text(encoding='utf-8'), Loader=yaml.BaseLoader)
    assert 'epochs' not in workflow.get('workflow_dispatch', {}).get('inputs', {})
    variant_step = next(step for step in workflow['jobs']['e5_variant']['steps'] if step.get('name') == 'Run preregistered E5 variant')
    assert variant_step['env']['EPOCHS'] == '20'

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.verify_bbbc039_baseline_run import validate_baseline_run
from scripts.verify_bbbc039_checkpoint import validate_checkpoint_metadata
from scripts.verify_bbbc039_artifact_provenance import build_baseline_artifact_provenance


EXPECTED_SHA = "d4a653e94501e8b9f1ec9de09ff71720f90ab340"


def baseline_run(**overrides):
    metadata = {
        "id": 12345,
        "name": "BBBC039 baseline experiment",
        "path": ".github/workflows/bbbc039_baseline.yml",
        "head_branch": "main",
        "head_sha": EXPECTED_SHA,
        "status": "completed",
        "conclusion": "success",
    }
    metadata.update(overrides)
    return metadata


def baseline_config():
    return {
        "experiment": "bbbc039_baseline",
        "seed": 42,
        "training": {
            "device": "auto",
            "epochs": 100,
            "batch_size": 8,
            "num_workers": 4,
            "learning_rate": 0.0003,
            "weight_decay": 0.00001,
        },
    }


def checkpoint_metadata(config=None, *, seed=42, epochs_run=100):
    return {
        "config": baseline_config() if config is None else config,
        "seed": seed,
        "epochs_run": epochs_run,
    }


def test_accepts_successful_baseline_from_exact_main_commit():
    assert validate_baseline_run(baseline_run(), EXPECTED_SHA) == {
        "run_id": "12345",
        "baseline_sha": EXPECTED_SHA,
    }


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"head_branch": "fix/untrusted-pr"}, "must originate from main"),
        ({"head_sha": "b" * 40}, "does not match"),
        ({"conclusion": "failure"}, "completed successfully"),
        ({"status": "in_progress"}, "completed successfully"),
        ({"name": "unrelated workflow"}, "not the BBBC039 baseline"),
        ({"path": ".github/workflows/unrelated.yml"}, "does not use the BBBC039 baseline workflow file"),
        ({"id": 0}, "valid run ID"),
    ],
)
def test_rejects_untrusted_or_stale_baseline_run(overrides, message):
    with pytest.raises(ValueError, match=message):
        validate_baseline_run(baseline_run(**overrides), EXPECTED_SHA)


def test_rejects_the_observed_pr108_baseline_run():
    # Exact provenance of baseline run #42582135791, consumed by current-main
    # zero-shot run #42598700943 before the provenance guard was added.
    pr_baseline = baseline_run(
        id=42582135791,
        head_branch="fix/report-configured-retention-on-pinned-checkpoint-20261109",
        head_sha="73fe9ff4a38295c7372b3d06e052034ff0b0c231",
    )
    with pytest.raises(ValueError, match="must originate from main"):
        validate_baseline_run(pr_baseline, EXPECTED_SHA)


def test_rejects_the_observed_pr109_baseline_run():
    # Exact provenance of baseline run #42771485283, consumed by current-main
    # zero-shot run #42780911279 before the provenance guard was added.
    pr_baseline = baseline_run(
        id=42771485283,
        head_branch="fix/guard-s-biad634-baseline-provenance-20261109",
        head_sha="18980f4ae69ca3e502afc2619c4c345aa0f8694c",
    )
    with pytest.raises(ValueError, match="must originate from main"):
        validate_baseline_run(pr_baseline, EXPECTED_SHA)


def test_rejects_malformed_expected_commit_sha():
    with pytest.raises(ValueError, match="full lowercase 40-character commit"):
        validate_baseline_run(baseline_run(), "not-a-commit")


def test_accepts_checkpoint_trained_with_exact_committed_recipe():
    assert validate_checkpoint_metadata(checkpoint_metadata(), baseline_config()) == {
        "seed": 42,
        "epochs_run": 100,
    }


def test_rejects_checkpoint_that_only_trained_twenty_of_one_hundred_epochs():
    with pytest.raises(ValueError, match="epochs_run does not match"):
        validate_checkpoint_metadata(
            checkpoint_metadata(epochs_run=20),
            baseline_config(),
        )


def test_rejects_checkpoint_with_wrong_seed():
    with pytest.raises(ValueError, match="seed does not match"):
        validate_checkpoint_metadata(
            checkpoint_metadata(seed=7),
            baseline_config(),
        )


def test_rejects_historical_checkpoint_that_claimed_unimplemented_training_options():
    # Metadata read from baseline run #42771485283: config said 100 epochs,
    # AMP, early stopping and geometric augmentation, but epochs_run was 20.
    historical_config = {
        **baseline_config(),
        "training": {
            **baseline_config()["training"],
            "amp": True,
            "early_stopping_patience": 20,
        },
        "augmentation": {
            "horizontal_flip": True,
            "vertical_flip": True,
            "rotation_90": True,
            "intensity_jitter": False,
        },
    }
    with pytest.raises(ValueError, match="checkpoint config does not match"):
        validate_checkpoint_metadata(
            checkpoint_metadata(historical_config, epochs_run=20),
            baseline_config(),
        )


def _write_baseline_artifact(
    root: Path,
    *,
    dataset: str = "BBBC039v1",
    release: str = "v1",
    partitions: dict[str, list[str]] | None = None,
    archive_hash: str = "a" * 64,
):
    download = root / "data" / "raw" / "BBBC039" / "download_manifest.json"
    split = root / "data" / "manifests" / "bbbc039_official_split.json"
    download.parent.mkdir(parents=True)
    split.parent.mkdir(parents=True)
    download.write_text(
        json.dumps(
            {
                "dataset": dataset,
                "release": release,
                "authoritative_reference": "https://bbbc.broadinstitute.org/BBBC039",
                "archives": {
                    name: {"sha256": archive_hash}
                    for name in ("images", "masks", "metadata")
                },
            }
        ),
        encoding="utf-8",
    )
    actual_partitions = partitions or {
        "train": [f"train-{index}.png" for index in range(100)],
        "validation": [f"validation-{index}.png" for index in range(50)],
        "test": [f"test-{index}.png" for index in range(50)],
    }
    split_counts = {name: len(members) for name, members in actual_partitions.items()}
    split.write_text(
        json.dumps(
            {
                "dataset": dataset,
                "partitions": actual_partitions,
                "counts": split_counts,
                "validation": {"pairwise_overlap": False},
            }
        ),
        encoding="utf-8",
    )
    verification = root / "data" / "raw" / "BBBC039" / "verification_report.json"
    verification.write_text(
        json.dumps(
            {
                "dataset": dataset,
                "images": 200,
                "masks": 200,
                "image_shape": [520, 696],
                "image_dtype": "uint16",
                "image_channels": 1,
                "image_mask_correspondence_verified": True,
                "target_conversion_verified": True,
                "split_counts_detected": split_counts,
                "expected_split_counts": {"train": 100, "validation": 50, "test": 50},
                "split_counts_verified": split_counts == {"train": 100, "validation": 50, "test": 50},
            }
        ),
        encoding="utf-8",
    )
    config = root / "configs" / "bbbc039_baseline.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "\n".join(
            [
                "dataset:",
                f"  name: {dataset}",
                "  root: data/raw/BBBC039",
                "  split_manifest: data/manifests/bbbc039_official_split.json",
                "seed: 42",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return download, split, config


def test_records_dataset_release_split_and_config_hashes(tmp_path):
    download, split, config = _write_baseline_artifact(tmp_path)
    provenance = build_baseline_artifact_provenance(tmp_path, config)
    assert provenance["dataset"] == "BBBC039v1"
    assert provenance["dataset_release"] == "v1"
    assert provenance["split_counts"] == {"train": 100, "validation": 50, "test": 50}
    assert provenance["download_manifest_sha256"] == hashlib.sha256(download.read_bytes()).hexdigest()
    assert provenance["split_manifest_sha256"] == hashlib.sha256(split.read_bytes()).hexdigest()
    verification = tmp_path / "data" / "raw" / "BBBC039" / "verification_report.json"
    assert provenance["verification_report_sha256"] == hashlib.sha256(verification.read_bytes()).hexdigest()
    assert provenance["baseline_config_sha256"] == hashlib.sha256(config.read_bytes()).hexdigest()
    assert provenance["source_archive_sha256"] == {
        name: "a" * 64 for name in ("images", "masks", "metadata")
    }


def test_rejects_baseline_artifact_with_non_official_split_counts(tmp_path):
    _write_baseline_artifact(
        tmp_path,
        partitions={"train": ["train.png"], "validation": ["validation.png"], "test": ["test.png"]},
    )
    with pytest.raises(ValueError, match="official split counts"):
        build_baseline_artifact_provenance(
            tmp_path,
            tmp_path / "configs" / "bbbc039_baseline.yaml",
        )


def test_rejects_missing_dataset_verification_report(tmp_path):
    _write_baseline_artifact(tmp_path)
    (tmp_path / "data" / "raw" / "BBBC039" / "verification_report.json").unlink()
    with pytest.raises(FileNotFoundError, match="verification_report.json"):
        build_baseline_artifact_provenance(
            tmp_path,
            tmp_path / "configs" / "bbbc039_baseline.yaml",
        )


def test_rejects_dataset_verification_report_with_failed_integrity(tmp_path):
    _write_baseline_artifact(tmp_path)
    report_path = tmp_path / "data" / "raw" / "BBBC039" / "verification_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["image_mask_correspondence_verified"] = False
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="image_mask_correspondence_verified"):
        build_baseline_artifact_provenance(
            tmp_path,
            tmp_path / "configs" / "bbbc039_baseline.yaml",
        )


def test_rejects_baseline_artifact_with_overlapping_split_members(tmp_path):
    _write_baseline_artifact(
        tmp_path,
        partitions={
            "train": ["shared.png"],
            "validation": ["shared.png"],
            "test": ["test.png"],
        },
    )
    with pytest.raises(ValueError, match="overlap"):
        build_baseline_artifact_provenance(
            tmp_path,
            tmp_path / "configs" / "bbbc039_baseline.yaml",
        )


def test_rejects_baseline_artifact_with_wrong_dataset_release(tmp_path):
    _write_baseline_artifact(tmp_path, dataset="BBBC039v2")
    with pytest.raises(ValueError, match="BBBC039v1"):
        build_baseline_artifact_provenance(
            tmp_path,
            tmp_path / "configs" / "bbbc039_baseline.yaml",
        )


def test_rejects_baseline_artifact_with_missing_source_archive_digest(tmp_path):
    download, _, _ = _write_baseline_artifact(tmp_path)
    payload = json.loads(download.read_text(encoding="utf-8"))
    payload["archives"]["images"]["sha256"] = "invalid"
    download.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="archive SHA-256"):
        build_baseline_artifact_provenance(
            tmp_path,
            tmp_path / "configs" / "bbbc039_baseline.yaml",
        )


def test_rejects_baseline_artifact_with_missing_split_partition(tmp_path):
    _write_baseline_artifact(
        tmp_path,
        partitions={"train": ["train.png"], "validation": ["validation.png"]},
    )
    with pytest.raises(ValueError, match="test"):
        build_baseline_artifact_provenance(
            tmp_path,
            tmp_path / "configs" / "bbbc039_baseline.yaml",
        )


def test_rejects_config_that_points_to_a_different_dataset(tmp_path):
    _, _, config = _write_baseline_artifact(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    payload["dataset"]["name"] = "BBBC038"
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="dataset name"):
        build_baseline_artifact_provenance(
            tmp_path,
            config,
        )


def test_rejects_config_that_points_to_a_different_split_manifest(tmp_path):
    _, _, config = _write_baseline_artifact(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    payload["dataset"]["split_manifest"] = "data/manifests/other.json"
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="split manifest path"):
        build_baseline_artifact_provenance(
            tmp_path,
            config,
        )



def test_zero_shot_provenance_records_baseline_dataset_and_split_identity():
    workflow_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "s_biad634_zero_shot.yml"
    )
    workflow = yaml.load(
        workflow_path.read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    provenance = next(
        step for step in workflow["jobs"]["zero-shot"]["steps"]
        if step.get("name") == "Record evaluation provenance"
    )
    assert "build_baseline_artifact_provenance" in provenance["run"]
    assert "baseline_artifact_provenance" in provenance["run"]
    assert "baseline_artifact" in provenance["run"]
    assert "bbbc039_baseline.yaml" in provenance["run"]



def test_zero_shot_workflow_only_accepts_main_baseline_and_records_its_identity():
    workflow_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "s_biad634_zero_shot.yml"
    )
    workflow = yaml.load(
        workflow_path.read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    assert "push" not in workflow["on"]
    assert workflow["on"]["workflow_run"]["branches"] == ["main"]
    job = workflow["jobs"]["zero-shot"]
    condition = job["if"]
    assert "github.ref == 'refs/heads/main'" in condition
    assert "github.event.workflow_run.head_branch == 'main'" in condition
    assert "github.event.workflow_run.head_sha == github.sha" in condition

    steps = job["steps"]
    selection = next(step for step in steps if step.get("name") == "Select baseline run")
    assert "verify_bbbc039_baseline_run.py" in selection["run"]
    assert "head_sha=$GITHUB_SHA" in selection["run"]

    recipe_verification = next(
        step for step in steps
        if step.get("name") == "Verify baseline checkpoint training recipe"
    )
    provenance = next(step for step in steps if step.get("name") == "Record evaluation provenance")
    assert "verify_bbbc039_checkpoint.py" in recipe_verification["run"]
    assert steps.index(recipe_verification) < steps.index(provenance)

    assert "baseline_commit_sha" in provenance["run"]
    assert "baseline_checkpoint_sha256" in provenance["run"]


def test_baseline_workflow_uses_documented_release_training_recipe() -> None:
    root = Path(__file__).resolve().parents[1]
    trainer_path = root / "scripts" / "train_bbbc039.py"
    trainer_source = trainer_path.read_text(encoding="utf-8")
    tree = ast.parse(trainer_source)
    resolver = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_seed"
    )
    namespace: dict[str, object] = {}
    isolated = ast.Module(body=[resolver], type_ignores=[])
    exec(compile(isolated, str(trainer_path), "exec"), namespace)
    resolve_seed = namespace["resolve_seed"]
    assert resolve_seed(42, None) == 42
    assert resolve_seed(42, 7) == 7
    with pytest.raises(ValueError, match="non-negative"):
        resolve_seed(42, -1)

    assert 'parser.add_argument("--seed", type=int, default=None' in trainer_source
    assert 'seed = resolve_seed(int(cfg["seed"]), args.seed)' in trainer_source

    baseline_path = root / ".github" / "workflows" / "bbbc039_baseline.yml"
    baseline = yaml.load(baseline_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    verify_step = next(
        step for step in baseline["jobs"]["train-evaluate"]["steps"]
        if step.get("name") == "Verify dataset and build official manifest"
    )
    assert "--output data/raw/BBBC039/verification_report.json" in verify_step["run"]
    train_step = next(
        step for step in baseline["jobs"]["train-evaluate"]["steps"]
        if step.get("name") == "Train boundary-aware U-Net baseline"
    )
    assert (baseline["on"]["workflow_dispatch"] or {}) == {}
    config = yaml.safe_load((root / "configs" / "bbbc039_baseline.yaml").read_text(encoding="utf-8"))
    assert config["training"]["epochs"] == 100
    assert config["seed"] == 42
    # Keep checkpoint metadata truthful: only declare training options the
    # canonical trainer actually consumes. Geometric augmentation, AMP and
    # early stopping are not implemented and must not be implied by the YAML.
    assert set(config["training"]) == {
        "device",
        "epochs",
        "batch_size",
        "num_workers",
        "learning_rate",
        "weight_decay",
    }
    assert "augmentation" not in config
    # The canonical workflow must use the committed configuration as the
    # single source of truth, not reintroduce a second epoch/seed override.
    assert "env" not in train_step
    assert "--epochs" not in train_step["run"]
    assert "--seed" not in train_step["run"]


def test_baseline_training_is_restricted_to_main() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow_path = root / ".github" / "workflows" / "bbbc039_baseline.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert workflow["jobs"]["train-evaluate"]["if"] == "${{ github.ref == 'refs/heads/main' }}"

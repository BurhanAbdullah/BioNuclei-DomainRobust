from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class _UniqueKeyBaseLoader(yaml.BaseLoader):
    def construct_mapping(self, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"duplicate YAML mapping key: {key!r}")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def test_zero_shot_provenance_binds_target_manifest_and_metrics_after_evaluation():
    workflow = yaml.load(
        (ROOT / ".github/workflows/s_biad634_zero_shot.yml").read_text(encoding="utf-8"),
        Loader=_UniqueKeyBaseLoader,
    )
    steps = workflow["jobs"]["zero-shot"]["steps"]
    names = [step.get("name") for step in steps]
    expected_order = [
        "Download and inventory S-BIAD634",
        "Run zero-shot transfer evaluation",
        "Require complete zero-shot metrics",
        "Bind target dataset and metrics to provenance",
        "Upload zero-shot results",
    ]
    assert [names.index(name) for name in expected_order] == sorted(
        names.index(name) for name in expected_order
    )

    bind = next(step for step in steps if step.get("name") == expected_order[3])
    script = bind["run"]
    for required in (
        "download_manifest.json",
        "archive_sha256",
        "target_manifest_sha256",
        "target_archive_sha256",
        "target_manifest_file_count",
        "metrics_sha256",
        "evaluator_sha256",
        "instance_metrics_sha256",
        "baseline_config_sha256",
        "baseline_checkpoint_verifier_sha256",
        "target_data_used_for_training",
        "n_target_images",
        "instance_iou_threshold",
        "sha256(manifest_path)",
        "sha256(metrics_path)",
    ):
        assert required in script, required

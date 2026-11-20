from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.e5_run_ablation import canonical_acquisition_manifest, verify_variant_evidence


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def test_acquisition_manifest_canonicalization_ignores_download_time(tmp_path: Path) -> None:
    base = {'dataset': 'BBBC039v1', 'archives': {'images': {'sha256': 'abc', 'downloaded_at_utc': '2026-01-01T00:00:00Z'}}}
    first = tmp_path / 'first.json'
    second = tmp_path / 'second.json'
    _write_json(first, base)
    changed = json.loads(json.dumps(base))
    changed['archives']['images']['downloaded_at_utc'] = '2026-01-02T00:00:00Z'
    _write_json(second, changed)
    assert canonical_acquisition_manifest(first) == canonical_acquisition_manifest(second)


def test_variant_evidence_recomputes_hashes_and_rejects_split_mismatch(tmp_path: Path) -> None:
    root = tmp_path / 'outputs' / 'e5'
    name = 'full_frozen_e4'
    variant = root / name
    source_split = {'dataset': 'BBBC039v1', 'partitions': {'train': ['a'], 'test': ['b']}}
    source_download = {'dataset': 'BBBC039v1', 'archives': {'images': {'sha256': 'abc', 'downloaded_at_utc': '2026-01-01'}}}
    target_download = {'dataset': 'S-BIAD634', 'archives': {'images': {'sha256': 'def', 'downloaded_at_utc': '2026-01-01'}}}
    config_path = root / f'{name}.yaml'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('seed: 42\ntraining:\n  epochs: 20\n', encoding='utf-8')
    source_split_path = variant / 'source_split_manifest.json'
    source_download_path = variant / 'source_download_manifest.json'
    target_path = variant / 'target_download_manifest.json'
    checkpoint_path = variant / 'checkpoint' / 'last.pt'
    method_path = variant / 'checkpoint' / 'method_record.json'
    metrics_path = variant / 'evaluation' / 'metrics.json'
    _write_json(source_split_path, source_split)
    _write_json(source_download_path, source_download)
    _write_json(target_path, target_download)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_bytes(b'checkpoint bytes')
    split_sha = hashlib.sha256(source_split_path.read_bytes()).hexdigest()
    source_sha = hashlib.sha256(source_download_path.read_bytes()).hexdigest()
    config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
    method = {'method': 'source_manifest_training', 'training_dataset': 'BBBC039v1', 'source_split_manifest_sha256': split_sha, 'source_download_manifest_sha256': source_sha, 'config_sha256': config_sha, 'initialization': 'random_initialization', 'init_checkpoint': None, 'init_checkpoint_sha256': None}
    _write_json(method_path, method)
    metrics = {'n_images': 79, 'per_image': [{} for _ in range(79)], 'mean': {k: 0 for k in ('dice','iou','precision','recall','f1_score','aji','boundary_f1')}, 'median': {k: 0 for k in ('dice','iou','precision','recall','f1_score','aji','boundary_f1')}}
    _write_json(metrics_path, metrics)
    provenance = {'commit': 'commit123', 'workflow_run_id': 'run456', 'seed': 42, 'epochs': 20, 'target_data_used_for_training': False, 'n_target_images': 79, 'source_split_manifest_sha256': split_sha, 'source_download_manifest_sha256': source_sha, 'target_manifest_sha256': hashlib.sha256(target_path.read_bytes()).hexdigest(), 'config_sha256': config_sha, 'checkpoint_sha256': hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(), 'method_record_sha256': hashlib.sha256(method_path.read_bytes()).hexdigest(), 'metrics_sha256': hashlib.sha256(metrics_path.read_bytes()).hexdigest()}
    _write_json(variant / 'provenance.json', provenance)
    result = verify_variant_evidence(root, name, 'commit123', 'run456')
    assert result[0] == json.dumps(source_split, sort_keys=True, separators=(',', ':'))
    assert result[1] == canonical_acquisition_manifest(source_download_path)
    assert result[2] == canonical_acquisition_manifest(target_path)
    assert result[3] == (42, 20)
    source_split_path.write_text(json.dumps({'dataset': 'BBBC039v1', 'partitions': {'train': ['different']}}), encoding='utf-8')
    with pytest.raises(AssertionError):
        verify_variant_evidence(root, name, 'commit123', 'run456')

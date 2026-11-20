#!/usr/bin/env python3
"""Run one or all preregistered E5 variants.

E5 variants are independently executable so hosted CI can run them in parallel
and avoid a single wall-clock timeout. The scientific definition is unchanged:
full frozen E4 plus the two independently identifiable removals.

Release-integrity guard: fail before training if either source or target
manifest is missing/empty, so provenance cannot be recorded for an accidental
or incomplete dataset inventory.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
import yaml


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def require_manifest(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f'{label} manifest missing: {path}')
    if path.stat().st_size == 0:
        raise RuntimeError(f'{label} manifest is empty: {path}')
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f'{label} manifest is not valid JSON: {path}') from exc
    if not payload:
        raise RuntimeError(f'{label} manifest contains no records: {path}')


def canonical_manifest(path: Path) -> str:
    return json.dumps(json.loads(path.read_text()), sort_keys=True, separators=(',', ':'))


def canonical_acquisition_manifest(path: Path) -> str:
    payload = json.loads(path.read_text())
    for archive in payload.get('archives', {}).values():
        if isinstance(archive, dict):
            archive.pop('downloaded_at_utc', None)
    return json.dumps(payload, sort_keys=True, separators=(',', ':'))


def verify_variant_evidence(root: Path, name: str, expected_commit: str, expected_run_id: str):
    variant = root / name
    provenance_path = variant / 'provenance.json'
    method_record_path = variant / 'checkpoint' / 'method_record.json'
    source_split_path = variant / 'source_split_manifest.json'
    source_download_path = variant / 'source_download_manifest.json'
    target_manifest_path = variant / 'target_download_manifest.json'
    config_path = root / f'{name}.yaml'
    checkpoint_path = variant / 'checkpoint' / 'last.pt'
    metrics_path = variant / 'evaluation' / 'metrics.json'
    provenance = json.loads(provenance_path.read_text())
    method_record = json.loads(method_record_path.read_text())
    source_split = json.loads(source_split_path.read_text())
    source_download = json.loads(source_download_path.read_text())
    target_manifest = json.loads(target_manifest_path.read_text())
    metrics = json.loads(metrics_path.read_text())
    source_split_sha = sha256(source_split_path)
    source_download_sha = sha256(source_download_path)
    target_manifest_sha = sha256(target_manifest_path)
    config_sha = sha256(config_path)
    checkpoint_sha = sha256(checkpoint_path)
    method_record_sha = sha256(method_record_path)
    metrics_sha = sha256(metrics_path)
    assert provenance['commit'] == expected_commit
    assert provenance['workflow_run_id'] == expected_run_id
    assert provenance['seed'] == 42 and provenance['epochs'] == 20
    assert provenance['target_data_used_for_training'] is False
    assert provenance['n_target_images'] == 79
    assert provenance['source_split_manifest_sha256'] == source_split_sha
    assert provenance['source_download_manifest_sha256'] == source_download_sha
    assert provenance['target_manifest_sha256'] == target_manifest_sha
    assert provenance['config_sha256'] == config_sha
    assert provenance['checkpoint_sha256'] == checkpoint_sha
    assert provenance['method_record_sha256'] == method_record_sha
    assert provenance['metrics_sha256'] == metrics_sha
    assert method_record['method'] == 'source_manifest_training'
    assert method_record['training_dataset'] == source_split.get('dataset')
    assert source_download.get('dataset') == source_split.get('dataset')
    assert method_record['source_split_manifest_sha256'] == source_split_sha
    assert method_record['source_download_manifest_sha256'] == source_download_sha
    assert method_record['config_sha256'] == config_sha
    assert method_record['initialization'] == 'random_initialization'
    assert method_record['init_checkpoint'] is None
    assert method_record['init_checkpoint_sha256'] is None
    assert 'adaptation_dataset' not in method_record
    assert 'target_data_used_for_training' not in method_record
    assert metrics['n_images'] == 79 and len(metrics.get('per_image', [])) == 79
    required_metrics = ('dice', 'iou', 'precision', 'recall', 'f1_score', 'aji', 'boundary_f1')
    assert all(k in metrics.get('mean', {}) and k in metrics.get('median', {}) for k in required_metrics)
    return (canonical_manifest(source_split_path), canonical_acquisition_manifest(source_download_path), canonical_acquisition_manifest(target_manifest_path), (provenance['seed'], provenance['epochs']))


def run(cmd):
    print('+', ' '.join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True)


def workflow_identity():
    return {
        'commit': os.environ.get('GITHUB_SHA'),
        'workflow_run_id': os.environ.get('GITHUB_RUN_ID'),
        'ref': os.environ.get('GITHUB_REF'),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--target-manifest', type=Path, required=True)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--target-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--epochs', type=int, default=20)
    p.add_argument('--variant', choices=('full_frozen_e4', 'no_intensity_randomization', 'no_contrast', 'all'), default='all')
    a = p.parse_args()
    require_manifest(a.manifest, 'source split')
    require_manifest(a.target_manifest, 'target')
    source_download_manifest = a.source_root / 'download_manifest.json'
    require_manifest(source_download_manifest, 'source acquisition')
    source_manifest = json.loads(a.manifest.read_text())
    download_manifest = json.loads(source_download_manifest.read_text())
    if source_manifest.get('dataset') != download_manifest.get('dataset'):
        raise RuntimeError('Source split and source acquisition manifests identify different datasets')
    base = yaml.safe_load(a.config.read_text())
    variants = {
        'full_frozen_e4': lambda c: None,
        'no_intensity_randomization': lambda c: c['augmentation'].__setitem__('apply_probability', 0.0),
        'no_contrast': lambda c: c['augmentation'].__setitem__('contrast_probability', 0.0),
    }
    names = list(variants) if a.variant == 'all' else [a.variant]
    a.output.mkdir(parents=True, exist_ok=True)
    for name in names:
        cfg = json.loads(json.dumps(base))
        variants[name](cfg)
        cfg['experiment'] = f'e5_{name}'
        cfg_path = a.output / f'{name}.yaml'
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
        out = a.output / name
        out.mkdir(parents=True, exist_ok=True)
        (out / 'source_download_manifest.json').write_bytes(source_download_manifest.read_bytes())
        (out / 'source_split_manifest.json').write_bytes(a.manifest.read_bytes())
        (out / 'target_download_manifest.json').write_bytes(a.target_manifest.read_bytes())
        train_out = out / 'checkpoint'
        eval_out = out / 'evaluation'
        run([sys.executable, 'scripts/train_domain_robust.py', '--config', str(cfg_path),
             '--manifest', str(a.manifest), '--data-root', str(a.source_root),
             '--source-download-manifest', str(source_download_manifest),
             '--output', str(train_out), '--epochs', str(a.epochs)])
        ckpt = train_out / 'last.pt'
        run([sys.executable, 'scripts/evaluate_s_biad634.py', '--checkpoint', str(ckpt),
             '--data-root', str(a.target_root), '--output', str(eval_out)])
        metrics = json.loads((eval_out / 'metrics.json').read_text())
        if metrics.get('n_images') != 79 or len(metrics.get('per_image', [])) != 79:
            raise RuntimeError(f'{name}: incomplete target evaluation')
        provenance = {
            **workflow_identity(),
            'experiment': f'e5_{name}', 'variant': name, 'seed': int(cfg['seed']),
            'epochs': int(a.epochs), 'source_split_manifest_sha256': sha256(a.manifest),
            'source_download_manifest_sha256': sha256(source_download_manifest),
            'method_record_sha256': sha256(train_out / 'method_record.json'),
            'target_manifest_sha256': sha256(a.target_manifest),
            'config_sha256': sha256(cfg_path), 'checkpoint_sha256': sha256(ckpt),
            'decoder': 'bionuclei.masks.decode_instance_mask',
            'target_data_used_for_training': False, 'n_target_images': 79,
            'evaluator': 'scripts/evaluate_s_biad634.py',
            'metrics_file': str(eval_out / 'metrics.json'),
            'metrics_sha256': sha256(eval_out / 'metrics.json'),
            'metrics_sha256': sha256(eval_out / 'metrics.json'),
        }
        (out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(f'E5 completed variants: {", ".join(names)}')


if __name__ == '__main__':
    main()

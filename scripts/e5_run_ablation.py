#!/usr/bin/env python3
"""Run the preregistered E5 full method and applicable ablations.

The frozen E4 implementation has one combined intensity block
(gain/gamma/bias/noise) and one separately parameterized contrast block.
Therefore E5 evaluates the frozen full method plus the two independently
identifiable removals. No new augmentation component is invented here.

Release-integrity guard: fail before training if either source or target
manifest is missing/empty, so provenance cannot be recorded for an accidental
or incomplete dataset inventory.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
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


def run(cmd):
    print('+', ' '.join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--target-manifest', type=Path, required=True)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--target-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--epochs', type=int, default=20)
    a = p.parse_args()
    require_manifest(a.manifest, 'source split')
    require_manifest(a.target_manifest, 'target')
    base = yaml.safe_load(a.config.read_text())
    variants = {
        'full_frozen_e4': lambda c: None,
        'no_intensity_randomization': lambda c: c['augmentation'].__setitem__('apply_probability', 0.0),
        'no_contrast': lambda c: c['augmentation'].__setitem__('contrast_probability', 0.0),
    }
    a.output.mkdir(parents=True, exist_ok=True)
    for name, mutate in variants.items():
        cfg = json.loads(json.dumps(base))
        mutate(cfg)
        cfg['experiment'] = f'e5_{name}'
        cfg_path = a.output / f'{name}.yaml'
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
        out = a.output / name
        train_out = out / 'checkpoint'
        eval_out = out / 'evaluation'
        run([sys.executable, 'scripts/train_domain_robust.py', '--config', str(cfg_path),
             '--manifest', str(a.manifest), '--data-root', str(a.source_root),
             '--output', str(train_out), '--epochs', str(a.epochs)])
        ckpt = train_out / 'last.pt'
        run([sys.executable, 'scripts/evaluate_s_biad634.py', '--checkpoint', str(ckpt),
             '--data-root', str(a.target_root), '--output', str(eval_out)])
        metrics = json.loads((eval_out / 'metrics.json').read_text())
        if metrics.get('n_images') != 79 or len(metrics.get('per_image', [])) != 79:
            raise RuntimeError(f'{name}: incomplete target evaluation')
        provenance = {
            'experiment': f'e5_{name}', 'variant': name, 'seed': int(cfg['seed']),
            'epochs': int(a.epochs), 'source_split_manifest_sha256': sha256(a.manifest),
            'target_manifest_sha256': sha256(a.target_manifest),
            'config_sha256': sha256(cfg_path), 'checkpoint_sha256': sha256(ckpt),
            'decoder': 'bionuclei.masks.decode_instance_mask',
            'target_data_used_for_training': False, 'n_target_images': 79,
            'evaluator': 'scripts/evaluate_s_biad634.py',
            'metrics_file': str(eval_out / 'metrics.json'),
        }
        (out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print('E5 full frozen method and applicable ablations completed')


if __name__ == '__main__':
    main()

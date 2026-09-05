#!/usr/bin/env python3
"""Run the frozen E6 cross-dataset few-shot protocol on Aitslab-bioimaging1."""
from __future__ import annotations
import argparse, hashlib, json, math, random, subprocess, sys
from pathlib import Path

FRACTIONS=(0.01,0.05,0.10,0.25)

def sha256(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        while True:
            b=f.read(1024*1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',type=Path,required=True); ap.add_argument('--dataset-root',type=Path,required=True); ap.add_argument('--dataset-manifest',type=Path,required=True); ap.add_argument('--init-checkpoint',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--epochs',type=int,default=20); ap.add_argument('--seed',type=int,default=42)
    a=ap.parse_args(); meta=json.loads(a.dataset_manifest.read_text()); parts=meta['partitions']; train=parts['train']; dev=parts['development']; test=parts['test']
    if not train or not dev or not test: raise RuntimeError('E6 BLOCKED: publisher split is incomplete')
    test_ids={r['image_id'] for r in test}; train_ids={r['image_id'] for r in train}
    if train_ids & test_ids: raise RuntimeError('E6 BLOCKED: publisher train/test overlap')
    a.output.mkdir(parents=True,exist_ok=True); results=[]
    rng=random.Random(a.seed); shuffled=list(train); rng.shuffle(shuffled)
    for frac in FRACTIONS:
        n=max(1,math.ceil(len(train)*frac)); selected=shuffled[:n]
        split={'partitions':{'train':[r['image_id'] for r in selected],'validation':[r['image_id'] for r in dev],'test':[r['image_id'] for r in test]},'fraction':frac,'n_adaptation_images':n,'selection_rule':'uniform image-level sample from publisher train split; deterministic seed 42; ceil(fraction*N); no test access'}
        split_path=a.output/f'split_{int(frac*100):02d}pct.json'; split_path.write_text(json.dumps(split,indent=2)+'\n')
        run_dir=a.output/f'{int(frac*100):02d}pct'; ckpt_dir=run_dir/'checkpoint'; eval_dir=run_dir/'evaluation'
        cfg_path=run_dir/'config.yaml'; cfg_path.parent.mkdir(parents=True,exist_ok=True); cfg_path.write_text(a.config.read_text())
        subprocess.run([sys.executable,'scripts/train_domain_robust.py','--config',str(cfg_path),'--manifest',str(split_path),'--data-root',str(a.dataset_root),'--output',str(ckpt_dir),'--epochs',str(a.epochs),'--init-checkpoint',str(a.init_checkpoint)],check=True)
        subprocess.run([sys.executable,'scripts/evaluate_bbbc039.py','--checkpoint',str(ckpt_dir/'last.pt'),'--manifest',str(split_path),'--data-root',str(a.dataset_root),'--split','test','--output',str(eval_dir)],check=True)
        metrics=json.loads((eval_dir/'test_metrics.json').read_text())
        if metrics.get('n_images') != len(test): raise RuntimeError(f'E6 {frac}: incomplete test evaluation')
        provenance={'experiment':'E6_cross_dataset_few_shot','dataset':'Aitslab_bioimaging1','doi':'10.5281/zenodo.6657260','fraction':frac,'n_adaptation_images':n,'n_test_images':len(test),'seed':a.seed,'epochs':a.epochs,'dataset_manifest_sha256':sha256(a.dataset_manifest),'split_manifest_sha256':sha256(split_path),'config_sha256':sha256(cfg_path),'init_checkpoint_sha256':sha256(a.init_checkpoint),'adapted_checkpoint_sha256':sha256(ckpt_dir/'last.pt'),'test_metrics_sha256':sha256(eval_dir/'test_metrics.json'),'s_biad634_used_for_adaptation':False,'test_images_used_for_adaptation':False}
        (run_dir/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n'); results.append({'fraction':frac,'n_adaptation_images':n,'mean':metrics['mean'],'provenance':str(run_dir/'provenance.json')})
    (a.output/'aggregate_results.json').write_text(json.dumps({'protocol':'E6_cross_dataset_few_shot','fractions':results},indent=2)+'\n')
    print(json.dumps(results,indent=2))
if __name__=='__main__': main()

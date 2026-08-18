#!/usr/bin/env python3
"""Zero-shot evaluation of a BBBC039-trained model on S-BIAD634."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np, tifffile, torch
from scipy import ndimage
from skimage.io import imread
from bionuclei.data import decode_instance_mask
from bionuclei.metrics import boundary_f1, dice_coefficient, iou_score
from bionuclei.models import BoundaryUNet
from scripts.metrics_instance import instance_prf


def aji_score(pred, target):
    pred_ids=[x for x in np.unique(pred) if x>0]; true_ids=[x for x in np.unique(target) if x>0]
    if not true_ids and not pred_ids:return 1.0
    if not true_ids or not pred_ids:return 0.0
    used=set(); inter_sum=0.0; union_sum=0.0
    for tid in true_ids:
        t=target==tid; best=(0.0,None)
        for pid in pred_ids:
            if pid in used: continue
            p=pred==pid; inter=np.logical_and(t,p).sum()
            if inter==0: continue
            score=inter/np.logical_or(t,p).sum()
            if score>best[0]:best=(score,pid)
        if best[1] is None: union_sum+=t.sum()
        else:
            pid=int(best[1]); used.add(pid); p=pred==pid
            inter_sum+=np.logical_and(t,p).sum(); union_sum+=np.logical_or(t,p).sum()
    for pid in pred_ids:
        if pid not in used: union_sum+=(pred==pid).sum()
    return float(inter_sum/union_sum) if union_sum else 1.0


def boundary_band(mask):
    fg=mask>0; eroded=ndimage.binary_erosion(fg,structure=np.ones((3,3),dtype=np.uint8)); return fg & ~eroded


def _dataset_dir(root,name):
    candidates=sorted(p for p in root.rglob(name) if p.is_dir())
    if len(candidates)==1:return candidates[0]
    if not candidates:raise RuntimeError(f"Missing required S-BIAD634 directory '{name}' under {root}")
    raise RuntimeError(f"Ambiguous S-BIAD634 directory '{name}': {[str(p) for p in candidates]}")


def discover(root,directory,suffixes):
    d=_dataset_dir(root,directory); return sorted(p for p in d.rglob('*') if p.is_file() and p.suffix.lower() in suffixes)


def pair_files(root):
    images=discover(root,'rawimages',('.tif','.tiff','.png')); masks=discover(root,'groundtruth',('.tif','.tiff','.png'))
    if not images:raise RuntimeError('No S-BIAD634 raw images found')
    stems={p.stem for p in images}; candidates={}
    for mask in masks:
        if mask.stem in stems:candidates.setdefault(mask.stem,[]).append(mask)
    pairs=[]; missing=[]; ambiguous=[]
    for image in images:
        matches=candidates.get(image.stem,[])
        if len(matches)==1:pairs.append((image,matches[0]))
        elif not matches:missing.append(image.stem)
        else:ambiguous.append(image.stem)
    if missing or ambiguous or len(pairs)!=len(images):raise RuntimeError(f'Could not deterministically pair S-BIAD634 files: images={len(images)}, groundtruth_tif_files={len(masks)}, pairs={len(pairs)}, missing={missing[:10]}, ambiguous={ambiguous[:10]}')
    return pairs


def to_model_grayscale(image):
    x=np.asarray(image)
    if x.ndim==2:return x
    if x.ndim==3 and x.shape[-1] in (3,4):
        rgb=x[..., :3].astype(np.float32)
        return (0.299*rgb[...,0]+0.587*rgb[...,1]+0.114*rgb[...,2]).astype(np.float32)
    raise ValueError(f'Unsupported S-BIAD634 image shape: {x.shape}')


def predict_semantic(model,x,tile_size=512,overlap=32):
    if tile_size<=0 or overlap<0 or overlap>=tile_size:raise ValueError('tile_size must be positive and overlap must satisfy 0 <= overlap < tile_size')
    h,w=x.shape; n_classes=3; logits_sum=np.zeros((n_classes,h,w),np.float32); weights=np.zeros((h,w),np.float32); stride=tile_size-overlap
    ys=list(range(0,max(h-tile_size,0)+1,stride)); xs=list(range(0,max(w-tile_size,0)+1,stride))
    if not ys or ys[-1]+tile_size<h:ys.append(max(h-tile_size,0))
    if not xs or xs[-1]+tile_size<w:xs.append(max(w-tile_size,0))
    for y0 in ys:
        for x0 in xs:
            y1,x1=min(y0+tile_size,h),min(x0+tile_size,w); tile=x[y0:y1,x0:x1]; ph,pw=(-tile.shape[0])%8,(-tile.shape[1])%8
            if ph or pw:tile=np.pad(tile,((0,ph),(0,pw)),mode='reflect')
            with torch.inference_mode():tl=model(torch.from_numpy(tile[None,None]).float()).cpu().numpy()[0]
            tl=tl[:,:y1-y0,:x1-x0]; logits_sum[:,y0:y1,x0:x1]+=tl; weights[y0:y1,x0:x1]+=1
    return np.argmax(logits_sum/np.maximum(weights[None],1),axis=0)


def load_mask(path):return decode_instance_mask(np.asarray(imread(path)))


def main():
    p=argparse.ArgumentParser(); p.add_argument('--checkpoint',type=Path,required=True); p.add_argument('--data-root',type=Path,required=True); p.add_argument('--output',type=Path,default=Path('outputs/s_biad634_zero_shot')); p.add_argument('--tile-size',type=int,default=512); p.add_argument('--overlap',type=int,default=32); a=p.parse_args()
    checkpoint=torch.load(a.checkpoint,map_location='cpu'); cfg=checkpoint['config']; model=BoundaryUNet(in_channels=int(cfg['model']['in_channels']),out_channels=int(cfg['model']['out_channels']),base_channels=int(cfg['model']['base_channels'])); model.load_state_dict(checkpoint['model']); model.eval(); results=[]
    for image_path,mask_path in pair_files(a.data_root):
        raw=np.asarray(tifffile.imread(image_path)); image=to_model_grayscale(raw); target=load_mask(mask_path)
        if image.shape!=target.shape:raise ValueError(f'Shape mismatch: {image_path.name}: {image.shape} vs {mask_path.name}: {target.shape}')
        x=image.astype(np.float32); scale=np.percentile(x,99.5); x=np.clip(x/max(float(scale),1.0),0,1); classes=predict_semantic(model,x,a.tile_size,a.overlap); pred,_=ndimage.label(classes!=0,structure=np.ones((3,3),dtype=np.uint8)); pred=pred.astype(np.int32)
        prf=instance_prf(pred,target,iou_threshold=0.5)
        results.append({'image':image_path.name,'dice':dice_coefficient(pred>0,target>0),'iou':iou_score(pred>0,target>0),'precision':prf['precision'],'recall':prf['recall'],'f1_score':prf['f1_score'],'aji':aji_score(pred,target),'boundary_f1':boundary_f1(boundary_band(pred),boundary_band(target)),'height':int(image.shape[0]),'width':int(image.shape[1]),'n_target_instances':int(np.max(target)),'n_pred_instances':int(np.max(pred)),'tp':prf['tp'],'fp':prf['fp'],'fn':prf['fn']})
    metrics=('dice','iou','precision','recall','f1_score','aji','boundary_f1')
    summary={'experiment':'zero_shot_bbbc039_to_s_biad634','n_images':len(results),'mean':{m:float(np.mean([r[m] for r in results])) for m in metrics},'median':{m:float(np.median([r[m] for r in results])) for m in metrics},'per_image':results,'checkpoint_seed':checkpoint.get('seed'),'tile_size':a.tile_size,'overlap':a.overlap,'instance_iou_threshold':0.5}
    a.output.mkdir(parents=True,exist_ok=True); (a.output/'metrics.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary['mean'],indent=2))

if __name__=='__main__':main()

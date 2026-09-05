#!/usr/bin/env python3
"""Train the Boundary U-Net robustness model, optionally fine-tuning a frozen E4 checkpoint."""
from __future__ import annotations
import argparse,json,random
from pathlib import Path
import numpy as np, torch, yaml
from torch.utils.data import DataLoader
from bionuclei.data import InstanceMaskDataset
from bionuclei.losses import BoundaryAwareLoss
from bionuclei.models import BoundaryUNet
from bionuclei.targets import instance_to_boundary_target

def seed_everything(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic=True; torch.backends.cudnn.benchmark=False

def resolve(root,name,kind):
    base=root/('images' if kind=='image' else 'masks'); stem=Path(name).stem
    exts=('.tif','.tiff','.png','.jpg','.jpeg') if kind=='image' else ('.png','.tif','.tiff')
    c=sorted(p for p in base.rglob('*') if p.is_file() and p.suffix.lower() in exts and p.stem==stem)
    if len(c)!=1: raise RuntimeError(f'Expected one {kind} for {name}, found {c}')
    return c[0]

def collate(batch):
    images,masks=zip(*batch)
    return torch.stack(images),torch.stack([torch.from_numpy(instance_to_boundary_target(m.numpy())) for m in masks])

def augment(x,c):
    a=c['augmentation']; y=x.clone()
    if random.random()<a['apply_probability']:
        y=torch.clamp(y*random.uniform(a['gain_min'],a['gain_max']),0,1)
        y=torch.clamp(torch.pow(torch.clamp(y,1e-6,1),random.uniform(a['gamma_min'],a['gamma_max']))+random.uniform(a['bias_min'],a['bias_max']),0,1)
        if a['noise_std']>0: y=torch.clamp(y+torch.randn_like(y)*a['noise_std'],0,1)
    if random.random()<a['contrast_probability']:
        m=y.mean(dim=(-2,-1),keepdim=True); y=torch.clamp((y-m)*random.uniform(a['contrast_min'],a['contrast_max'])+m,0,1)
    return y

def resolve_device(device_config):
    if device_config=='auto': return torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return torch.device(device_config)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--config',type=Path,required=True); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--data-root',type=Path,required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--epochs',type=int,default=None); p.add_argument('--init-checkpoint',type=Path,default=None); a=p.parse_args()
    c=yaml.safe_load(a.config.read_text()); seed_everything(int(c['seed'])); m=json.loads(a.manifest.read_text()); names=m['partitions']['train']
    root=a.data_root; images=[resolve(root,n,'image') for n in names]; masks=[resolve(root,n,'mask') for n in names]
    loader=DataLoader(InstanceMaskDataset(images,masks),batch_size=int(c['training']['batch_size']),shuffle=True,num_workers=int(c['training']['num_workers']),collate_fn=collate)
    device=resolve_device(c['training']['device'])
    model=BoundaryUNet(in_channels=int(c['model']['in_channels']),out_channels=int(c['model']['out_channels']),base_channels=int(c['model']['base_channels'])).to(device)
    if a.init_checkpoint:
        ckpt=torch.load(a.init_checkpoint,map_location='cpu')
        if 'model' not in ckpt: raise RuntimeError('Initial checkpoint does not contain a model state dict')
        model.load_state_dict(ckpt['model'], strict=True)
    loss=BoundaryAwareLoss(boundary_weight=float(c['loss']['boundary_weight']),dice_weight=float(c['loss']['dice_weight'])).to(device)
    opt=torch.optim.AdamW(model.parameters(),lr=float(c['training']['learning_rate']),weight_decay=float(c['training']['weight_decay']))
    a.output.mkdir(parents=True,exist_ok=True); hist=[]
    for ep in range(1,int(a.epochs or c['training']['epochs'])+1):
        model.train(); total=0
        for x,y in loader:
            x,y=augment(x.to(device),c),y.to(device); opt.zero_grad(set_to_none=True); z=model(x); l=loss(z,y); l.backward(); opt.step(); total+=l.item()*x.size(0)
        v=total/len(loader.dataset); hist.append({'epoch':ep,'train_loss':v}); print(f'epoch={ep:03d} train_loss={v:.6f}')
        torch.save({'model':model.state_dict(),'config':c,'seed':int(c['seed']),'epochs_run':ep,'method':'few_shot_external_fluorescence','init_checkpoint':str(a.init_checkpoint) if a.init_checkpoint else None},a.output/'last.pt')
    (a.output/'train_history.json').write_text(json.dumps(hist,indent=2)+'\n')
    (a.output/'method_record.json').write_text(json.dumps({'method':'few_shot_external_fluorescence','target_data_used_for_training':False,'adaptation_dataset':'Aitslab_bioimaging1','seed':int(c['seed']),'init_checkpoint':str(a.init_checkpoint) if a.init_checkpoint else None},indent=2)+'\n')
if __name__=='__main__': main()

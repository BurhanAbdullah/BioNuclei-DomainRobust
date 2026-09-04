#!/usr/bin/env python3
"""Execute the prespecified matched E3/E4 image-level statistical analysis."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from scipy.stats import wilcoxon

METRICS = ["aji", "dice", "iou", "precision", "recall", "f1_score", "boundary_f1"]

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--e3",required=True); p.add_argument("--e4",required=True)
    p.add_argument("--out",required=True); p.add_argument("--seed",type=int,default=42)
    p.add_argument("--bootstrap-resamples",type=int,default=10000)
    a=p.parse_args()
    e3=json.load(open(a.e3)); e4=json.load(open(a.e4))
    A={r["image"]:r for r in e3["per_image"]}; B={r["image"]:r for r in e4["per_image"]}
    ids=sorted(set(A)&set(B)); assert len(ids)==79 and not (set(A)^set(B))
    rng=np.random.default_rng(a.seed); results=[]; pvals=[]
    for m in METRICS:
        x=np.array([A[i][m] for i in ids],float); y=np.array([B[i][m] for i in ids],float); d=y-x
        nz=d!=0; stat=wilcoxon(d,zero_method="wilcox",alternative="two-sided",method="auto") if nz.any() else None
        boots=d[rng.integers(0,len(d),(a.bootstrap_resamples,len(d)))].mean(1)
        results.append({"metric":m,"e3_mean":float(x.mean()),"e3_median":float(np.median(x)),"e4_mean":float(y.mean()),"e4_median":float(np.median(y)),"mean_delta":float(d.mean()),"median_delta":float(np.median(d)),"positive":int((d>0).sum()),"zero":int((d==0).sum()),"negative":int((d<0).sum()),"positive_fraction":float((d>0).mean()),"bootstrap95_mean_delta":[float(v) for v in np.quantile(boots,[.025,.975])],"wilcoxon_p_uncorrected":float(stat.pvalue) if stat else 1.0,"nonzero_pairs":int(nz.sum())})
        pvals.append(float(stat.pvalue) if stat else 1.0)
    order=np.argsort(pvals); adj=[0.0]*len(pvals); running=0.0
    for rank,idx in enumerate(order):
        running=max(running,min(1.0,(len(pvals)-rank)*pvals[idx])); adj[idx]=running
    for r,pv in zip(results,adj): r["wilcoxon_p_holm"]=float(pv)
    d=np.array([B[i]["aji"]-A[i]["aji"] for i in ids]); ratio=np.array([B[i]["n_pred_instances"]/max(B[i]["n_target_instances"],1) for i in ids])
    out={"analysis":"prespecified_matched_e3_e4","status":"executed","seed":a.seed,"bootstrap_resamples":a.bootstrap_resamples,"n_images":len(ids),"image_ids":ids,"primary_endpoint":"aji","secondary_endpoints":["dice","iou","precision","recall","f1_score","boundary_f1"],"results":results,"source_sha256":{"e3_metrics":sha256(a.e3),"e4_metrics":sha256(a.e4)},"failure_analysis":{"highest_aji_loss":[{"image":ids[i],"aji_delta":float(d[i]),"e3_aji":A[ids[i]]["aji"],"e4_aji":B[ids[i]]["aji"]} for i in np.argsort(d)[:10]],"highest_aji_gain":[{"image":ids[i],"aji_delta":float(d[i])} for i in np.argsort(d)[-10:][::-1]],"highest_prediction_target_ratios":[{"image":ids[i],"ratio":float(ratio[i]),"target_instances":A[ids[i]]["n_target_instances"],"predicted_instances_e3":A[ids[i]]["n_pred_instances"],"predicted_instances_e4":B[ids[i]]["n_pred_instances"]} for i in np.argsort(ratio)[-10:][::-1]]}}
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
if __name__=="__main__": main()

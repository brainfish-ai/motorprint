"""Leave-one-dataset-out: how well does the recipe generalise to a human population it never saw?
For each real human dataset D: train on bots + all other human datasets (train-split users), calibrate the
threshold on validation humans from the other datasets (<=0.5% FPR), then score EVERY window of D.
Usage: python3 train/lodo.py   (reads data/features.json and tune/best-config.json) -> train/lodo-report.md"""
import json
import numpy as np
from mlp import *

names, X, y, style, sid, META = load(meta=True)
DS, USER = META['dataset'], META['user']
tr, va, te, held = split(style, sid, group=USER)
cfgp = ROOT / "tune" / "best-config.json"
cfg = json.loads(cfgp.read_text()) if cfgp.exists() else dict(hidden=[16, 8], lr=3e-3, wd=1e-4, noise=0.0)
real = sorted({d for d, s in zip(DS.tolist(), style.tolist()) if s.startswith('real_')})
rows = []
for D in real:
    trm, vam = tr & (DS != D), va & (DS != D)
    mu, sd = standardize_fit(X[trm]); Z = standardize(X, mu, sd)
    r = train(Z[trm], y[trm], Z[vam], y[vam], hidden=tuple(cfg['hidden']), lr=cfg['lr'], wd=cfg['wd'], noise=cfg['noise'], epochs=30, seed=0)
    P = r['last']; p = predict(P, Z)
    thr = float(np.clip(np.quantile(p[vam & (y == 0)], 0.995), 0.3, 0.95))
    dm = DS == D
    bot_te = te & (y == 1)
    rows.append(dict(dataset=D, users=len(set(USER[dm].tolist())), windows=int(dm.sum()), thr=thr,
                     fpr=float((p[dm] >= thr).mean()), fpr05=float((p[dm] >= 0.5).mean()),
                     bot_tpr=float((p[bot_te] >= thr).mean()), heldout_tpr=float((p[held] >= thr).mean())))
    print(rows[-1])
md = ["# Leave-one-dataset-out (human generalisation)", "", f"Config: `{json.dumps(cfg)}`, float32, 30 epochs. Each row: the model never saw any window from that dataset.", "",
      "| held-out human dataset | users | windows | threshold | FPR @ threshold | FPR @ 0.5 | bot test TPR | held-out-style bot TPR |", "|---|---|---|---|---|---|---|---|"]
for r in rows:
    md.append(f"| {r['dataset']} | {r['users']} | {r['windows']} | {r['thr']:.3f} | {r['fpr']*100:.2f}% | {r['fpr05']*100:.2f}% | {r['bot_tpr']*100:.1f}% | {r['heldout_tpr']*100:.1f}% |")
(ROOT / 'train' / 'lodo-report.md').write_text('\n'.join(md) + '\n')
print('\n'.join(md))

"""Lever 3: gradient fine-tuning of dead slots on top of the shipped WSP model, judged leave-one-tool-out.
For each non-replay tool T: fine-tune 3 dead slots (lr 1e-3, 6 epochs) on train humans + DESIGN-half windows of the
OTHER tools; threshold from val humans; detection measured on T's EVAL half. 'all' = trained on every tool's design half
(in-sample tools, held-out sessions). Replays are never trained on. -> tune/r3/loto_ft.json, models in tune/r3/models/"""
import json, sys
import numpy as np
from common import *
from mlp import load as mload, split, train, export
OUT = Path(__file__).parent; (OUT / 'models').mkdir(exist_ok=True)
BASE = shipped(); mu, sd, off = np.array(BASE['mean']), np.array(BASE['std']), BASE['off']
def Zf(X):
    Z = np.clip((X - mu) / sd, -6, 6); Z[:, off] = 0; return Z
names, X, y, style, sid, M = mload(ROOT / 'data' / 'features-real.json', meta=True)
tr, va, te, held = split(style, sid, group=M['user'])
S = load()
P0 = spec_params(BASE)
dead1 = [j for j in range(P0[0][0].shape[0]) if not P0[0][0][j].any() and not P0[1][0][:, j].any()][:3]
dead2 = [k for k in range(P0[1][0].shape[0]) if not P0[1][0][k].any() and P0[2][0][0, k] == 0][:3]
def finetune(tools, seed=1):
    BX = np.concatenate([s['X'] for s in S if s['kind'] == 'bot' and s['half'] == 'design' and s['group'] in tools and len(s['X'])])
    m = [np.zeros_like(W) for W, _ in P0]; rng = np.random.default_rng(0); Pi = [[W.copy(), b.copy()] for W, b in P0]
    for j, k in zip(dead1, dead2):
        m[0][j, :] = 1; m[0][j, off] = 0; m[1][k, j] = 1; m[2][0, k] = 1
        Pi[0][0][j] = rng.normal(0, 0.1, Pi[0][0].shape[1]) * m[0][j]; Pi[1][0][k, j] = 0.5; Pi[2][0][0, k] = 0.5
    r = train(np.vstack([Zf(X[tr]), Zf(BX)]), np.r_[y[tr], np.ones(len(BX))], Zf(X[va]), y[va], hidden=(32, 16), lr=1e-3, wd=0.0, epochs=6, seed=seed, P0=Pi, masks=m)
    P = r['best']
    for li in range(3):
        P[li][0] = np.where(m[li] > 0, P[li][0], Pi[li][0])
        keep = np.ones_like(P[li][1], bool)
        if li == 0: keep[dead1] = False
        if li == 1: keep[dead2] = False
        P[li][1] = np.where(keep, Pi[li][1], P[li][1])
    return export(P, mu, sd, names, bits=8, thr=0.5, off=off)
def evaluate(spec):
    hs = {}
    for s in S:
        if s['kind'] == 'human': hs.setdefault((s['split'], s['group']), []).append(ema_max(logits(spec, s['X'])))
    bs = {t: [ema_max(logits(spec, s['X'])) for s in S if s['kind'] == 'bot' and s['group'] == t and s['half'] == 'eval'] for t in TOOLS}
    return report(bs, hs, calibrate(hs))
NR = [t for t in TOOLS if t not in REPLAYS]
res = json.loads((OUT / 'loto_ft.json').read_text()) if (OUT / 'loto_ft.json').exists() else {}
for T in ['all'] + NR:
    if T in res: continue
    spec = finetune(NR if T == 'all' else [t for t in NR if t != T])
    (OUT / 'models' / f'ft-loto-{T}.json').write_text(json.dumps(spec))
    res[T] = evaluate(spec); (OUT / 'loto_ft.json').write_text(json.dumps(res, indent=1))
    print(T, 'held-out tool det' if T != 'all' else 'score10', res[T]['det'].get(T, res[T]['score10']), 'worst', res[T]['worst'], flush=True)

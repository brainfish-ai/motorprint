"""Gradient baseline for WSP round 2: fine-tune the shipped model on the SAME data the hand-written units were designed
from (training windows + bench DESIGN-half bot windows, replays excluded), then int8. Two variants:
  ft_masked: all surviving weights, pruning mask kept (same size);  ft_slots: only as many dead slots as the units use.
-> tune/wsp/models/benchft-*.json"""
import json, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'train'))
from mlp import load, split, train, export, spec_params
BASE = json.loads(re.search(r'MODEL: ModelSpec = (\{.*\});', (ROOT / 'src' / 'weights.ts').read_text()).group(1))
mu, sd = np.array(BASE['mean']), np.array(BASE['std']); off = BASE['off']
def Zf(X):
    Z = np.clip((X - mu) / sd, -6, 6); Z[:, off] = 0; return Z
names, X, y, style, sid, M = load(ROOT / 'data' / 'features-real.json', meta=True)
tr, va, te, held = split(style, sid, group=M['user'])
S = [json.loads(l) for l in open(ROOT / 'bench' / 'data' / 'windows.jsonl')]
idx = lambda s: int(re.search(r'__(\d+)-', s['id']).group(1))
BX = np.concatenate([np.array(s['X']).reshape(-1, 38) for s in S if s['kind'] == 'bot' and (idx(s) // 4) % 2 == 0 and not s['group'].startswith('replay') and s['X']])
Ztr = np.vstack([Zf(X[tr]), Zf(BX)]); ytr = np.r_[y[tr], np.ones(len(BX))]
Zva, yva = Zf(X[va]), y[va]
P0 = spec_params(BASE)
mask = [(W != 0).astype(float) for W, _ in P0]
n_slots = int(sys.argv[1]) if len(sys.argv) > 1 else 3
for name in ['ft_masked', 'ft_slots']:
    if name == 'ft_masked': m = mask; Pi = P0
    else:
        dead1 = [j for j in range(P0[0][0].shape[0]) if not P0[0][0][j].any() and not P0[1][0][:, j].any()][:n_slots]
        dead2 = [k for k in range(P0[1][0].shape[0]) if not P0[1][0][k].any() and P0[2][0][0, k] == 0][:n_slots]
        m = [np.zeros_like(W) for W, _ in P0]; rng = np.random.default_rng(0); Pi = [[W.copy(), b.copy()] for W, b in P0]
        for j, k in zip(dead1, dead2):
            m[0][j, :] = 1; m[0][j, off] = 0; m[1][k, j] = 1; m[2][0, k] = 1
            Pi[0][0][j] = rng.normal(0, 0.1, Pi[0][0].shape[1]) * m[0][j]; Pi[1][0][k, j] = 0.5; Pi[2][0][0, k] = 0.5
        frozen = [[W.copy(), b.copy()] for W, b in Pi]
    for lr in (3e-4, 1e-3):
        r = train(Ztr, ytr, Zva, yva, hidden=(32, 16), lr=lr, wd=0.0, epochs=6, seed=1, P0=Pi, masks=m)
        P = r['best']
        if name == 'ft_slots':
            for li in range(3):
                P[li][0] = np.where(m[li] > 0, P[li][0], frozen[li][0])
                keep = np.ones_like(P[li][1], bool)
                if li == 0: keep[dead1] = False
                if li == 1: keep[dead2] = False
                P[li][1] = np.where(keep, frozen[li][1], P[li][1])
        spec = export(P, mu, sd, names, bits=8, thr=0.5, off=off)
        (HERE / 'models' / f'benchft-{name}-lr{lr:g}.json').write_text(json.dumps(spec)); print(name, lr, 'val auc', round(r['best_auc'], 5), 'ep', r['best_ep'])

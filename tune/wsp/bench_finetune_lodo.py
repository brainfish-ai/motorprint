"""LODO check for the gradient baseline: apply the ft_slots recipe (3 dead slots, lr 1e-3, 6 epochs, design-half bench
bots, replays excluded) to each leave-one-dataset-out model (trained without dataset d, fine-tuned without d), then score
the held-out dataset's humans with the bench streaming rule. -> tune/wsp/benchft-lodo.json"""
import json, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'train'))
from mlp import load, split, train, spec_params
names, X, y, style, sid, M = load(ROOT / 'data' / 'features-real.json', meta=True)
tr, va, te, held = split(style, sid, group=M['user'])
S = [json.loads(l) for l in open(ROOT / 'bench' / 'data' / 'windows.jsonl')]
idx = lambda s: int(re.search(r'__(\d+)-', s['id']).group(1))
BXraw = np.concatenate([np.array(s['X']).reshape(-1, 38) for s in S if s['kind'] == 'bot' and (idx(s) // 4) % 2 == 0 and not s['group'].startswith('replay') and s['X']])
HUM = [s for s in S if s['kind'] == 'human']
for s in HUM: s['X'] = np.array(s['X'], float).reshape(-1, 38)
def ema(p):
    l = np.log(np.maximum(1e-6, p) / np.maximum(1e-6, 1 - p)); o = []; v0 = None
    for v in l: v0 = v if v0 is None else v0 + 0.35 * (v - v0); o.append(v0)
    return 1 / (1 + np.exp(-np.array(o)))
def fwd(P, Z):
    h = Z
    for li, (W, b) in enumerate(P):
        h = h @ W.T + b
        if li < len(P) - 1: h = np.maximum(h, 0)
    return 1 / (1 + np.exp(-np.clip(h[:, 0], -30, 30)))
out = {}
for d in sorted({s['group'] for s in HUM}):
    base = json.loads((ROOT / 'bench' / 'data' / 'lodo-models' / f'{d}.json').read_text())
    mu, sd, off = np.array(base['mean']), np.array(base['std']), base.get('off', [])
    def Zf(A):
        Z = np.clip((A - mu) / sd, -6, 6); Z[:, off] = 0; return Z
    trm, vam = tr & (M['dataset'] != d), va & (M['dataset'] != d)
    P0 = spec_params(base)
    dead1 = [j for j in range(P0[0][0].shape[0]) if not P0[0][0][j].any() and not P0[1][0][:, j].any()][:3]
    dead2 = [k for k in range(P0[1][0].shape[0]) if not P0[1][0][k].any() and P0[2][0][0, k] == 0][:3]
    m = [np.zeros_like(W) for W, _ in P0]; rng = np.random.default_rng(0); Pi = [[W.copy(), b.copy()] for W, b in P0]
    for j, k in zip(dead1, dead2):
        m[0][j, :] = 1; m[0][j, off] = 0; m[1][k, j] = 1; m[2][0, k] = 1
        Pi[0][0][j] = rng.normal(0, 0.1, Pi[0][0].shape[1]) * m[0][j]; Pi[1][0][k, j] = 0.5; Pi[2][0][0, k] = 0.5
    r = train(np.vstack([Zf(X[trm]), Zf(BXraw)]), np.r_[y[trm], np.ones(len(BXraw))], Zf(X[vam]), y[vam], hidden=(32, 16), lr=1e-3, wd=0.0, epochs=6, seed=1, P0=Pi, masks=m)
    P = r['best']
    for li in range(3):   # only the slots train (as in ft_slots); no int8 here, so this slightly favours the fine-tune
        P[li][0] = np.where(m[li] > 0, P[li][0], Pi[li][0])
        keep = np.ones_like(P[li][1], bool)
        if li == 0: keep[dead1] = False
        if li == 1: keep[dead2] = False
        P[li][1] = np.where(keep, Pi[li][1], P[li][1])
    ss = [s for s in HUM if s['group'] == d and len(s['X'])]
    sm0 = np.array([ema(fwd(P0, Zf(s['X']))).max() for s in ss]); sm = np.array([ema(fwd(P, Zf(s['X']))).max() for s in ss])
    nseg = len([s for s in HUM if s['group'] == d])
    out[d] = dict(base_session_fpr=float((sm0 >= .5).sum() / nseg), ft_session_fpr=float((sm >= .5).sum() / nseg),
                  ft_session_fpr_at_0798=float((sm >= .798).sum() / nseg), dead_slots=len(dead1))
    print(d, out[d], flush=True)
(HERE / 'benchft-lodo.json').write_text(json.dumps(out, indent=1))

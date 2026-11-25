"""Shared loading for the weight-space-programming experiment (tune/wsp)."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'train'))
from mlp import load, split, spec_params, metrics, auc  # noqa

BASE_SPEC = Path(__file__).resolve().parent / 'base-4_quant.json'   # shipped real-data model (int8, 38-32-16-1)


def data(features=ROOT / 'data' / 'features-real.json'):
    names, X, y, style, sid, M = load(features, meta=True)
    tr, va, te, held = split(style, sid, group=M['user'])
    # held-out bot styles are split by session into a DESIGN half (may be looked at / used to program or
    # fine-tune) and an EVAL half (only for reporting). Same rng for every method.
    rng = np.random.default_rng(42)
    sess = sorted(set(sid[held].tolist())); r = {s: rng.random() for s in sess}
    u = np.array([r.get(s, 1.0) for s in sid])
    held_design = held & (u < 0.5); held_eval = held & (u >= 0.5)
    return dict(names=names, X=X, y=y, style=style, sid=sid, user=M['user'], dataset=M['dataset'], off=M['off'],
                tr=tr, va=va, te=te, held=held, held_design=held_design, held_eval=held_eval)


def standardize(spec, X):
    Z = np.clip((X - np.array(spec['mean'])) / np.array(spec['std']), -6, 6)
    for i in spec.get('off', []): Z[:, i] = 0
    return Z


def acts(P, Z):
    """All layer activations (post-ReLU for hidden layers, logit for the last)."""
    h = Z; out = []
    for li, (W, b) in enumerate(P):
        h = h @ W.T + b
        if li < len(P) - 1: h = np.maximum(h, 0)
        out.append(h)
    return out


def score(P, Z):
    return 1 / (1 + np.exp(-np.clip(acts(P, Z)[-1][:, 0], -30, 30)))


def report(P, D, Z, thr=0.5, tag=''):
    p = score(P, Z); y, st = D['y'], D['style']
    te, held_eval = D['te'], D['held_eval']
    real_te = te & (y == 0) & np.char.startswith(st.astype(str), 'real_')
    out = dict(tag=tag, test_auc=auc(y[te], p[te]), test_acc=metrics(y[te], p[te], thr)['acc'],
               real_fpr=float((p[real_te] >= thr).mean()), real_n=int(real_te.sum()),
               heldout_eval_auc=auc(np.r_[y[held_eval], y[real_te]], np.r_[p[held_eval], p[real_te]]))
    for s in ['ghost', 'wind', 'agent']:
        m = held_eval & (st == s); out[f'catch_{s}'] = float((p[m] >= thr).mean())
    for ds in sorted(set(D['dataset'][real_te].tolist())):
        m = real_te & (D['dataset'] == ds); out[f'fpr_{ds}'] = float((p[m] >= thr).mean())
    rp = st == 'replay'; out['catch_replay'] = float((p[rp] >= thr).mean())
    return out

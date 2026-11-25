"""Tiny numpy MLP: training, evaluation, pruning, quantization, export. No dependencies beyond numpy."""
import json, base64, gzip, hashlib, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TRAIN_STYLES = ['teleport', 'linear', 'eased', 'bezier', 'dom']
HELDOUT_STYLES = ['ghost', 'wind', 'agent']


def load(path=ROOT / 'data' / 'features.json'):
    d = json.loads(Path(path).read_text())
    X = np.array(d['X'], dtype=np.float64)
    y = np.array(d['y'], dtype=np.float64)
    style = np.array(d['style']); sid = np.array(d['sid'])
    return d['names'], X, y, style, sid


def split(style, sid, seed=0):
    """Session-level split. Held-out bot styles never touch train/val."""
    rng = np.random.default_rng(seed)
    uniq = sorted(set(sid.tolist()))
    r = {s: rng.random() for s in uniq}
    u = np.array([r[s] for s in sid])
    held = np.isin(style, HELDOUT_STYLES)
    other = ~held & ~np.char.startswith(style.astype(str), 'replay')  # real_* sessions join train/val/test
    tr = other & (u < 0.70)
    va = other & (u >= 0.70) & (u < 0.85)
    te = other & (u >= 0.85)
    return tr, va, te, held


def auc(y, p):
    y = np.asarray(y); p = np.asarray(p)
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg): return float('nan')
    order = np.argsort(np.concatenate([pos, neg]), kind='mergesort')
    ranks = np.empty(len(order)); ranks[order] = np.arange(1, len(order) + 1)
    allp = np.concatenate([pos, neg])
    # average ties
    _, inv, cnt = np.unique(allp, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks); ranks = (sums / cnt)[inv]
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def metrics(y, p, thr=0.5):
    yh = (p >= thr).astype(int); y = y.astype(int)
    tp = int(((yh == 1) & (y == 1)).sum()); tn = int(((yh == 0) & (y == 0)).sum())
    fp = int(((yh == 1) & (y == 0)).sum()); fn = int(((yh == 0) & (y == 1)).sum())
    return dict(acc=(tp + tn) / max(1, len(y)), auc=auc(y, p), tp=tp, tn=tn, fp=fp, fn=fn,
                tpr=tp / max(1, tp + fn), fpr=fp / max(1, fp + tn))


# ---------------- model ----------------
def init(sizes, rng):
    P = []
    for a, b in zip(sizes[:-1], sizes[1:]):
        P.append([rng.normal(0, np.sqrt(2 / a), (b, a)), np.zeros(b)])
    return P


def forward(P, Z, masks=None):
    h = Z; acts = [h]
    for li, (W, b) in enumerate(P):
        h = h @ W.T + b
        if li < len(P) - 1: h = np.maximum(h, 0)
        acts.append(h)
    return acts


def predict(P, Z):
    return 1 / (1 + np.exp(-np.clip(forward(P, Z)[-1][:, 0], -30, 30)))


def standardize_fit(X):
    mu = X.mean(0); sd = X.std(0); sd[sd < 1e-6] = 1.0
    return mu, sd


def standardize(X, mu, sd):
    return np.clip((X - mu) / sd, -6, 6)


def train(Ztr, ytr, Zva, yva, hidden=(16, 8), lr=3e-3, wd=1e-4, epochs=40, batch=256, seed=0,
          pos_weight=None, P0=None, masks=None, noise=0.0, snapshots=False, log=None):
    rng = np.random.default_rng(seed)
    sizes = [Ztr.shape[1], *hidden, 1]
    P = [[W.copy(), b.copy()] for W, b in P0] if P0 is not None else init(sizes, rng)
    if pos_weight is None: pos_weight = (ytr == 0).sum() / max(1, (ytr == 1).sum())
    m = [[np.zeros_like(W), np.zeros_like(b)] for W, b in P]; v = [[np.zeros_like(W), np.zeros_like(b)] for W, b in P]
    t = 0; best = (-1, None, -1); snaps = []
    for ep in range(epochs):
        idx = rng.permutation(len(Ztr))
        lr_ep = lr * 0.5 * (1 + np.cos(np.pi * ep / epochs))  # cosine schedule
        for s in range(0, len(idx), batch):
            bi = idx[s:s + batch]; Z = Ztr[bi]; Y = ytr[bi]
            if noise: Z = Z + rng.normal(0, noise, Z.shape)
            acts = forward(P, Z)
            p = 1 / (1 + np.exp(-np.clip(acts[-1][:, 0], -30, 30)))
            wgt = np.where(Y == 1, pos_weight, 1.0)
            g = ((p - Y) * wgt / wgt.sum())[:, None]
            t += 1
            for li in range(len(P) - 1, -1, -1):
                W, b = P[li]
                gW = g.T @ acts[li] + wd * W; gb = g.sum(0)
                if li > 0: g = (g @ W) * (acts[li] > 0)
                for k, gr in ((0, gW), (1, gb)):
                    m[li][k] = 0.9 * m[li][k] + 0.1 * gr; v[li][k] = 0.999 * v[li][k] + 0.001 * gr * gr
                    P[li][k] = P[li][k] - lr_ep * (m[li][k] / (1 - 0.9 ** t)) / (np.sqrt(v[li][k] / (1 - 0.999 ** t)) + 1e-8)
                if masks is not None: P[li][0] = P[li][0] * masks[li]
        a = auc(yva, predict(P, Zva))
        if snapshots and ep >= epochs // 2: snaps.append([[W.copy(), b.copy()] for W, b in P])
        if a > best[0]: best = (a, [[W.copy(), b.copy()] for W, b in P], ep)
        if log: log(ep, a)
    return dict(last=P, best=best[1], best_auc=best[0], best_ep=best[2], snaps=snaps)


def average(models):
    return [[np.mean([mm[li][0] for mm in models], 0), np.mean([mm[li][1] for mm in models], 0)] for li in range(len(models[0]))]


def prune(P, frac):
    """Global magnitude pruning over all weight matrices (biases kept)."""
    if frac <= 0: return [[W.copy(), b.copy()] for W, b in P], [np.ones_like(W) for W, _ in P]
    allw = np.concatenate([np.abs(W).ravel() for W, _ in P])
    thr = np.quantile(allw, frac)
    masks = [(np.abs(W) > thr).astype(float) for W, _ in P]
    return [[W * mk, b.copy()] for (W, b), mk in zip(P, masks)], masks


def quantize(P, bits):
    """Symmetric per-output-row quantization. Returns dequantized params and the integer codes/scales."""
    if bits == 32: return [[W.copy(), b.copy()] for W, b in P], None
    qmax = 127 if bits == 8 else 7
    out, codes = [], []
    for W, b in P:
        s = np.abs(W).max(1) / qmax; s[s == 0] = 1.0
        q = np.clip(np.round(W / s[:, None]), -qmax, qmax).astype(np.int8)
        out.append([q * s[:, None], b.copy()]); codes.append((q, s))
    return out, codes


def export(P, mu, sd, names, bits=32, thr=0.5):
    layers = []
    _, codes = quantize(P, bits)
    for li, (W, b) in enumerate(P):
        o, i = W.shape
        if bits == 32:
            raw = W.astype('<f4').tobytes(); s = None
        else:
            q, s = codes[li]
            if bits == 8: raw = q.astype(np.int8).tobytes()
            else:
                flat = (q.ravel().astype(np.int16) & 15).astype(np.uint8)
                if len(flat) % 2: flat = np.append(flat, 0)
                raw = (flat[0::2] | (flat[1::2] << 4)).astype(np.uint8).tobytes()
            s = [float(f'{x:.6g}') for x in s]
        L = dict(i=int(i), o=int(o), bits=bits, w=base64.b64encode(raw).decode(), b=[float(f'{x:.6g}') for x in b])
        if s is not None: L['s'] = s
        layers.append(L)
    return dict(v=1, names=list(names), mean=[float(f'{x:.6g}') for x in mu], std=[float(f'{x:.6g}') for x in sd], layers=layers, thr=thr)


def spec_gz_bytes(spec):
    return len(gzip.compress(json.dumps(spec, separators=(',', ':')).encode(), 9))


def nparams(P):
    return int(sum(W.size + b.size for W, b in P)), int(sum((W != 0).sum() + b.size for W, b in P))


def evaluate(P, Z, y, style, sid, masks_d, thr=0.5):
    """Window-level metrics on test + held-out styles, per-style detection rates, session-level accuracy."""
    p = predict(P, Z)
    tr, va, te, held = masks_d
    out = dict(test=metrics(y[te], p[te], thr))
    # held-out styles evaluated against the human test windows (so AUC is defined)
    hum_te = te & (y == 0)
    ho = held | hum_te
    out['heldout'] = metrics(y[ho], p[ho], thr)
    out['per_style'] = {}
    for s in sorted(set(style[te | held].tolist())):
        mk = (te | held) & (style == s)
        out['per_style'][s] = dict(n=int(mk.sum()), flagged=float((p[mk] >= thr).mean()), mean_score=float(p[mk].mean()))
    # session level: mean window score per session
    def sess(mask):
        ids = sorted(set(sid[mask].tolist()))
        ps = np.array([p[mask & (sid == i)].mean() for i in ids]); ys = np.array([y[mask & (sid == i)][0] for i in ids])
        return metrics(ys, ps, thr)
    rp = style == 'replay'
    if rp.any():
        out['attack_replay'] = dict(n=int(rp.sum()), flagged=float((p[rp] >= thr).mean()), mean_score=float(p[rp].mean()))
    out['session_test'] = sess(te)
    out['session_heldout'] = sess(ho)
    return out


def write_weights_ts(spec, path=ROOT / 'src' / 'weights.ts', note=''):
    body = json.dumps(spec, separators=(',', ':'))
    Path(path).write_text(
        "// Generated by train/train.py or tune/tune.py. Do not edit by hand.\n"
        f"// {note}\n"
        "import type { ModelSpec } from './model';\n"
        f"export const MODEL: ModelSpec = {body};\n")

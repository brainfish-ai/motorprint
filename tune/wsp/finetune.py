"""(3b) Gradient baselines on the SAME failure examples (DESIGN half of the ghost sessions), starting
from the shipped weights, then int8 per-row quantisation like the shipped model.
  ft_masked: Adam on all surviving weights (pruning mask kept, so same sparsity and size).
  ft_slot:   Adam on only the two dead slots the hand-programmed unit uses (same parameter budget).
Training data = train users/sessions + ghost design windows; model picked by validation AUC."""
import json
import numpy as np
from common import *
from mlp import train, export

spec = json.loads(BASE_SPEC.read_text()); P0 = spec_params(spec); names = spec['names']
mu, sd = np.array(spec['mean']), np.array(spec['std'])
D = data(); Z = standardize(spec, D['X']); y = D['y']
trm = D['tr'] | D['held_design']
Ztr, ytr, Zva, yva = Z[trm], y[trm], Z[D['va']], y[D['va']]
out = Path(__file__).parent / 'models'
mask = [(W != 0).astype(float) for W, _ in P0]
for name, P_init, m in [('ft_masked', P0, mask), ('ft_slot', None, None)]:
    if name == 'ft_slot':
        # small random init in the slots; mask = only the slot entries can be non-zero/learn
        rng = np.random.default_rng(0); P_init = [[W.copy(), b.copy()] for W, b in P0]
        m = [np.zeros_like(W) for W, _ in P0]
        m[0][1, :] = 1; m[0][1, spec['off']] = 0; m[1][0, 1] = 1; m[2][0, 0] = 1
        P_init[0][0][1] = rng.normal(0, 0.1, P_init[0][0].shape[1]) * m[0][1]; P_init[1][0][0, 1] = 0.5; P_init[2][0][0, 0] = 0.5
        # the frozen weights must stay put: wrap masks so only slot entries change
        frozen = [[W.copy(), b.copy()] for W, b in P_init]
    for lr in [3e-4, 1e-3]:
        r = train(Ztr, ytr, Zva, yva, hidden=(32, 16), lr=lr, wd=0.0, epochs=8, seed=1, P0=P_init, masks=m)
        P = r['best'] if r['best'] is not None else r['last']
        if name == 'ft_slot':  # restore frozen weights/biases outside the slots (masks only cover weights)
            for li in range(3):
                P[li][0] = np.where(m[li] > 0, P[li][0], frozen[li][0])
                keep = np.ones_like(P[li][1], bool)
                if li == 0: keep[1] = False
                if li == 1: keep[0] = False
                P[li][1] = np.where(keep, frozen[li][1], P[li][1])
        s = export(P, mu, sd, names, bits=8, thr=spec['thr'], off=spec.get('off'))
        (out / f'{name}_lr{lr:g}.json').write_text(json.dumps(s))
        print(name, lr, 'val auc', round(r['best_auc'], 5), 'ep', r['best_ep'])

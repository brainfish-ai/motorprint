"""Hand-written units in raw feature space, and a writer that installs them into any ModelSpec.
A unit = {'name', 'w': {feature: raw weight}, 'b': raw bias, 'gain', 'out'}:
    h = relu(gain * (sum_f w_f * x_f + b));  logit += out * h      (out < 0 = a human-side 'suppressor')
Units go into dead slots (no inputs and no outputs) when the model has them, else the layers grow by one unit.
Because units are written in raw feature units, the SAME unit can be installed into any model trained on the same
features (e.g. the leave-one-dataset-out models), which is how LODO FPR is checked for each unit."""
import numpy as np, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'train'))
from mlp import spec_params, export


def install(spec, units):
    P = [[W.copy(), b.copy()] for W, b in spec_params(spec)]
    names = spec['names']; mu = np.array(spec['mean']); sd = np.array(spec['std'])
    s_out = spec['layers'][2].get('s', [None])[0]
    for u in units:
        W1, b1 = P[0]; W2, b2 = P[1]; W3, b3 = P[2]
        dead1 = [j for j in range(W1.shape[0]) if not W1[j].any() and not W2[:, j].any()]
        dead2 = [k for k in range(W2.shape[0]) if not W2[k].any() and W3[0, k] == 0]
        if dead1: j = dead1[0]
        else:
            P[0] = [np.vstack([W1, np.zeros((1, W1.shape[1]))]), np.r_[b1, 0.0]]; P[1][0] = np.hstack([W2, np.zeros((W2.shape[0], 1))]); j = P[0][0].shape[0] - 1
        W2 = P[1][0]
        if dead2: k = dead2[0]
        else:
            P[1] = [np.vstack([W2, np.zeros((1, W2.shape[1]))]), np.r_[P[1][1], 0.0]]; P[2][0] = np.hstack([P[2][0], np.zeros((1, 1))]); k = P[1][0].shape[0] - 1
        w = np.zeros(len(names)); b = u['b']
        for f, v in u['w'].items():
            i = names.index(f); w[i] = v * sd[i]; b += v * mu[i]
        P[0][0][j] = u['gain'] * w; P[0][1][j] = u['gain'] * b
        o = u['out']; relay = 1.0
        if s_out:
            # keep the output row's int8 grid AND its scale: if |out| exceeds the row's largest code, the excess moves into
            # the unit's own layer-2 relay row (which has its own scale), so no other weight is re-quantised
            cap = 127 * s_out
            if abs(o) > cap: relay = abs(o) / cap; o = float(np.sign(o) * cap)
            o = float(np.round(o / s_out) * s_out)
        P[1][0][k, :] = 0; P[1][0][k, j] = relay; P[1][1][k] = 0.0
        P[2][0][0, k] = o
    bits = spec['layers'][0].get('bits', 8)
    return export(P, mu, sd, names, bits=bits, thr=spec.get('thr', 0.5), off=spec.get('off'))


def n_params(units):
    return sum(len(u['w']) + 1 + 1 + 1 + 1 for u in units)   # weights + h1 bias + relay + h2 bias + output

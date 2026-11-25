"""(2) Weight-space programming: hand-write one feature-detector unit into the shipped int8 model.
No gradient descent. The unit is written in raw-feature units, converted to z-space by hand, and
placed in slots that global pruning left dead (h1_1 has no inputs/outputs, h2_0 has no inputs and
output weight 0), so the architecture (38-32-16-1), int8 format and byte budget are unchanged.

Unit G ("unclocked, never-collinear, busy cursor"), from the probes in probes.md:
  real cursors arrive on a display/USB clock (a dominant inter-event dt -> high dt_mode_share) and
  in integer pixels (many exactly-collinear steps -> high turn_zero_frac). ghost-cursor style bots
  emit events off-clock with sub-pixel noise on every point, and move continuously with almost no
  pauses and evenly spread turning (high turn_entropy). G fires only when ALL of these hold and the
  window has plenty of moves (gate on n_moves, which is 0 for windows without a mouse).

  G = relu( 3 * [ (0.15 - turn_zero_frac)/0.15 + (0.20 - dt_mode_share)/0.20
                + (turn_entropy - 0.55)/0.15 + (0.10 - pause_frac)/0.10
                + 1.0 * (n_moves - 3.0) - 3.0 ] )
  h2_0 = relu(1.0 * G);  logit += 1.0 * h2_0
Design used only train/val users and the DESIGN half of held-out ghost sessions (see common.py).
"""
import json, copy
import numpy as np
from common import *
from mlp import export, spec_gz_bytes

RAW = {'turn_zero_frac': -1 / 0.15, 'dt_mode_share': -1 / 0.20, 'turn_entropy': 1 / 0.15, 'pause_frac': -1 / 0.10, 'n_moves': 1.0}
RAW_B = 0.15 / 0.15 + 0.20 / 0.20 - 0.55 / 0.15 + 0.10 / 0.10 - 3.0 - 3.0
GAIN, W_RELAY, W_OUT = 3.0, 1.0, 1.0
H1_SLOT, H2_SLOT = 1, 0


def program(spec):
    P = spec_params(spec); names = spec['names']; mu = np.array(spec['mean']); sd = np.array(spec['std'])
    assert not P[0][0][H1_SLOT].any() and not P[1][0][:, H1_SLOT].any(), 'h1 slot not dead'
    assert not P[1][0][H2_SLOT].any() and P[2][0][0, H2_SLOT] == 0, 'h2 slot not dead'
    Q = [[W.copy(), b.copy()] for W, b in P]
    w = np.zeros(len(names)); b = RAW_B
    for n, v in RAW.items():
        i = names.index(n); w[i] = v * sd[i]; b += v * mu[i]  # x = z*sd + mu
    Q[0][0][H1_SLOT] = GAIN * w; Q[0][1][H1_SLOT] = GAIN * b
    Q[1][0][H2_SLOT, H1_SLOT] = W_RELAY; Q[1][1][H2_SLOT] = 0.0
    # output row: snap the new weight onto the row's existing int8 grid so no other code changes
    s_out = spec['layers'][2]['s'][0]; Q[2][0][0, H2_SLOT] = np.round(W_OUT / s_out) * s_out
    new = export(Q, mu, sd, names, bits=8, thr=spec['thr'], off=spec.get('off'))
    return P, Q, new


def changed(spec_a, spec_b):
    A, B = spec_params(spec_a), spec_params(spec_b)
    ch = sum(int((np.abs(Wa - Wb) > 1e-9).sum() + (np.abs(ba - bb) > 1e-9).sum()) for (Wa, ba), (Wb, bb) in zip(A, B))
    nz = sum(int((W != 0).sum() + len(b)) for W, b in A)
    tot = sum(W.size + len(b) for W, b in A)
    return ch, nz, tot


if __name__ == '__main__':
    spec = json.loads(BASE_SPEC.read_text())
    P, Q, new = program(spec)
    out = Path(__file__).parent / 'models' / 'wsp.json'; out.write_text(json.dumps(new))
    ch, nz, tot = changed(spec, new)
    print(f'wrote {out}: changed {ch} params ({ch / nz:.1%} of {nz} non-zero+bias, {ch / tot:.2%} of {tot} total); '
          f'gz {spec_gz_bytes(spec)} -> {spec_gz_bytes(new)} B')

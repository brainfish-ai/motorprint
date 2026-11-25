"""(1) Dump the shipped int8 weights with feature names -> tune/wsp/weights-dump.md"""
import json
import numpy as np
from common import *

spec = json.loads(BASE_SPEC.read_text()); P = spec_params(spec); names = spec['names']; off = set(spec.get('off', []))
L1, L2, L3 = P
lines = ['# motorprint shipped model: raw weights', '', f"38 inputs (standardised features, z-scores; `off` = {[names[i] for i in off]}), 32 ReLU -> 16 ReLU -> 1 logit. int8 per-row, dequantised below.", '']
lines += ['## Layer 1 (feature -> h1_j). Nonzero incoming weights, largest first', '']
alive1 = []
for j in range(L1[0].shape[0]):
    w = L1[0][j]; nz = [(names[i], w[i]) for i in np.argsort(-np.abs(w)) if w[i] != 0 and i not in off]
    out_use = np.abs(L2[0][:, j]).sum()
    if not nz or out_use == 0: lines.append(f'- h1_{j}: dead (in={len(nz)} nonzero, out-use={out_use:.2f})'); continue
    alive1.append(j)
    lines.append(f"- **h1_{j}** b={L1[1][j]:+.2f} | " + ', '.join(f'{n} {v:+.2f}' for n, v in nz) + f' | feeds h2 with |w|sum={out_use:.2f}')
lines += ['', '## Layer 2 (h1 -> h2_k)', '']
for k in range(L2[0].shape[0]):
    w = L2[0][k]; nz = [(f'h1_{j}', w[j]) for j in np.argsort(-np.abs(w)) if w[j] != 0]
    lines.append(f"- **h2_{k}** b={L2[1][k]:+.2f} out={L3[0][0][k]:+.2f} | " + ', '.join(f'{n} {v:+.2f}' for n, v in nz))
lines += ['', f'## Output: b={L3[1][0]:+.2f}', '']
(Path(__file__).parent / 'weights-dump.md').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))

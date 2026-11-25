"""(1b) Activation probes: check each interpretation claim on real vs bot windows -> tune/wsp/probes.md
Uses train+val users and the DESIGN half of the held-out bot styles only (test users and the EVAL half stay untouched)."""
import json
import numpy as np
from common import *

spec = json.loads(BASE_SPEC.read_text()); P = spec_params(spec); names = spec['names']
D = data(); Z = standardize(spec, D['X']); A1, A2, A3 = acts(P, Z); p = 1 / (1 + np.exp(-A3[:, 0]))
y, st, ds = D['y'], D['style'], D['dataset']
look = (D['tr'] | D['va']) | D['held_design']
alive1 = [j for j in range(P[0][0].shape[0]) if np.abs(P[1][0][:, j]).sum() > 0.1 and np.abs(P[0][0][j]).sum() > 0]
alive2 = [k for k in range(P[1][0].shape[0]) if P[2][0][0, k] != 0]
groups = {}
for d_ in ['adserp', 'boun', 'dux', 'mousetask', 'keyrecs', 'cmu']: groups[f'human:{d_}'] = look & (ds == d_)
for s in ['teleport', 'linear', 'eased', 'bezier', 'dom']: groups[f'bot:{s}'] = look & (st == s)
gh = look & (st == 'ghost')
groups['ghost:caught'] = gh & (p >= 0.5); groups['ghost:missed'] = gh & (p < 0.5)
groups['wind'] = look & (st == 'wind'); groups['agent'] = look & (st == 'agent')
L = ['# Activation probes', '', 'Mean activation (fraction of windows where the ReLU is on) per group. Groups: train+val users of each human dataset, train/val sessions of each bot style, and the DESIGN half of held-out styles.', '']
hdr = '| unit | ' + ' | '.join(groups) + ' |'
L += ['## Layer 1', '', hdr, '|' + '---|' * (len(groups) + 1)]
for j in alive1:
    L.append(f'| h1_{j} | ' + ' | '.join(f"{A1[m, j].mean():.2f} ({(A1[m, j] > 0).mean():.0%})" for m in groups.values()) + ' |')
L += ['', '## Layer 2 (out weight in brackets)', '', hdr, '|' + '---|' * (len(groups) + 1)]
for k in alive2:
    L.append(f'| h2_{k} [{P[2][0][0, k]:+.2f}] | ' + ' | '.join(f"{A2[m, k].mean():.2f}" for m in groups.values()) + ' |')
L += ['', '| score | ' + ' | '.join(f"{p[m].mean():.2f}" for m in groups.values()) + ' |', '| n | ' + ' | '.join(str(int(m.sum())) for m in groups.values()) + ' |']
# feature correlations per unit (all looked-at windows where the unit's inputs vary)
L += ['', '## Strongest feature correlations per layer-1 unit (Pearson, looked-at windows)', '']
Zl = Z[look]
for j in alive1:
    a = A1[look, j]
    cs = []
    for i, n in enumerate(names):
        if Zl[:, i].std() < 1e-9 or a.std() < 1e-9: continue
        cs.append((n, float(np.corrcoef(Zl[:, i], a)[0, 1])))
    cs.sort(key=lambda t: -abs(t[1]))
    L.append(f'- h1_{j}: ' + ', '.join(f'{n} {c:+.2f}' for n, c in cs[:6]))
# failure analysis: missed ghost vs real humans vs caught ghost (z-scores, design half only)
L += ['', '## Failure analysis: missed ghost windows vs real humans (mean z-score, design half)', '', '| feature | real humans (train+val) | ghost missed | ghost caught | separation (missed vs human, in human SDs) |', '|---|---|---|---|---|']
hum = look & (y == 0)
rows = []
for i, n in enumerate(names):
    if i in spec.get('off', []): continue
    hm, hs = Z[hum, i].mean(), Z[hum, i].std() + 1e-9
    gm = Z[groups['ghost:missed'], i].mean(); gc = Z[groups['ghost:caught'], i].mean()
    rows.append((abs(gm - hm) / hs, n, hm, gm, gc))
for sep, n, hm, gm, gc in sorted(rows, reverse=True)[:14]:
    L.append(f'| {n} | {hm:+.2f} | {gm:+.2f} | {gc:+.2f} | {sep:.2f} |')
# false-positive cluster among real humans (val users)
fp = D['va'] & (y == 0) & (p >= 0.5); tn = D['va'] & (y == 0) & (p < 0.5)
L += ['', f'## Real-human false positives (validation users): {int(fp.sum())} of {int((D["va"] & (y == 0)).sum())} windows', '',
      'By dataset: ' + ', '.join(f"{d_} {int((fp & (ds == d_)).sum())}" for d_ in sorted(set(ds[fp].tolist()))), '',
      '| feature | FP windows | other val humans | bots (train) |', '|---|---|---|---|']
bots = D['tr'] & (y == 1)
rows = []
for i, n in enumerate(names):
    if i in spec.get('off', []): continue
    rows.append((abs(Z[fp, i].mean() - Z[tn, i].mean()), n, Z[fp, i].mean(), Z[tn, i].mean(), Z[bots, i].mean()))
for _, n, a, b, c in sorted(rows, reverse=True)[:12]:
    L.append(f'| {n} | {a:+.2f} | {b:+.2f} | {c:+.2f} |')
(Path(__file__).parent / 'probes.md').write_text('\n'.join(L) + '\n')
print('\n'.join(L))

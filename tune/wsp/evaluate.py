"""(3) Before/after table on data nobody looked at: test users (real-human FPR) and the EVAL half of
held-out bot sessions. Writes tune/wsp/RESULTS.md and results.json."""
import json
import numpy as np
from common import *
from mlp import spec_gz_bytes
from program import changed

D = data(); base = json.loads(BASE_SPEC.read_text())
models = {'shipped (4_quant)': base}
for f in sorted((Path(__file__).parent / 'models').glob('*.json')): models[f.stem] = json.loads(f.read_text())
rows = []
for k, s in models.items():
    r = report(spec_params(s), D, standardize(s, D['X']), thr=s['thr'], tag=k)
    ch, nz, tot = changed(base, s); r.update(changed=ch, changed_pct=ch / nz, gz=spec_gz_bytes(s)); rows.append(r)
cols = ['test_auc', 'real_fpr', 'heldout_eval_auc', 'catch_ghost', 'catch_wind', 'catch_agent', 'catch_replay', 'changed', 'changed_pct', 'gz']
L = ['# WSP results (threshold = shipped 0.5)', '', f'Real-human FPR on {rows[0]["real_n"]} test-user windows; catch rates on the EVAL half of held-out bot sessions (never used for design or fine-tuning).', '',
     '| model | ' + ' | '.join(cols) + ' |', '|---|' + '---|' * len(cols)]
for r in rows:
    L.append(f"| {r['tag']} | " + ' | '.join(f'{r[c]:.4f}' if isinstance(r[c], float) and c not in ('changed_pct',) else (f'{r[c]:.1%}' if c == 'changed_pct' else str(r[c])) for c in cols) + ' |')
L += ['', 'Per-dataset real-human FPR (test users):', '']
dss = sorted(k[4:] for k in rows[0] if k.startswith('fpr_'))
L += ['| model | ' + ' | '.join(dss) + ' |', '|---|' + '---|' * len(dss)]
for r in rows: L.append(f"| {r['tag']} | " + ' | '.join(f"{r['fpr_' + d]:.4f}" for d in dss) + ' |')
# matched-FPR view: pick each model's threshold on VALIDATION real users so its val FPR equals the shipped
# model's val FPR, then report test FPR and eval-half catch rates at that threshold (fair to gradient fine-tunes,
# whose calibration moves).
y, st = D['y'], D['style']
val_h = D['va'] & (y == 0)
pb = score(spec_params(base), standardize(base, D['X'])); fpr_v = float((pb[val_h] >= base['thr']).mean())
L += ['', f'Matched-FPR view: threshold re-picked on validation users so val real FPR = {fpr_v:.4f} (shipped value), then scored on test users / eval half:', '',
      '| model | thr | real_fpr (test) | ghost | wind | agent | replay | heldout_eval_auc |', '|---|---|---|---|---|---|---|---|']
for k, s_ in models.items():
    Zs = standardize(s_, D['X']); p = score(spec_params(s_), Zs)
    t = float(np.quantile(p[val_h], 1 - fpr_v)) if fpr_v > 0 else float(p[val_h].max())
    t = max(t, 1e-6)
    r = report(spec_params(s_), D, Zs, thr=t, tag=k)
    for rr in rows:
        if rr['tag'] == k: rr['matched'] = dict(thr=t, **{c: r[c] for c in ['real_fpr', 'catch_ghost', 'catch_wind', 'catch_agent', 'catch_replay']})
    L.append(f"| {k} | {t:.3f} | {r['real_fpr']:.4f} | {r['catch_ghost']:.4f} | {r['catch_wind']:.4f} | {r['catch_agent']:.4f} | {r['catch_replay']:.4f} | {r['heldout_eval_auc']:.4f} |")
here = Path(__file__).parent
(here / 'RESULTS.md').write_text('\n'.join(L) + '\n'); (here / 'results.json').write_text(json.dumps(rows, indent=1))
print('\n'.join(L))

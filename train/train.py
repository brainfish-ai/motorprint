"""Baseline: train one float32 MLP with default hyperparameters and export it.
Usage: python3 train/train.py [--out src/weights.ts]"""
import json, sys
import numpy as np
from mlp import *

names, X, y, style, sid, META = load(meta=True)
tr, va, te, held = split(style, sid, group=META['user'])
mu, sd = standardize_fit(X[tr]); Z = standardize(X, mu, sd)
r = train(Z[tr], y[tr], Z[va], y[va], hidden=(16, 8), lr=3e-3, wd=1e-4, epochs=30, seed=0)
P = r['last']
ev = evaluate(P, Z, y, style, sid, (tr, va, te, held), dataset=META['dataset'])
spec = export(P, mu, sd, names, bits=32, off=META['off'])
ev['params'] = nparams(P); ev['model_gz_bytes'] = spec_gz_bytes(spec)
ev['counts'] = dict(train=int(tr.sum()), val=int(va.sum()), test=int(te.sum()), heldout=int(held.sum()))
print(json.dumps(ev, indent=1))
(ROOT / 'train' / 'baseline-report.json').write_text(json.dumps(ev, indent=1))
(ROOT / 'train' / 'baseline-model.json').write_text(json.dumps(spec))
if '--write' in sys.argv:
    write_weights_ts(spec, note='baseline float32 MLP 16-8')

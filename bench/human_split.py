"""Freeze the official human splits used by the benchmark -> bench/human_split.json.
Leave-users-out: the exact train/val/test users of the shipped model (train/mlp.py split, seed 0).
Leave-one-dataset-out: each dataset in turn, all of its users (scored by a recipe model trained without it)."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'train'))
from mlp import load, split
names, X, y, style, sid, M = load(ROOT / 'data' / 'features-real.json', meta=True)
tr, va, te, held = split(style, sid, group=M['user'])
out = {}
for k, m in [('train', tr), ('val', va), ('test', te)]:
    hm = m & (y == 0)
    out[k] = sorted(set(M['user'][hm].tolist()))
out['datasets'] = sorted(set(M['dataset'][y == 0].tolist()))
(Path(__file__).parent / 'human_split.json').write_text(json.dumps(out, indent=0))
print({k: len(v) for k, v in out.items()})

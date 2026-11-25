"""Lever 2: session-level aggregation of the shipped model's window logits. Thresholds from val humans only;
scored on eval-half bots and test humans. -> tune/r3/aggregate.md"""
import numpy as np, json
from common import *
S = load(); spec = shipped()
for s in S: s['l'] = logits(spec, s['X'])
def cusum(l, c, h_unused=None):
    g = 0.0; m = -30.0
    for v in l: g = max(0.0, g + v - c); m = max(m, g)
    return m if len(l) else -30.0
AGG = {
  'EMA max a=0.35 (shipped rule)': lambda l: ema_max(l, 0.35),
  'EMA max a=0.2': lambda l: ema_max(l, 0.2),
  'EMA max a=0.6': lambda l: ema_max(l, 0.6),
  'max window': lambda l: float(l.max()) if len(l) else -30,
  'mean logit': lambda l: float(l.mean()) if len(l) else -30,
  'top-2 mean': lambda l: float(np.sort(l)[-2:].mean()) if len(l) else -30,
  'CUSUM c=-2': lambda l: cusum(l, -2.0), 'CUSUM c=0': lambda l: cusum(l, 0.0), 'CUSUM c=2': lambda l: cusum(l, 2.0),
}
L = ['# Lever 2: session aggregation (shipped model, eval-half bots, test humans; thr from val humans)', '', HDR]
out = {}
for name, f in AGG.items():
    hs = {}
    for s in S:
        if s['kind'] == 'human': hs.setdefault((s['split'], s['group']), []).append(f(s['l']))
    bs = {t: [f(s['l']) for s in S if s['kind'] == 'bot' and s['group'] == t and s['half'] == 'eval'] for t in TOOLS}
    r = report(bs, hs, calibrate(hs)); out[name] = r; L.append(fmt_row(name, r)); print(L[-1], flush=True)
(Path(__file__).parent / 'aggregate.md').write_text('\n'.join(L) + '\n'); (Path(__file__).parent / 'aggregate.json').write_text(json.dumps(out, indent=1))

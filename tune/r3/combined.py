"""Round-3 headline: motion model (+ optional fine-tune) OR provenance rules, on held-out sessions.
Threshold for the model part is calibrated on VALIDATION humans with the rules included (worst val dataset <= 0.5%).
Bots: eval half only. 'LOTO' rows score each tool with the fine-tune that never saw that tool.
Datasets: A = bench/data/windows.jsonl (300/tool recordings, motion recorder), B = windows2.jsonl (80/tool, + probe).
-> tune/r3/combined.md / combined.json"""
import json, sys
import numpy as np
from common import *
FL = json.loads((Path(__file__).parent / 'flags.json').read_text())
SA = load()
HUM = [s for s in SA if s['kind'] == 'human']
B_PATH = ROOT / 'bench' / 'data' / 'windows2.jsonl'
SB = [s for s in load(B_PATH) if s['kind'] == 'bot'] if B_PATH.exists() else []
BOTS = {'A': [s for s in SA if s['kind'] == 'bot' and s['half'] == 'eval'], 'B': [s for s in SB if s['half'] == 'eval']}
MODELS = {'wsp2': shipped(), 'ft_all': json.loads((Path(__file__).parent / 'models' / 'ft-loto-all.json').read_text())}
LOTO = {t: json.loads((Path(__file__).parent / 'models' / f'ft-loto-{t}.json').read_text()) for t in TOOLS if (Path(__file__).parent / 'models' / f'ft-loto-{t}.json').exists()}
cache = {}
def smax(spec_name, s):
    key = (spec_name, s['id'])
    if key not in cache:
        spec = MODELS[spec_name] if spec_name in MODELS else LOTO[spec_name]
        cache[key] = ema_max(logits(spec, s['X']))
    return cache[key]
def flags(s, src):
    if s['kind'] == 'human': f = dict(FL['humans'].get(s['id'], {}))
    else: f = dict(FL['bots1' if src == 'A' else 'bots2'].get(s['id'], {}))
    f['U'] = int(np.any(np.array(s['untr']) > 0)) if len(s['untr']) else 0
    return f
def run(name, src, model, rules, loto=False):
    BIG = 1e9
    def score(s, spec_name):
        f = flags(s, src); r = any(f.get(k, 0) for k in rules)
        m = smax(spec_name, s) if spec_name else -BIG
        return BIG if r else m
    def hum_scores(mdl):
        hs = {}
        for s in HUM: hs.setdefault((s['split'], s['group']), []).append(score(s, mdl))
        return hs
    hs = hum_scores(model); thr = calibrate(hs)
    bs = {t: [score(s, model) for s in BOTS[src] if s['group'] == t] for t in TOOLS}
    bs = {t: v for t, v in bs.items() if v}
    r = report(bs, hs, thr, tools=[t for t in TOOLS if t in bs]); r['n'] = {t: len(v) for t, v in bs.items()}
    if loto:   # each held-out tool is scored by the fine-tune that never saw it, at THAT model's own val-calibrated threshold
        worst = r['worst']; r['loto_thr'] = {}
        for t in bs:
            if t not in LOTO: continue
            hs_t = hum_scores(t); thr_t = calibrate(hs_t); r_t = report({t: [score(s, t) for s in BOTS[src] if s['group'] == t]}, hs_t, thr_t, tools=[t])
            r['det'][t] = r_t['det'][t]; worst = max(worst, r_t['worst']); r['loto_thr'][t] = thr_t
        r['worst'] = worst; ok = worst <= 0.01; tl = list(r['det'])
        r['raw10'] = float(np.mean([r['det'][t] for t in tl])); r['raw8'] = float(np.mean([r['det'][t] for t in tl if t not in REPLAYS]))
        r['score10'] = r['raw10'] if ok else 0.0; r['score8'] = r['raw8'] if ok else 0.0
    # pooled WINDOW fpr of the model part at thr (window logits >= thr) for the 'must not rise' check
    if model:
        w = np.concatenate([logits(MODELS.get(model, LOTO.get(model)), s['X']) for s in HUM if s['split'] == 'test' and len(s['X'])])
        r['pooled_window_fpr_model'] = float((w >= thr).mean())
    return r
ROWS = [
  ('A: WSP-2 model only', 'A', 'wsp2', [], False),
  ('A: WSP-2 + isTrusted', 'A', 'wsp2', ['U'], False),
  ('A: WSP-2 + F1 teleport-instant-click', 'A', 'wsp2', ['F1'], False),
  ('A: WSP-2 + F1 + isTrusted', 'A', 'wsp2', ['F1', 'U'], False),
  ('A: FT(all tools, in-sample tools) + F1 + isTrusted', 'A', 'ft_all', ['F1', 'U'], False),
  ('A: FT leave-tool-out + F1 + isTrusted', 'A', 'ft_all', ['F1', 'U'], True),
  ('A: rules only (F1 + isTrusted)', 'A', None, ['F1', 'U'], False),
]
if SB:
    ROWS += [
      ('B: WSP-2 model only', 'B', 'wsp2', [], False),
      ('B: WSP-2 + F1 + isTrusted', 'B', 'wsp2', ['F1', 'U'], False),
      ('B: WSP-2 + F1 + isTrusted + F2 pressure0', 'B', 'wsp2', ['F1', 'U', 'F2'], False),
      ('B: WSP-2 + F1 + isTrusted + F2 + F3 keyless insert', 'B', 'wsp2', ['F1', 'U', 'F2', 'F3'], False),
      ('B: FT leave-tool-out + F1 + isTrusted + F2 + F3', 'B', 'ft_all', ['F1', 'U', 'F2', 'F3'], True),
      ('B: FT(all) + F1 + isTrusted + F2 + F3', 'B', 'ft_all', ['F1', 'U', 'F2', 'F3'], False),
      ('B: rules only (F1, isTrusted, F2, F3)', 'B', None, ['F1', 'U', 'F2', 'F3'], False),
    ]
res = {}; L = ['# Round 3: model + provenance rules (eval-half bots, test humans; model threshold calibrated on val humans with the rules included)', '', HDR]
for name, *a in ROWS:
    r = run(name, *a); res[name] = r; L.append(fmt_row(name, r)); print(L[-1], 'win-FPR', r.get('pooled_window_fpr_model'), flush=True)
(Path(__file__).parent / 'combined.md').write_text('\n'.join(L) + '\n'); (Path(__file__).parent / 'combined.json').write_text(json.dumps(res, indent=1))

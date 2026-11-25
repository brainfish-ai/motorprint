"""WSP round 2, step 1: which features separate the bench bots the model MISSES from humans?
Uses only the DESIGN half of bench bot sessions (even plan index) and train+val human users. -> tune/wsp/bench-probes.md"""
import json, re, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'train'))
from mlp import spec_params
SPEC = json.loads(re.search(r'MODEL: ModelSpec = (\{.*\});', (ROOT / 'src' / 'weights.ts').read_text()).group(1))
names = SPEC['names']; off = set(SPEC['off'])


def prob(spec, X):
    Z = np.clip((X - np.array(spec['mean'])) / np.array(spec['std']), -6, 6)
    for i in spec.get('off', []): Z[:, i] = 0
    h = Z; P = spec_params(spec)
    for li, (W, b) in enumerate(P):
        h = h @ W.T + b
        if li < len(P) - 1: h = np.maximum(h, 0)
    return 1 / (1 + np.exp(-h[:, 0]))


S = [json.loads(l) for l in open(ROOT / 'bench' / 'data' / 'windows.jsonl')]
idx = lambda s: int(re.search(r'__(\d+)-', s['id']).group(1))
H = np.concatenate([np.array(s['X']).reshape(-1, 38) for s in S if s['kind'] == 'human' and s['split'] in ('train', 'val') and s['X']])
L = ['# Bench failure probes (design half only)', '', f'Humans: {len(H)} windows from train+val users. Quantiles are [10%, 50%, 90%] of raw feature values. "sep" = |median(missed) - median(human)| / human IQR.', '']
for tool in ['botasaurus-human', 'playwright-mcp', 'undetected-chromedriver', 'ghost-cursor', 'nodriver', 'playwright-stealth', 'puppeteer-stealth', 'pyautogui']:
    ss = [s for s in S if s['kind'] == 'bot' and s['group'] == tool and (idx(s) // 4) % 2 == 0 and s['X']]
    if not ss: continue
    X = np.concatenate([np.array(s['X']).reshape(-1, 38) for s in ss]); p = prob(SPEC, X); miss = X[p < 0.5]
    L += [f'## {tool}: {len(ss)} design sessions, {len(X)} windows, {100 * (p >= 0.5).mean():.0f}% windows caught', '']
    if len(miss) < 5: continue
    L += ['| feature | humans | missed bot windows | sep |', '|---|---|---|---|']
    rows = []
    for i, n in enumerate(names):
        if i in off: continue
        hq = np.percentile(H[:, i], [10, 25, 50, 75, 90]); mq = np.percentile(miss[:, i], [10, 50, 90])
        iqr = max(hq[3] - hq[1], 1e-3 * (abs(hq[2]) + 1)); rows.append((abs(mq[1] - hq[2]) / iqr, n, hq[[0, 2, 4]], mq))
    for sep, n, hq, mq in sorted(rows, key=lambda r: -r[0])[:10]:
        L.append(f'| {n} | {np.round(hq, 3).tolist()} | {np.round(mq, 3).tolist()} | {sep:.1f} |')
    L.append('')
(Path(__file__).parent / 'bench-probes.md').write_text('\n'.join(L) + '\n')
print('\n'.join(L))

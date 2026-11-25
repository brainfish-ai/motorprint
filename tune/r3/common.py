"""Round-3 helpers: load bench windows, score a spec per window, honest calibration and bench score.
Calibration: the threshold is picked on VALIDATION humans (worst dataset <= 0.5% session FPR, half the 1% budget);
test humans, eval-half bots and leave-one-tool-out runs are never used to pick anything."""
import json, re, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'train'))
from mlp import spec_params
TOOLS = ['ghost-cursor', 'puppeteer-stealth', 'playwright-stealth', 'undetected-chromedriver', 'nodriver', 'botasaurus-human', 'pyautogui', 'playwright-mcp', 'replay-cdp', 'replay-xdotool']
REPLAYS = ['replay-cdp', 'replay-xdotool']
idx = lambda s: int(re.search(r'__(\d+)-', s['id']).group(1))
half = lambda s: 'design' if (idx(s) // 4) % 2 == 0 else 'eval'


def shipped():
    return json.loads(re.search(r'MODEL: ModelSpec = (\{.*\});', (ROOT / 'src' / 'weights.ts').read_text()).group(1))


def load(path=ROOT / 'bench' / 'data' / 'windows.jsonl'):
    S = [json.loads(l) for l in open(path)]
    for s in S:
        s['X'] = np.array(s['X'], dtype=float).reshape(-1, 38)
        if s['kind'] == 'bot': s['half'] = half(s)
    return S


def logits(spec, X):
    if len(X) == 0: return np.zeros(0)
    Z = np.clip((X - np.array(spec['mean'])) / np.array(spec['std']), -6, 6)
    for i in spec.get('off', []): Z[:, i] = 0
    h = Z; P = spec_params(spec)
    for li, (W, b) in enumerate(P):
        h = h @ W.T + b
        if li < len(P) - 1: h = np.maximum(h, 0)
    return np.clip(h[:, 0], -30, 30)


def ema_max(l, alpha=0.35):
    if len(l) == 0: return -30.0
    s = l[0]; m = s
    for v in l[1:]: s = s + alpha * (v - s); m = max(m, s)
    return float(m)


def calibrate(hum_scores, budget=0.005):
    """hum_scores: {(split, dataset): array of session scores}. Lowest threshold whose worst VAL dataset FPR <= budget."""
    val = [np.asarray(v) for (sp, d), v in hum_scores.items() if sp == 'val']
    u = np.unique(np.concatenate(val)); cands = np.r_[(u[:-1] + u[1:]) / 2, u[-1] + 1e-6]   # midpoints of the gaps
    for t in cands:
        if max((v >= t).mean() for v in val if len(v)) <= budget: return float(t)
    return float('inf')


def report(bot_scores, hum_scores, thr, tools=TOOLS):
    """bot_scores: {tool: array of session scores}; returns per-tool det, score10, score8, test FPR worst/pooled."""
    det = {t: float((np.asarray(bot_scores[t]) >= thr).mean()) for t in tools if t in bot_scores}
    test = {d: float((np.asarray(v) >= thr).mean()) for (sp, d), v in hum_scores.items() if sp == 'test'}
    pooled = float(np.mean(np.concatenate([np.asarray(v) >= thr for (sp, d), v in hum_scores.items() if sp == 'test'])))
    worst = max(test.values())
    s10 = float(np.mean([det[t] for t in tools if t in det])); s8 = float(np.mean([det[t] for t in tools if t in det and t not in REPLAYS]))
    ok = worst <= 0.01
    return dict(det=det, test_fpr=test, worst=worst, pooled=pooled, thr=thr, score10=s10 if ok else 0.0, score8=s8 if ok else 0.0, raw10=s10, raw8=s8)


def fmt_row(name, r, tools=TOOLS):
    return f"| {name} | " + ' | '.join(f"{100 * r['det'].get(t, float('nan')):.1f}" for t in tools) + f" | {100 * r['worst']:.2f}% | {100 * r['pooled']:.2f}% | {r['thr']:.3g} | **{100 * r['score10']:.1f}** | **{100 * r['score8']:.1f}** |"


HDR = '| detector | ghost | pptr-st | pw-st | uc | nodriver | botasaurus | pyautogui | MCP | replay-CDP | replay-xdo | worst test FPR | pooled test FPR | thr | score (10 tools) | score (no replays) |\n|---|' + '---|' * 15

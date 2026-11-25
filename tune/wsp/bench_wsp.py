"""WSP round 2 (benchmark-guided). Hand-written units are DESIGNED here on the bench DESIGN half (even plan index)
and train+val human users only; acceptance is decided by bench/score.py on the EVAL half + test users + LODO.
Usage: python3 tune/wsp/bench_wsp.py design            # quick design-half table for every candidate set
       python3 tune/wsp/bench_wsp.py build <name>      # write tune/wsp/models/bench-<name>.json + units file"""
import json, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'train')); sys.path.insert(0, str(HERE))
from mlp import spec_params
from units import install, n_params
BASE = json.loads(re.search(r'MODEL: ModelSpec = (\{.*\});', (ROOT / 'src' / 'weights.ts').read_text()).group(1))

# ---- candidate units (raw feature units; see bench-probes.md for the numbers they come from) ----
U = {
  # --- vetoed before testing for acceptance: they key on events our human data cannot produce ---
  # human `input` events are synthesised from key presses by the converters, so input_no_key_frac is always 0 for humans
  'keyless_typing': dict(name='keyless_typing', w={'input_no_key_frac': 1.0}, b=-0.08, gain=60.0, out=1.6),
  # --- candidates on events humans DO produce in the data ---
  # B: botasaurus' humanised cursor peaks its speed at the very start of every move (peak_pos ~0.005 vs ~0.4 for
  #    people) on a steady event clock (dt_cv ~0.17 vs ~0.6). Humans: mouse in 4 datasets, 0.6M+ moves.
  'early_peak_metronome': dict(name='early_peak_metronome', w={'peak_pos': -1 / 0.03, 'dt_cv': -1 / 0.3, 'n_moves': 1.0}, b=1.0 + 1.0 - 2.5 - 1.0, gain=2.0, out=1.6),
  # G: real ghost-cursor moves on a near-perfect clock (dt_cv ~0.10, dt_mode_share ~0.55), long continuous paths, no pauses
  'clocked_glide': dict(name='clocked_glide', w={'dt_cv': -1 / 0.15, 'dt_mode_share': 1 / 0.15, 'n_moves': 1.0, 'pause_frac': -1 / 0.02}, b=1.0 - 0.45 / 0.15 - 3.0 + 1.0 - 1.0, gain=2.0, out=1.6),
  # W: pyautogui.scroll(-k) sends k wheel notches in one burst (<4 ms apart). Humans who scroll (AdSERP 16k windows,
  #    DUX 0.9k) essentially never do. dt_sub4_frac saturates at 0.091 raw (z clip), so the threshold is 0.05.
  'wheel_burst': dict(name='wheel_burst', w={'dt_sub4_frac': 1 / 0.04, 'has_scroll': 3.0}, b=-0.05 / 0.04 - 3.0, gain=3.0, out=1.6),
  # R (LODO): a scroll-only reading window (no pointer, keys or clicks) is human-side evidence
  'scroll_reader': dict(name='scroll_reader', w={'has_scroll': 1.0, 'has_mouse': -1.0, 'has_keys': -1.0, 'has_click': -1.0}, b=-0.5, gain=6.0, out=-1.6),
}
for _sl in (2.0, 3.0, 4.0):
    U[f'G{_sl:g}'] = dict(U['clocked_glide'], name=f'clocked_glide_slack{_sl:g}', b=1.0 - 0.45 / 0.15 - 3.0 + 1.0 - _sl)
SETS = {'base': [], 'K(vetoed)': ['keyless_typing'], 'B': ['early_peak_metronome'], 'G': ['clocked_glide'], 'W': ['wheel_burst'], 'R': ['scroll_reader'],
        'BG': ['early_peak_metronome', 'clocked_glide'], 'BGW': ['early_peak_metronome', 'clocked_glide', 'wheel_burst'],
        'BGWR': ['early_peak_metronome', 'clocked_glide', 'wheel_burst', 'scroll_reader'],
        'BW': ['early_peak_metronome', 'wheel_burst'], 'BWR': ['early_peak_metronome', 'wheel_burst', 'scroll_reader'],
        'BWG2': ['early_peak_metronome', 'wheel_burst', 'G2'], 'BWG3': ['early_peak_metronome', 'wheel_burst', 'G3'], 'BWG4': ['early_peak_metronome', 'wheel_burst', 'G4']}
if len(sys.argv) > 2: SETS = {k: SETS[k] for k in sys.argv[2].split(',')}


def prob(spec, X):
    Z = np.clip((X - np.array(spec['mean'])) / np.array(spec['std']), -6, 6)
    for i in spec.get('off', []): Z[:, i] = 0
    h = Z; P = spec_params(spec)
    for li, (W, b) in enumerate(P):
        h = h @ W.T + b
        if li < len(P) - 1: h = np.maximum(h, 0)
    return 1 / (1 + np.exp(-np.clip(h[:, 0], -30, 30)))


def ema_max(p):
    if not len(p): return 0.0
    l = np.log(np.maximum(1e-6, p) / np.maximum(1e-6, 1 - p)); s = l[0]; m = s
    for v in l[1:]: s = s + 0.35 * (v - s); m = max(m, s)
    return float(1 / (1 + np.exp(-m)))


def design():
    S = [json.loads(l) for l in open(ROOT / 'bench' / 'data' / 'windows.jsonl')]
    idx = lambda s: int(re.search(r'__(\d+)-', s['id']).group(1))
    for s in S: s['X'] = np.array(s['X']).reshape(-1, 38)
    bots = [s for s in S if s['kind'] == 'bot' and (idx(s) // 4) % 2 == 0 and not s['group'].startswith('replay')]
    hum = [s for s in S if s['kind'] == 'human' and s['split'] in ('train', 'val')]
    tools = sorted({s['group'] for s in bots}); ds = sorted({s['group'] for s in hum})
    print('set | ' + ' | '.join(tools) + ' | human session FPR worst (dataset) | pooled | params')
    for name, us in SETS.items():
        spec = install(BASE, [U[u] for u in us])
        sm = lambda s: ema_max(prob(spec, s['X'])) if len(s['X']) else 0.0
        det = {t: np.mean([sm(s) >= 0.5 for s in bots if s['group'] == t]) for t in tools}
        fpr = {d: np.mean([sm(s) >= 0.5 for s in hum if s['group'] == d]) for d in ds}
        w = max(fpr, key=fpr.get)
        print(f'{name} | ' + ' | '.join(f'{100 * det[t]:.0f}%' for t in tools) + f' | {100 * fpr[w]:.2f}% ({w}) | {100 * np.mean([sm(s) >= 0.5 for s in hum]):.2f}% | {n_params([U[u] for u in us])}')


def build(name):
    us = [U[u] for u in SETS[name]]
    spec = install(BASE, us)
    (HERE / 'models').mkdir(exist_ok=True)
    (HERE / 'models' / f'bench-{name}.json').write_text(json.dumps(spec))
    (HERE / 'models' / f'bench-{name}.units.json').write_text(json.dumps(us))
    print('wrote', name, n_params(us), 'params')


if __name__ == '__main__':
    design() if sys.argv[1] == 'design' else build(sys.argv[2])

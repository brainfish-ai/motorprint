"""Per-session provenance statistics from the round-3 probe (bench/data/raw2). Prints per-tool rates so candidate
in-browser signals can be judged on the DESIGN half. Usage: python3 probe_stats.py [design|eval|all]"""
import json, glob, sys, collections, re
import numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
H = sys.argv[1] if len(sys.argv) > 1 else 'design'
def sess():
    for f in sorted(glob.glob(str(ROOT / 'bench' / 'data' / 'raw2' / '*' / '*.json'))):
        s = json.load(open(f)); i = int(re.search(r'__(\d+)-', f).group(1)); h = 'design' if (i // 4) % 2 == 0 else 'eval'
        if H != 'all' and h != H: continue
        s['tool'] = Path(f).parent.name; s['task'] = re.search(r'-(\w+)\.json', f).group(1); yield s
def stats(s):
    P = s.get('probe', []); o = {}
    kd_t = [p['t'] for p in P if p['k'] == 'keydown']
    md_t = [p['t'] for p in P if p['k'] in ('mousedown', 'pointerdown')]
    tab_t = [p['t'] for p in P if p['k'] == 'keydown']  # code not stored; any key counts as a possible Tab
    bi = [p for p in P if p['k'] == 'beforeinput']
    o['n_beforeinput'] = len(bi)
    o['keyless_insert'] = sum(1 for p in bi if p.get('it') == 'insertText' and not any(0 <= p['t'] - t < 100 for t in kd_t))
    o['insert_len>1'] = sum(1 for p in bi if p.get('it') == 'insertText' and p.get('dl', 0) > 1)
    fi = [p for p in P if p['k'] == 'focusin' and p.get('tag') in ('INPUT', 'TEXTAREA', 'SELECT')]
    o['n_focus'] = len(fi)
    o['causeless_focus'] = sum(1 for p in fi if not any(0 <= p['t'] - t < 500 for t in md_t + tab_t))
    downs = [p for p in P if p['k'] == 'mousedown']
    o['n_down'] = len(downs)
    pdown = [p for p in P if p['k'] == 'pointerdown']
    o['down_pressure'] = collections.Counter(round(p['pr'], 2) for p in pdown).most_common(1)[0][0] if pdown else None
    o['down_wh'] = collections.Counter((p['w'], p['h']) for p in pdown).most_common(1)[0][0] if pdown else None
    o['pt'] = collections.Counter(p['pt'] for p in P if p['k'] == 'pointermove').most_common(1)[0][0] if any(p['k'] == 'pointermove' for p in P) else None
    kds = [p for p in P if p['k'] == 'keydown']
    o['n_kd'] = len(kds); o['kd_no_code'] = sum(1 for p in kds if not p.get('kc')); o['kd_no_keycode'] = sum(1 for p in kds if not p.get('kcode'))
    o['kd_loc'] = collections.Counter(p.get('loc') for p in kds).most_common(1)[0][0] if kds else None
    kp = sum(1 for p in P if p['k'] == 'keypress'); o['keypress_per_kd'] = kp / len(kds) if kds else None
    o['lag_down_med'] = float(np.median([p['lag'] for p in downs])) if downs else None
    o['lag_kd_med'] = float(np.median([p['lag'] for p in kds])) if kds else None
    mm = [p for p in P if p['k'] == 'mousemove']
    o['lag_mm_med'] = float(np.median([p['lag'] for p in mm])) if mm else None
    o['lag_min'] = float(min(p['lag'] for p in P if p['k'] in ('mousedown', 'keydown', 'wheel'))) if any(p['k'] in ('mousedown', 'keydown', 'wheel') for p in P) else None
    wh = [p for p in P if p['k'] == 'wheel']
    o['n_wheel'] = len(wh); o['wheel_dy'] = collections.Counter(abs(p['dy']) for p in wh).most_common(2) if wh else None
    o['wheel_dm'] = collections.Counter(p['dm'] for p in wh).most_common(1)[0][0] if wh else None
    o['ce_gt1_frac'] = float(np.mean([p['ce'] > 1 for p in P if p['k'] == 'pointermove'])) if any(p['k'] == 'pointermove' for p in P) else None
    clicks = [p for p in P if p['k'] == 'click']; o['click_detail0'] = sum(1 for p in clicks if p.get('d') == 0)
    o['untrusted'] = sum(1 for p in P if not p['tr'])
    o['fx'] = sum(1 for p in mm if p.get('fx'))
    # mousedown not preceded by a pointerover/mousemove at the same spot within the session
    o['down_no_move'] = sum(1 for d in downs if not any(p['k'] == 'mousemove' and p['t'] <= d['t'] for p in P))
    return o
if __name__ == '__main__':
    by = collections.defaultdict(list)
    for s in sess(): by[s['tool']].append((s['task'], stats(s)))
    keys = ['keyless_insert', 'insert_len>1', 'causeless_focus', 'kd_no_code', 'kd_no_keycode', 'click_detail0', 'untrusted', 'down_no_move', 'fx']
    print('tool | n | ' + ' | '.join(f'{k} (sess>0)' for k in keys))
    for t, L in sorted(by.items()):
        print(t, len(L), ' '.join(f"{k}={np.mean([o[k] > 0 for _, o in L]):.2f}" for k in keys))
    for t, L in sorted(by.items()):
        f = lambda k: [o[k] for _, o in L if o[k] is not None]
        print(t, 'lag down', np.round(np.percentile(f('lag_down_med'), [10, 50, 90]), 2) if f('lag_down_med') else '-', 'lag kd', np.round(np.percentile(f('lag_kd_med'), [10, 50, 90]), 2) if f('lag_kd_med') else '-',
              'lag mm', np.round(np.percentile(f('lag_mm_med'), [10, 50, 90]), 2) if f('lag_mm_med') else '-', 'lag_min', np.round(np.percentile(f('lag_min'), [10, 50, 90]), 2) if f('lag_min') else '-',
              'press', collections.Counter(map(str, f('down_pressure'))).most_common(2), collections.Counter(map(str, f('down_wh'))).most_common(1), collections.Counter(f('pt')).most_common(2),
              'kploc', collections.Counter(f('kd_loc')).most_common(2), 'kp/kd', np.round(np.mean(f('keypress_per_kd')), 2) if f('keypress_per_kd') else '-',
              'wheel', collections.Counter(str(w) for w in f('wheel_dy')).most_common(2), 'dm', collections.Counter(f('wheel_dm')).most_common(2), 'ce>1', np.round(np.mean(f('ce_gt1_frac')), 3) if f('ce_gt1_frac') else '-')

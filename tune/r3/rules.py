"""Round-3 provenance rules, per session. Writes tune/r3/flags.json:
  bots1[sid]  (bench/data/raw, motion recorder only)     -> {F1}
  bots2[sid]  (bench/data/raw2, recorder + probe)          -> {F1, F2, F3, F4, F5}
  humans[id]  (data/external/sessions cut into the same 10 s segments as bench/featurize.ts, id = sid@k) -> {F1}
F1 teleport_instant_click: a mousedown whose previous 1 s holds exactly ONE mousemove, that move <= 30 ms before the
   press, and a mouseup < 5 ms after the press (a scripted 'move to target, press, release').  Verifiable on humans:
   AdSERP, BOUN and DUX log moves + presses.
F2 pressure0_press: a pointerdown with pointerType 'mouse' and pressure 0. The Pointer Events spec says a
   mouse with a button down reports 0.5; CDP Input.dispatchMouseEvent without `force` reports 0. NOT verifiable on our
   human datasets (they have no pointer attributes); checked only on real OS input (xdotool / pyautogui sessions).
F3 keyless_insert: a beforeinput with inputType 'insertText' and no keydown in the previous 100 ms (CDP insertText /
   fill). NOT verifiable on human datasets (their input events are synthesised from keys).
F4 causeless_focus: focus moves into an input/textarea/select with no pointerdown/mousedown/keydown in the previous
   500 ms, after the first input event of the page (report-only, not used: page scripts may focus fields).
F5 untrusted: any isTrusted=false input event (the existing isTrusted baseline)."""
import json, glob, re, bisect
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def f1(ev, W=1000, near=30, inst=5):
    ev = sorted((e for e in ev if isinstance(e.get('t'), (int, float))), key=lambda e: e['t'])
    mt = [e['t'] for e in ev if e['k'] == 'm']; ups = [e['t'] for e in ev if e['k'] == 'u']
    for e in ev:
        if e['k'] != 'd': continue
        i = bisect.bisect_right(mt, e['t']); j = bisect.bisect_left(mt, e['t'] - W)
        if not (i - j == 1 and e['t'] - mt[i - 1] <= near): continue
        k = bisect.bisect_left(ups, e['t'])
        if k < len(ups) and ups[k] - e['t'] < inst: return 1
    return 0


def probe_rules(P):
    o = {}
    o['F2'] = int(any(p['k'] == 'pointerdown' and p.get('pt') == 'mouse' and p.get('pr') == 0 for p in P))
    kd = [p['t'] for p in P if p['k'] == 'keydown']
    o['F3'] = int(any(p['k'] == 'beforeinput' and p.get('it') == 'insertText' and not any(0 <= p['t'] - t < 100 for t in kd) for p in P))
    cause = sorted(p['t'] for p in P if p['k'] in ('pointerdown', 'mousedown', 'keydown'))
    first = cause[0] if cause else float('inf')
    o['F4'] = int(any(p['k'] == 'focusin' and p.get('tag') in ('INPUT', 'TEXTAREA', 'SELECT') and p['t'] > first and not any(0 <= p['t'] - t < 500 for t in cause) for p in P))
    o['F5'] = int(any(not p['tr'] for p in P))
    return o


if __name__ == '__main__':
    out = {'bots1': {}, 'bots2': {}, 'humans': {}}
    for f in glob.glob(str(ROOT / 'bench' / 'data' / 'raw' / '*' / '*.json')):
        s = json.load(open(f)); out['bots1'][s['sid']] = {'F1': f1(s['events'])}
    for f in glob.glob(str(ROOT / 'bench' / 'data' / 'raw2' / '*' / '*.json')):
        s = json.load(open(f)); out['bots2'][s['sid']] = {'F1': f1(s['events']), **probe_rules(s.get('probe', []))}
    split = json.loads((ROOT / 'bench' / 'human_split.json').read_text())
    for ds in split['datasets']:
        for line in open(ROOT / 'data' / 'external' / 'sessions' / f'{ds}.jsonl'):
            if not line.strip(): continue
            s = json.loads(line); ev = sorted(s['events'], key=lambda e: e['t'])
            if not ev: continue
            t0 = ev[0]['t']; k = 0
            while t0 + k * 10000 <= ev[-1]['t']:
                seg = [e for e in ev if t0 + k * 10000 <= e['t'] < t0 + (k + 1) * 10000]
                if len(seg) >= 4: out['humans'][f"{s['sid']}@{k}"] = {'F1': f1(seg)}
                k += 1
    (Path(__file__).parent / 'flags.json').write_text(json.dumps(out))
    print({k: len(v) for k, v in out.items()})

"""Convert open human-behaviour datasets into motorprint's event format (src/types.ts).

Output: data/external/sessions/<dataset>.jsonl, one session per line:
  {"label":"human","style":"real_<dataset>","dataset":..,"user":..,"events":[{k,t,x,y,tr,...}]}

Normalisation applied to every dataset (documented in DATA.md):
  * timestamps -> milliseconds relative to session start (features quantise to 1 ms anyway)
  * coordinates -> integer CSS pixels
  * mouse sampling -> browser-like: sources sampled faster than a display frame are coalesced to
    rAF-aligned frames at a random per-session refresh rate (60/120/144 Hz, or left raw), keeping the
    latest sample per frame and its own timestamp, exactly like Chrome's mousemove coalescing
  * long recordings are cut into <= 60 s chunks; chunks with < 20 events are dropped
  * keystroke-only datasets get an `input` event 1 ms after each printable keydown (what a browser emits)
  * isTrusted = 1 for everything (real hardware input)
Usage: python3 data/external/convert/convert.py [--only adserp,dux,...]
"""
import csv, glob, gzip, json, math, os, random, sys, zipfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / 'raw'
OUT = HERE.parent / 'sessions'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE))
CHUNK_MS = 60000
rng = random.Random(1234)


def coalesce(moves, mode):
    """moves: list of (t_ms, x, y) sorted. mode: 'raw' or refresh rate in Hz."""
    if mode == 'raw' or not moves: return moves
    P = 1000.0 / mode; phase = rng.uniform(0, P)
    out = {}
    for t, x, y in moves:
        out[math.ceil((t - phase) / P)] = (t, x, y)
    return [out[k] for k in sorted(out)]


def pick_rate(weights=((60, .55), (120, .2), (144, .1), ('raw', .15))):
    r = rng.random(); acc = 0
    for v, w in weights:
        acc += w
        if r <= acc: return v
    return 'raw'


def finish(events, dataset, user, sid, extra=None):
    """Sort, drop duplicate consecutive mouse positions, rebase time, chunk."""
    events.sort(key=lambda e: e['t'])
    clean, last = [], None
    for e in events:
        if e['k'] == 'm':
            if last == (e['x'], e['y']): continue
            last = (e['x'], e['y'])
        clean.append(e)
    out = []
    if not clean: return out
    start = clean[0]['t']; cur = []; c0 = start
    for e in clean:
        if e['t'] - c0 > CHUNK_MS:
            if len(cur) >= 20: out.append(cur)
            cur = []; c0 = e['t']
        cur.append(e)
    if len(cur) >= 20: out.append(cur)
    res = []
    for i, ch in enumerate(out):
        t0 = ch[0]['t']
        evs = [{**e, 't': round(e['t'] - t0 + 500, 1)} for e in ch]
        res.append(dict(label='human', style=f'real_{dataset}', dataset=dataset, user=f'{dataset}:{user}', sid=f'{sid}#{i}', events=evs, **(extra or {})))
    return res


def M(t, x, y): return {'k': 'm', 't': t, 'x': int(round(x)), 'y': int(round(y)), 'tr': 1}
def B(k, t, x, y): return {'k': k, 't': t, 'x': int(round(x)), 'y': int(round(y)), 'tr': 1}
PRINTABLE_PREFIX = ('LETTER_', 'DIGIT', 'NUMPAD', 'SPACE', 'COMMA', 'PERIOD', 'MINUS', 'EQUALS', 'SLASH', 'SEMICOLON', 'QUOTE', 'BRACKET', 'BACK_SLASH', 'AT')


# ---------------- AdSERP (Zenodo 15236546, CC BY 4.0) ----------------
def adserp(max_sessions=1200):
    files = sorted(glob.glob(str(RAW / 'adserp' / 'mouse-movement-data' / '*.csv')))
    rng.shuffle(files)
    per_user = defaultdict(int); out = []
    for f in files:
        user = os.path.basename(f).split('-')[0]
        if per_user[user] >= max_sessions // 47 + 1: continue
        per_user[user] += 1
        ev, moves, lasty = [], [], None
        for r in csv.DictReader(open(f)):
            t = int(r['timestamp']); e = r['event']
            if e == 'mousemove': moves.append((t, float(r['xpos']), float(r['ypos'])))
            elif e in ('mousedown', 'mouseup', 'click'):
                ev.append(B({'mousedown': 'd', 'mouseup': 'u', 'click': 'c'}[e], t, float(r['xpos']), float(r['ypos'])))
            elif e == 'wheel': ev.append({'k': 'w', 't': t, 'tr': 1})  # delta not logged
            elif e == 'scroll':
                y = float(r['ypos']); ev.append({'k': 's', 't': t, 'dy': 0 if lasty is None else y - lasty, 'tr': 1}); lasty = y
        ev += [M(*m) for m in moves]  # already ~60 Hz browser events
        out += finish(ev, 'adserp', user, os.path.basename(f))
    return out


# ---------------- MouseTask (Zenodo 6559329, CC BY 4.0) ----------------
def mousetask(max_sessions=2500):
    d = json.load(gzip.open(RAW / 'MouseTask_dataset.json.gz', 'rt'))
    users = list(d); rng.shuffle(users)
    per = max_sessions // len(users) + 1; out = []
    for uid in users:
        sess = list(d[uid].get('TaskData', {}).items()); rng.shuffle(sess)
        for sk, s in sess[:per]:
            raw = s['mTaskData']; raw = raw.values() if isinstance(raw, dict) else raw
            moves = sorted((e['t'], e['x'], e['y']) for e in raw if e.get('e') == 'Mo')
            # 'Cl' events carry no press/release split, so clicks are dropped (movement only)
            out += finish([M(*m) for m in moves], 'mousetask', uid, sk)
    return out


# ---------------- DUX (Zenodo 7778612, CC BY 4.0): browser web-app sessions, mouse + keyboard ----------------
def dux(max_chunks=1500):
    by = defaultdict(list)
    with open(RAW / 'dux-v1.csv') as f:
        r = csv.reader(f, delimiter='\t'); h = next(r); I = {k: i for i, k in enumerate(h)}
        for row in r:
            by[row[0]].append(row)
    out = []
    for s, rows in by.items():
        mode = 60 if rng.random() < 0.5 else 'raw'
        moves, ev, lasty = [], [], None
        for row in rows:
            t = int(row[I['timestamp']]); ty = row[I['type']]
            x, y = row[I['x']], row[I['y']]
            if ty == 'MouseMovement': moves.append((t, float(x), float(y)))
            elif ty in ('MouseButtonDown', 'MouseButtonUp', 'MouseClick'):
                ev.append(B({'MouseButtonDown': 'd', 'MouseButtonUp': 'u', 'MouseClick': 'c'}[ty], t, float(x or 0), float(y or 0)))
            elif ty in ('KeyPressed', 'KeyReleased'):
                key = row[I['key']] or 'x'
                ev.append({'k': 'kd' if ty == 'KeyPressed' else 'ku', 't': t, 'tr': 1, 'kc': key})
                if ty == 'KeyPressed' and key.startswith(PRINTABLE_PREFIX): ev.append({'k': 'i', 't': t + 1, 'tr': 1})
            elif ty == 'Scroll':
                yp = float(row[I['yPosition']] or 0); ev.append({'k': 's', 't': t, 'dy': 0 if lasty is None else yp - lasty, 'tr': 1}); lasty = yp
        ev += [M(*m) for m in coalesce(sorted(moves), mode)]
        out += finish(ev, 'dux', s, f'dux{s}', dict(rate=str(mode)))
    rng.shuffle(out)
    return out[:max_chunks]


# ---------------- Bogazici (Mendeley w6cxr8yc7p v2, CC BY 4.0): desktop free use, ~125 Hz OS events ----------------
def boun(per_user=45):
    from splitzip import SplitZip
    d = RAW / 'boun'
    z = SplitZip([str(d / f'boun-mouse-dynamics-dataset.z{i:02d}') for i in range(1, 10)] + [str(d / 'boun-mouse-dynamics-dataset.zip')])
    by = defaultdict(list)
    for e in z.entries:
        p = e[0].split('/')
        if e[0].endswith('.csv') and len(p) >= 5 and p[1] == 'users': by[p[2]].append(e)
    out = []
    for user, ents in sorted(by.items()):
        rng.shuffle(ents); got = 0
        for e in ents:
            if got >= per_user: break
            rows = z.read(e).decode('utf8', 'replace').splitlines()[1:]
            moves, ev = [], []
            for r in rows:
                p = r.split(',')
                if len(p) < 5: continue
                try: t = float(p[0]) * 1000; x = float(p[1]); y = float(p[2])
                except ValueError: continue
                st = p[4]
                if st in ('Move', 'Drag'): moves.append((t, x, y))
                elif st == 'Pressed': ev.append(B('d', t, x, y))
                elif st == 'Released':
                    ev.append(B('u', t, x, y))
                    if p[3] == 'Left': ev.append(B('c', t + 0.5, x, y))
            mode = pick_rate()
            ev += [M(*m) for m in coalesce(sorted(moves), mode)]
            ch = finish(ev, 'boun', user, e[0].split('/')[-1], dict(rate=str(mode)))
            rng.shuffle(ch); ch = ch[:3]
            out += ch; got += len(ch)
    return out


# ---------------- KeyRecs (Zenodo 7886743, CC BY 4.0): free-text digraph timings ----------------
def keyrecs(max_sessions=400):
    seqs = defaultdict(list)
    with open(RAW / 'keyrecs-free-text.csv') as f:
        r = csv.reader(f); h = [c.strip() for c in next(r)]; I = {k: i for i, k in enumerate(h)}
        for row in r:
            try: seqs[(row[0], row[1])].append((row[I['key1']], row[I['key2']], float(row[I['DU.key1.key1']]), float(row[I['DD.key1.key2']])))
            except (ValueError, IndexError): continue
    out = []
    for (p, s), rows in seqs.items():
        ev, t = [], 1000.0
        for k1, k2, hold, dd in rows:
            if not (0 < hold < 2) or not (-1 < dd < 5): t += 300; continue
            code = 'Key' + k1.upper() if len(k1) == 1 and k1.isalpha() else k1
            ev.append({'k': 'kd', 't': round(t, 1), 'tr': 1, 'kc': code})
            if len(k1) == 1 or k1 == 'Space': ev.append({'k': 'i', 't': round(t + 1, 1), 'tr': 1})
            ev.append({'k': 'ku', 't': round(t + hold * 1000, 1), 'tr': 1, 'kc': code})
            t += max(dd * 1000, 1)
        out += finish(ev, 'keyrecs', p, f'{p}-{s}')
    rng.shuffle(out)
    return out[:max_sessions]


# ---------------- CMU DSL-StrongPasswordData (Killourhy & Maxion 2009) ----------------
def cmu(max_sessions=200):
    rows = list(csv.DictReader(open(RAW / 'DSL-StrongPasswordData.csv')))
    keys = ['period', 't', 'i', 'e', 'five', 'Shift.r', 'o', 'a', 'n', 'l', 'Return']
    code = dict(period='Period', t='KeyT', i='KeyI', e='KeyE', five='Digit5', o='KeyO', a='KeyA', n='KeyN', l='KeyL', Return='Enter')
    code['Shift.r'] = 'KeyR'
    by = defaultdict(list)
    for r in rows: by[(r['subject'], r['sessionIndex'])].append(r)
    out = []
    for (subj, si), reps in by.items():
        ev, t = [], 1000.0
        for r in reps[:25]:
            for j, k in enumerate(keys):
                kc = code[k]
                if k == 'Shift.r':  # shift chord around 'r'
                    ev.append({'k': 'kd', 't': round(t - 80, 1), 'tr': 1, 'kc': 'ShiftLeft'})
                    ev.append({'k': 'ku', 't': round(t + float(r['H.Shift.r']) * 1000 + 30, 1), 'tr': 1, 'kc': 'ShiftLeft'})
                ev.append({'k': 'kd', 't': round(t, 1), 'tr': 1, 'kc': kc})
                if kc != 'Enter': ev.append({'k': 'i', 't': round(t + 1, 1), 'tr': 1})
                ev.append({'k': 'ku', 't': round(t + float(r[f'H.{k}']) * 1000, 1), 'tr': 1, 'kc': kc})
                if j + 1 < len(keys): t += float(r[f'DD.{k}.{keys[j + 1]}']) * 1000
            t += rng.uniform(1200, 3000)  # gap between repetitions is not recorded
        out += finish(ev, 'cmu', subj, f'{subj}-{si}')
    rng.shuffle(out)
    return out[:max_sessions]


ALL = dict(adserp=adserp, mousetask=mousetask, dux=dux, boun=boun, keyrecs=keyrecs, cmu=cmu)
if __name__ == '__main__':
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else list(ALL)
    for name in only:
        sess = ALL[name]()
        with open(OUT / f'{name}.jsonl', 'w') as f:
            for s in sess: f.write(json.dumps(s, separators=(',', ':')) + '\n')
        users = len({s['user'] for s in sess}); n_ev = sum(len(s['events']) for s in sess)
        print(f'{name}: {len(sess)} sessions, {users} users, {n_ev} events')

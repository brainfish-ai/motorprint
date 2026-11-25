"""Pick real human trace segments from TEST users only (never trained on) for the replay attacks.
50 segments of 12 s per dataset, deterministic. -> bench/data/replay-traces.jsonl (gitignored, derived from raw data)."""
import json, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
here = Path(__file__).parent
split = json.loads((here / 'human_split.json').read_text())
test = set(split['test'])
SEG, PER, VW, VH = 12000, 50, 1270, 790
out = []
for ds in split['datasets']:
    rng = random.Random(f'replay-{ds}')
    sess = [s for s in map(json.loads, open(ROOT / 'data' / 'external' / 'sessions' / f'{ds}.jsonl')) if s['user'] in test]
    sess.sort(key=lambda s: s['sid'])
    got, tries = 0, 0
    while got < PER and tries < 5000:
        tries += 1
        s = rng.choice(sess); ev = s['events']
        if len(ev) < 30: continue
        t0 = rng.choice(ev[: max(1, len(ev) - 30)])['t']
        seg = [e for e in ev if t0 <= e['t'] < t0 + SEG]
        if len(seg) < 30: continue
        xs = [e['x'] for e in seg if 'x' in e]; ys = [e['y'] for e in seg if 'y' in e]
        ox, oy = (min(0, min(xs)), min(0, min(ys))) if xs else (0, 0)   # a few traces have negative screen coords: shift into view
        sc = min(1.0, VW / (max(xs) - ox), VH / (max(ys) - oy)) if xs else 1.0
        evs = []
        for e in seg:
            r = {'k': e['k'], 't': round(e['t'] - t0, 1)}
            if 'x' in e: r['x'] = round((e['x'] - ox) * sc, 1); r['y'] = round((e['y'] - oy) * sc, 1)
            for k in ('dy', 'kc'):
                if k in e: r[k] = e[k]
            evs.append(r)
        kind = 'keys' if any(e['k'] in ('kd', 'ku') for e in evs) and not xs else 'mouse'
        out.append({'id': f'{ds}-{got:02d}', 'dataset': ds, 'user': s['user'], 'src_sid': s['sid'], 'kind': kind, 'scale': sc, 'events': evs})
        got += 1
(here / 'data').mkdir(exist_ok=True)
with open(here / 'data' / 'replay-traces.jsonl', 'w') as f:
    for r in out: f.write(json.dumps(r) + '\n')
import collections
print(len(out), collections.Counter((r['dataset'], r['kind']) for r in out))

"""Lever 4 prototype: replay fingerprinting by duplicate-trace hashing across sessions (server-side).
A replay tool that reuses a recorded human trace reproduces its relative motion. Fingerprint = the sequence of
(dx, dy) between consecutive mousemoves quantised to 4 px, over a sliding run of 32 moves with >= 10 distinct steps (translation-invariant,
timing-free). A session 'collides' if any of its runs also appears in a DIFFERENT session.
Reports collision rates for replay sessions and for human segments from different users/sessions."""
import json, glob, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
K, Q, MIN_DISTINCT = 32, 4, 10
def runs(ev):
    m = [(e['x'], e['y']) for e in sorted(ev, key=lambda e: e['t']) if e['k'] == 'm' and 'x' in e]
    d = [(round((b[0] - a[0]) / Q), round((b[1] - a[1]) / Q)) for a, b in zip(m, m[1:])]
    d = [v for v in d if v != (0, 0)]
    return {hash(tuple(d[i:i + K])) for i in range(0, max(0, len(d) - K + 1)) if len(set(d[i:i + K])) >= MIN_DISTINCT}   # skip low-entropy runs (straight lines)
idx = collections.defaultdict(set); owner = {}
items = []
for tool in ['replay-cdp', 'replay-xdotool', 'ghost-cursor', 'botasaurus-human']:
    for f in sorted(glob.glob(str(ROOT / 'bench' / 'data' / 'raw' / tool / '*.json'))):
        s = json.load(open(f)); items.append((tool, s['sid'], runs(s['events'])))
for ds in ['adserp', 'boun', 'dux', 'mousetask']:
    for line in open(ROOT / 'data' / 'external' / 'sessions' / f'{ds}.jsonl'):
        s = json.loads(line); ev = sorted(s['events'], key=lambda e: e['t'])
        if not ev: continue
        t0 = ev[0]['t']; k = 0
        while t0 + k * 10000 <= ev[-1]['t']:
            seg = [e for e in ev if t0 + k * 10000 <= e['t'] < t0 + (k + 1) * 10000]; k += 1
            items.append(('human:' + ds, f"{s['sid']}@{k}", runs(seg)))
for g, sid, R in items:
    for h in R: idx[h].add(sid)
res = collections.defaultdict(lambda: [0, 0, 0])
for g, sid, R in items:
    r = res[g]; r[0] += 1
    if R: r[1] += 1
    if any(len(idx[h]) > 1 for h in R):
        # humans: only count collisions with a segment of a DIFFERENT source session (a replay of yourself is not a collision)
        others = set().union(*[idx[h] for h in R]) - {sid}
        if g.startswith('human'): others = {o for o in others if o.split('@')[0] != sid.split('@')[0]}
        if others: r[2] += 1
out = {g: dict(sessions=a, with_run=b, collide=c, rate=round(c / max(b, 1), 4)) for g, (a, b, c) in res.items()}
for g, v in out.items(): print(g, v)
(Path(__file__).parent / 'replay_fp.json').write_text(json.dumps(out, indent=1))

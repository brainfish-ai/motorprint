// Slide a window over every session and write the feature matrix.
// Usage: npx tsx train/featurize.ts [--humans real|synthetic|both] [--window 3000] [--step 750] [--out data/features.json]
//   real      = converted open datasets in data/external/sessions + data/sessions-real (default)
//   synthetic = data/sessions/human (motor-control simulator)
// Bots (data/sessions/bot) and the replay-attack set (data/sessions/replay) are always included.
// Click target rects are stripped from every session because no public human dataset records them;
// click_offset and wheel_dy_cv are therefore trained "off" (see OFF below and ModelSpec.off).
import { readdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { extractFeatures, FEATURE_NAMES, windowAt } from '../src/features';
import type { Ev } from '../src/types';

const args = process.argv.slice(2);
const arg = (k: string, d: string) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
const WIN = +arg('window', '3000'), STEP = +arg('step', '750'), MIN_EV = 4;
const HUMANS = arg('humans', 'real');
const OUT = arg('out', 'data/features.json');
export const OFF = ['click_offset', 'wheel_dy_cv'];
const root = join(import.meta.dirname, '..', 'data');
const dirs = ['sessions/bot', 'sessions/replay'];
if (HUMANS !== 'real') dirs.push('sessions/human');
if (HUMANS !== 'synthetic') dirs.push('external/sessions', 'sessions-real');

interface S { label: string; style: string; headed?: boolean; events: Ev[]; id: string; user: string; dataset: string }
const sessions: S[] = [];
for (const d of dirs) {
  const p = join(root, d);
  if (!existsSync(p)) continue;
  for (const f of readdirSync(p).sort()) {
    if (!f.endsWith('.json') && !f.endsWith('.jsonl')) continue;
    const txt = readFileSync(join(p, f), 'utf8');
    const objs = f.endsWith('.jsonl') ? txt.split('\n').filter(Boolean).map((l) => JSON.parse(l)) : [JSON.parse(txt)];
    objs.forEach((o, i) => {
      const id = `${d}/${f}#${i}`;
      const style = o.style ?? (d === 'sessions-real' ? `real_${o.label}` : 'unknown');
      const dataset = o.dataset ?? (d === 'sessions-real' ? 'collect' : style === 'synthetic' ? 'synthetic' : o.label === 'bot' ? 'bot' : style);
      sessions.push({ ...o, style, dataset, user: o.user ?? id, id });
    });
  }
}
const strip = (e: Ev): Ev => { if (e.cx === undefined) return e; const { cx, cy, w, h, ...r } = e; return r; };
const X: number[][] = [], y: number[] = [], style: string[] = [], sid: string[] = [], user: string[] = [], dataset: string[] = [], headed: number[] = [];
for (const s of sessions) {
  const ev = s.events.map(strip).sort((a, b) => a.t - b.t);
  if (!ev.length) continue;
  const t0 = ev[0].t, t1 = ev[ev.length - 1].t;
  for (let te = Math.min(t0 + WIN, t1); te <= t1 + 1e-6; te += STEP) {
    const w = windowAt(ev, te, WIN);
    if (w.length < MIN_EV) continue;
    X.push(extractFeatures(w, WIN).map((v) => Math.round(v * 1e5) / 1e5));
    y.push(s.label === 'bot' ? 1 : 0);
    style.push(s.style); sid.push(s.id); user.push(s.user); dataset.push(s.dataset); headed.push(s.headed ? 1 : 0);
  }
}
const off = OFF.map((n) => (FEATURE_NAMES as readonly string[]).indexOf(n));
writeFileSync(join(import.meta.dirname, '..', OUT), JSON.stringify({ names: FEATURE_NAMES, window: WIN, step: STEP, humans: HUMANS, off, X, y, style, sid, user, dataset, headed }));
const by: Record<string, number> = {};
style.forEach((s) => (by[s] = (by[s] ?? 0) + 1));
console.log(`[${HUMANS}] ${sessions.length} sessions -> ${X.length} windows`, by);

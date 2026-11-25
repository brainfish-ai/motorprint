// Slide a window over every recorded/synthetic session and write the feature matrix.
// Usage: npx tsx train/featurize.ts [--window 3000] [--step 750]
import { readdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { extractFeatures, FEATURE_NAMES, windowAt } from '../src/features';
import type { Ev } from '../src/types';

const args = process.argv.slice(2);
const arg = (k: string, d: string) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
const WIN = +arg('window', '3000'), STEP = +arg('step', '750'), MIN_EV = 4;
const root = join(import.meta.dirname, '..', 'data');
const dirs = ['sessions/bot', 'sessions/human', 'sessions/replay', 'sessions-real'];

interface S { label: string; style: string; headed?: boolean; events: Ev[]; id: string }
const sessions: S[] = [];
for (const d of dirs) {
  const p = join(root, d);
  if (!existsSync(p)) continue;
  for (const f of readdirSync(p)) {
    const txt = readFileSync(join(p, f), 'utf8');
    const objs = f.endsWith('.jsonl') ? txt.split('\n').filter(Boolean).map((l) => JSON.parse(l)) : [JSON.parse(txt)];
    objs.forEach((o, i) => sessions.push({ ...o, style: o.style ?? (d === 'sessions-real' ? `real_${o.label}` : 'unknown'), id: `${d}/${f}#${i}` }));
  }
}
const X: number[][] = [], y: number[] = [], style: string[] = [], sid: string[] = [], headed: number[] = [];
for (const s of sessions) {
  const ev = [...s.events].sort((a, b) => a.t - b.t);
  if (!ev.length) continue;
  const t0 = ev[0].t, t1 = ev[ev.length - 1].t;
  for (let te = Math.min(t0 + WIN, t1); te <= t1 + 1e-6; te += STEP) {
    const w = windowAt(ev, te, WIN);
    if (w.length < MIN_EV) continue;
    X.push(extractFeatures(w, WIN).map((v) => Math.round(v * 1e5) / 1e5));
    y.push(s.label === 'bot' ? 1 : 0);
    style.push(s.style); sid.push(s.id); headed.push(s.headed ? 1 : 0);
  }
}
writeFileSync(join(root, 'features.json'), JSON.stringify({ names: FEATURE_NAMES, window: WIN, step: STEP, X, y, style, sid, headed }));
const by: Record<string, number> = {};
style.forEach((s) => (by[s] = (by[s] ?? 0) + 1));
console.log(`${sessions.length} sessions -> ${X.length} windows`, by);

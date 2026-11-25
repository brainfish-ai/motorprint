// Stream every session through the same windowing the live detector uses (tick every 500 ms, 3 s window,
// >= 4 events, skip a tick if the window did not change) and write per-tick features + cheap-baseline flags.
// Bots: bench/data/raw/<tool>/*.json. Humans: data/external/sessions/*.jsonl cut into 10 s segments.
// Usage: npx tsx bench/featurize.ts -> bench/data/windows.jsonl (gitignored)
import { readFileSync, readdirSync, writeFileSync, existsSync, createWriteStream } from 'node:fs';
import { join } from 'node:path';
import { extractFeatures, windowAt } from '../src/features';
import type { Ev } from '../src/types';

const here = import.meta.dirname, root = join(here, '..');
const TICK = 500, W = 3000, SEG = 10000, MIN_EV = 4;
const out = createWriteStream(join(here, 'data', 'windows.jsonl'));
const r4 = (v: number) => (Number.isFinite(v) ? Math.round(v * 1e4) / 1e4 : 0);

/** Naive event-rate rules a site could write by hand (no model). */
function rateRule(w: Ev[]): number {
  // returns a bitmask of which rule fired: 1 teleport-press, 2 fast keys, 4 sub-frame moves, 8 input without keys
  let m = 0;
  const mv = w.filter((e) => e.k === 'm'), kd = w.filter((e) => e.k === 'kd');
  // 1. a press with no pointer movement anywhere earlier in the window (teleport click)
  const firstDown = w.find((e) => e.k === 'd');
  if (firstDown && !mv.some((e) => e.t < firstDown.t)) m |= 1;
  // 2. typing faster than any person: median inter-key interval < 30 ms over >= 4 keys
  if (kd.length >= 4) { const d = kd.slice(1).map((e, i) => e.t - kd[i].t).sort((a, b) => a - b); if (d[d.length >> 1] < 30) m |= 2; }
  // 3. pointer events closer together than any display frame: median move interval < 4 ms over >= 10 moves
  if (mv.length >= 10) { const d = mv.slice(1).map((e, i) => e.t - mv[i].t).sort((a, b) => a - b); if (d[d.length >> 1] < 4) m |= 4; }
  // 4. text changed without any key presses (fill / paste / value=)
  if (w.some((e) => e.k === 'i') && kd.length === 0) m |= 8;
  return m;
}

function stream(id: string, meta: Record<string, unknown>, evs: Ev[]) {
  evs = evs.filter((e) => Number.isFinite(e.t)).sort((a, b) => a.t - b.t);
  if (evs.length < MIN_EV) { out.write(JSON.stringify({ id, ...meta, dur: 0, n_ev: evs.length, ticks: [], X: [], untr: [], rule: [] }) + '\n'); return; }
  const t0 = evs[0].t, tEnd = evs[evs.length - 1].t;
  const ticks: number[] = [], X: number[][] = [], untr: number[] = [], rule: number[] = [];
  let sig = '';
  for (let t = t0 + TICK; t <= tEnd + TICK; t += TICK) {
    const w = windowAt(evs, t, W);
    if (w.length < MIN_EV) continue;
    const s = `${w.length}:${w[w.length - 1].t}`;
    if (s === sig) continue;
    sig = s;
    ticks.push(Math.round(t - t0)); X.push(extractFeatures(w, W).map(r4));
    untr.push(w.some((e) => e.tr === 0) ? 1 : 0); rule.push(rateRule(w));
  }
  out.write(JSON.stringify({ id, ...meta, dur: Math.round(tEnd - t0), n_ev: evs.length, ticks, X, untr, rule }) + '\n');
}

// bots
const raw = join(here, 'data', 'raw');
let nb = 0;
for (const tool of existsSync(raw) ? readdirSync(raw).sort() : []) {
  for (const f of readdirSync(join(raw, tool)).sort()) {
    const s = JSON.parse(readFileSync(join(raw, tool, f), 'utf8'));
    stream(s.sid, { kind: 'bot', group: tool, task: s.task, webdriver: s.webdriver ? 1 : 0 }, s.events); nb++;
  }
}
// humans
const split = JSON.parse(readFileSync(join(here, 'human_split.json'), 'utf8'));
const role: Record<string, string> = {};
for (const k of ['train', 'val', 'test']) for (const u of split[k]) role[u] = k;
let nh = 0;
for (const ds of split.datasets) {
  for (const line of readFileSync(join(root, 'data', 'external', 'sessions', `${ds}.jsonl`), 'utf8').split('\n')) {
    if (!line.trim()) continue;
    const s = JSON.parse(line); const ev: Ev[] = s.events.slice().sort((a: Ev, b: Ev) => a.t - b.t);
    if (!ev.length) continue;
    const t0 = ev[0].t;
    for (let k = 0; t0 + k * SEG <= ev[ev.length - 1].t; k++) {
      const seg = ev.filter((e) => e.t >= t0 + k * SEG && e.t < t0 + (k + 1) * SEG);
      if (seg.length < MIN_EV) continue;
      stream(`${s.sid}@${k}`, { kind: 'human', group: ds, user: s.user, split: role[s.user] || 'none', webdriver: 0 }, seg); nh++;
    }
  }
}
out.end(() => console.log(`bench windows: ${nb} bot sessions, ${nh} human 10 s segments -> bench/data/windows.jsonl`));

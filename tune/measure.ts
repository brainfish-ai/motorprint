// Measure a model spec: gzipped library size (with that model bundled) and inference time per window.
// Usage: npx tsx tune/measure.ts <spec.json>   -> prints JSON
import { build } from 'esbuild';
import { readFileSync, readdirSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { join } from 'node:path';
import { performance } from 'node:perf_hooks';
import { extractFeatures, windowAt } from '../src/features';
import { createModel, type ModelSpec } from '../src/model';
import type { Ev } from '../src/types';

const specPath = process.argv[2];
const specTxt = readFileSync(specPath, 'utf8');
const spec: ModelSpec = JSON.parse(specTxt);
const root = join(import.meta.dirname, '..');

async function bundle(entry: string, externals: string[] = []) {
  const r = await build({
    entryPoints: [join(root, 'src', entry)], bundle: true, minify: true, format: 'esm', write: false, external: externals,
    plugins: [{ name: 'weights', setup(b) {
      b.onResolve({ filter: /\/weights$/ }, () => ({ path: 'weights', namespace: 'w' }));
      b.onLoad({ filter: /.*/, namespace: 'w' }, () => ({ contents: `export const MODEL=${specTxt.trim()};`, loader: 'js' }));
    } }],
  });
  const code = r.outputFiles[0].contents;
  return { min: code.length, gz: gzipSync(code, { level: 9 }).length };
}

const core = await bundle('index.ts');
const react = await bundle('react.ts', ['react']);

// inference timing over real windows from the session files
const evs: Ev[][] = [];
const dir = join(root, 'data', 'sessions');
for (const sub of ['bot', 'human']) {
  for (const f of readdirSync(join(dir, sub)).slice(0, 40)) {
    const txt = readFileSync(join(dir, sub, f), 'utf8');
    const objs = f.endsWith('.jsonl') ? txt.split('\n').slice(0, 60).map((l) => JSON.parse(l)) : [JSON.parse(txt)];
    for (const o of objs) {
      const ev = (o.events as Ev[]).sort((a, b) => a.t - b.t);
      for (let t = ev[0]?.t + 3000; ev.length && t <= ev[ev.length - 1].t; t += 1500) { const w = windowAt(ev, t); if (w.length >= 4) evs.push(w); }
    }
  }
}
const m = createModel(spec);
const feats = evs.map((w) => extractFeatures(w));
let sink = 0;
for (let r = 0; r < 2; r++) for (const w of evs) sink += m.predict(extractFeatures(w)); // warmup
let t0 = performance.now();
for (let r = 0; r < 3; r++) for (const w of evs) sink += extractFeatures(w)[0];
const featUs = ((performance.now() - t0) * 1000) / (3 * evs.length);
t0 = performance.now();
for (let r = 0; r < 20; r++) for (const f of feats) sink += m.predict(f);
const modelUs = ((performance.now() - t0) * 1000) / (20 * feats.length);
const specGz = gzipSync(Buffer.from(specTxt), { level: 9 }).length;
console.log(JSON.stringify({ lib_min: core.min, lib_gz: core.gz, react_gz: react.gz, spec_gz: specGz, windows: evs.length, feat_us: +featUs.toFixed(2), model_us: +modelUs.toFixed(3), total_us: +(featUs + modelUs).toFixed(2), _: sink > -1 ? 0 : 1 }));

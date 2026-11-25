// "Replay attack": drive a real browser with recorded (here: synthetic) human traces via Playwright.
// Used only as an attack test set, never for training. Usage: npx tsx data/replay-humans.ts --n 30
import { chromium, type Browser } from 'playwright-core';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import type { Ev } from '../src/types';
const args = process.argv.slice(2);
const arg = (k: string, d: string) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
const N = +arg('n', '30'), CONC = +arg('conc', '4');
const src = join(import.meta.dirname, 'sessions', 'replay-src.jsonl');
const OUT = join(import.meta.dirname, 'sessions', 'replay');
mkdirSync(OUT, { recursive: true });
const sessions = readFileSync(src, 'utf8').split('\n').filter(Boolean).slice(0, N).map((l) => JSON.parse(l).events as Ev[]);
const sleep = (ms: number) => new Promise((r) => setTimeout(r, Math.max(0, ms)));
async function play(browser: Browser, evs: Ev[], idx: number) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  await page.goto(arg('url', 'http://localhost:5173/collect.html'));
  await page.waitForFunction(() => (window as any).__rec);
  const t0 = Date.now(), e0 = evs[0].t;
  for (const e of evs.slice(0, 2500)) {
    if (e.t - e0 > 15000) break;
    await sleep(e.t - e0 - (Date.now() - t0));
    if (e.k === 'm') await page.mouse.move(e.x!, e.y!);
    else if (e.k === 'd') await page.mouse.down();
    else if (e.k === 'u') await page.mouse.up();
    else if (e.k === 'kd' && e.kc) await page.keyboard.down(e.kc).catch(() => {});
    else if (e.k === 'ku' && e.kc) await page.keyboard.up(e.kc).catch(() => {});
    else if (e.k === 'w') await page.mouse.wheel(0, e.dy ?? 0);
    if (page.url().indexOf('collect') < 0) break;
  }
  const out = await page.evaluate(() => (window as any).__rec.events);
  await ctx.close();
  writeFileSync(join(OUT, `replay-${idx}.json`), JSON.stringify({ label: 'bot', style: 'replay', events: out }));
}
const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true });
const q = sessions.map((s, i) => [s, i] as const);
await Promise.all(Array.from({ length: CONC }, async () => { while (q.length) { const [s, i] = q.pop()!; await play(browser, s, i).catch((e) => console.error(e.message)); } }));
await browser.close();
console.log('replayed', sessions.length);

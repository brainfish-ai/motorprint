// Drive the built demo with (1) a replayed synthetic-human trace and (2) a scripted Playwright bot.
// Saves screenshots + a video to ../bot-detect-artifacts. Usage: npx tsx tools/demo-run.ts [--url http://localhost:4173/]
import { chromium } from 'playwright-core';
import { mkdirSync, readFileSync, readdirSync, renameSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import type { Ev } from '../src/types';
const args = process.argv.slice(2);
const URL = args.includes('--url') ? args[args.indexOf('--url') + 1] : 'http://localhost:4173/';
const ART = join(import.meta.dirname, '..', '..', 'bot-detect-artifacts');
mkdirSync(ART, { recursive: true });
const sleep = (ms: number) => new Promise((r) => setTimeout(r, Math.max(0, ms)));
const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true });
const vdir = join(ART, 'video-tmp');
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, recordVideo: { dir: vdir, size: { width: 1440, height: 900 } } });
const page = await ctx.newPage();
await page.goto(URL);
await page.addStyleTag({ content: 'footer a{pointer-events:none}' });
await sleep(800);
await page.evaluate(() => window.scrollTo(0, 0)); await sleep(150);
await page.screenshot({ path: join(ART, '01-demo-idle.png') });
const score = () => page.evaluate(() => (window as any).__score?.score ?? null);

// ---- 1. replayed synthetic human (also demonstrates the replay limitation) ----
const src = readFileSync(join(import.meta.dirname, '..', 'data', 'sessions', 'replay-src.jsonl'), 'utf8').split('\n').filter(Boolean);
const human = (JSON.parse(src[src.length - 1]).events as Ev[]).filter((e) => e.k === 'm' || e.k === 'kd' || e.k === 'ku' || e.k === 'w');
const t0 = Date.now(), e0 = human[0].t;
let focused = false;
for (const e of human) {
  if (e.t - e0 > 9000) break;
  await sleep(e.t - e0 - (Date.now() - t0));
  if (e.k === 'm') await page.mouse.move(e.x! + 80, e.y! + 40);
  else if (e.k === 'w') await page.mouse.wheel(0, e.dy ?? 0);
  else if (e.kc && /^Key|Space/.test(e.kc)) {
    if (!focused) { await page.focus('#field'); focused = true; }
    e.k === 'kd' ? await page.keyboard.down(e.kc) : await page.keyboard.up(e.kc);
  }
}
await sleep(600);
const humanScore = await score();
await page.evaluate(() => window.scrollTo(0, 0)); await sleep(150);
await page.screenshot({ path: join(ART, '02-demo-human-trace-low.png') });
console.log('replayed human trace score', humanScore);

// ---- 2. scripted bot ----
await page.evaluate(() => (document.getElementById('field') as HTMLInputElement).value = '');
await page.mouse.move(700, 450);
const series: number[] = [];
for (let round = 0; round < 3; round++) {
  for (const id of ['btn2', 'btn5', 'btn9', 'btn1']) {
    const b = (await page.locator('#' + id).boundingBox())!;
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 12 });
    await page.mouse.down(); await page.mouse.up();
    await sleep(120);
  }
  await page.click('#field');
  await page.keyboard.type('buy 10 tickets now ', { delay: 45 });
  const sb = (await page.locator('#scrollbox').boundingBox())!;
  await page.mouse.move(sb.x + sb.width / 2, sb.y + sb.height / 2, { steps: 8 });
  for (let i = 0; i < 4; i++) { await page.mouse.wheel(0, 200); await sleep(100); }
  series.push(await score());
}
await sleep(600);
const botScore = await score();
await page.evaluate(() => window.scrollTo(0, 0)); await sleep(150);
await page.screenshot({ path: join(ART, '03-demo-bot-high.png') });
console.log('bot score series', series.map((s) => s?.toFixed(3)).join(' '), 'final', botScore);
await page.evaluate(() => window.scrollTo(0, 0));
await page.locator('.gaugebox').screenshot({ path: join(ART, '04-gauge-bot.png') });
await ctx.close();
await browser.close();
const vids = readdirSync(vdir).filter((f) => f.endsWith('.webm'));
if (vids.length) { renameSync(join(vdir, vids[0]), join(ART, 'demo-run.webm')); rmSync(vdir, { recursive: true, force: true }); }
console.log(JSON.stringify({ humanScore, botScore, series }));

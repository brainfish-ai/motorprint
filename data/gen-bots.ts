// Generate labelled bot sessions by driving demo/collect.html with Playwright.
// Usage: npx tsx data/gen-bots.ts --n 40 [--headed] [--styles a,b] [--conc 6] [--url http://localhost:5173/collect.html]
import { chromium, type Page, type Browser } from 'playwright-core';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const args = process.argv.slice(2);
const arg = (k: string, d: string) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
const N = +arg('n', '40');
const HEADED = args.includes('--headed');
const CONC = +arg('conc', '6');
const URL = arg('url', 'http://localhost:5173/collect.html');
const OUT = join(import.meta.dirname, 'sessions', 'bot');
export const TRAIN_STYLES = ['teleport', 'linear', 'eased', 'bezier', 'dom'];
export const HELDOUT_STYLES = ['ghost', 'wind', 'agent'];
const STYLES = arg('styles', [...TRAIN_STYLES, ...HELDOUT_STYLES].join(',')).split(',');
mkdirSync(OUT, { recursive: true });

const R = (a: number, b: number) => a + Math.random() * (b - a);
const RI = (a: number, b: number) => Math.floor(R(a, b + 1));
const gauss = () => { let u = 0, v = 0; while (!u) u = Math.random(); while (!v) v = Math.random(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
const sleep = (ms: number) => new Promise((r) => setTimeout(r, Math.max(0, ms)));
const SENTS = ['the quick brown fox jumps over the lazy dog', 'hello world', 'sign me up please', 'john.smith@example.com', 'order 4521 status', 'reset my password'];

type Pt = { x: number; y: number };
class Bot {
  pos: Pt = { x: R(0, 600), y: R(0, 400) };
  // per-session constants (bots are consistent; that's part of the signal)
  typeDelay = RI(20, 140);
  stepCount = RI(5, 40);
  constructor(public page: Page, public style: string) {}
  get m() { return this.page.mouse; }

  async pointIn(sel: string, exact: boolean): Promise<Pt | null> {
    const el = this.page.locator(sel).first();
    await el.scrollIntoViewIfNeeded().catch(() => {});
    const b = await el.boundingBox();
    if (!b) return null;
    if (exact) return { x: b.x + b.width / 2, y: b.y + b.height / 2 };
    return { x: b.x + b.width * R(0.2, 0.8), y: b.y + b.height * R(0.25, 0.75) };
  }

  async moveTo(p: Pt) {
    const s = this.style, a = this.pos;
    const D = Math.hypot(p.x - a.x, p.y - a.y);
    if (s === 'teleport' || s === 'agent') {
      await this.m.move(p.x, p.y);
    } else if (s === 'linear') {
      await this.m.move(p.x, p.y, { steps: this.stepCount });
    } else if (s === 'eased') {
      const n = RI(15, 35);
      for (let i = 1; i <= n; i++) {
        const t = i / n, e = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
        await this.m.move(a.x + (p.x - a.x) * e, a.y + (p.y - a.y) * e);
        await sleep(16);
      }
    } else if (s === 'bezier' || s === 'ghost') {
      const go = async (from: Pt, to: Pt, jitter: number) => {
        const d = Math.hypot(to.x - from.x, to.y - from.y);
        const nx = -(to.y - from.y) / (d || 1), ny = (to.x - from.x) / (d || 1);
        const c1 = { x: from.x + (to.x - from.x) * R(0.2, 0.4) + nx * d * R(-0.3, 0.3), y: from.y + (to.y - from.y) * R(0.2, 0.4) + ny * d * R(-0.3, 0.3) };
        const c2 = { x: from.x + (to.x - from.x) * R(0.6, 0.8) + nx * d * R(-0.3, 0.3), y: from.y + (to.y - from.y) * R(0.6, 0.8) + ny * d * R(-0.3, 0.3) };
        // ghost-cursor style: Fitts-ish step count
        const n = s === 'ghost' ? Math.max(12, Math.round(Math.log2(d / 40 + 1) * 12 + R(0, 10))) : Math.max(15, Math.min(60, Math.round(d / 8)));
        for (let i = 1; i <= n; i++) {
          let t = i / n;
          if (s === 'ghost') t = t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2;
          const u = 1 - t;
          const x = u ** 3 * from.x + 3 * u * u * t * c1.x + 3 * u * t * t * c2.x + t ** 3 * to.x + gauss() * jitter;
          const y = u ** 3 * from.y + 3 * u * u * t * c1.y + 3 * u * t * t * c2.y + t ** 3 * to.y + gauss() * jitter;
          await this.m.move(x, y);
          await sleep(s === 'ghost' ? R(6, 22) : R(4, 18));
        }
      };
      if (s === 'ghost' && D > 300) {
        const over = { x: p.x + (p.x - a.x) * R(0.03, 0.1) + gauss() * 8, y: p.y + (p.y - a.y) * R(0.03, 0.1) + gauss() * 8 };
        await go(a, over, 0.8);
        await sleep(R(30, 120));
        await go(over, p, 0.5);
      } else await go(a, p, s === 'ghost' ? 0.8 : 0);
    } else if (s === 'wind') {
      // WindMouse (Benjamin J. Land): gravity + wind physics
      let x = a.x, y = a.y, vx = 0, vy = 0, wx = 0, wy = 0;
      const G = R(7, 10), W = R(2, 4), M = R(10, 16), T = R(6, 10);
      let guard = 0;
      while (Math.hypot(p.x - x, p.y - y) > 1 && guard++ < 400) {
        const dist = Math.hypot(p.x - x, p.y - y), w = Math.min(W, dist);
        if (dist >= T) { wx = wx / Math.sqrt(3) + (2 * Math.random() - 1) * w / Math.sqrt(5); wy = wy / Math.sqrt(3) + (2 * Math.random() - 1) * w / Math.sqrt(5); }
        else { wx /= Math.sqrt(3); wy /= Math.sqrt(3); }
        vx += wx + G * (p.x - x) / dist; vy += wy + G * (p.y - y) / dist;
        const vm = Math.hypot(vx, vy), lim = dist >= T ? M : Math.max(1, M / 2 * Math.random() + 1);
        if (vm > lim) { const r = lim / 2 + Math.random() * lim / 2; vx = vx / vm * r; vy = vy / vm * r; }
        x += vx; y += vy;
        await this.m.move(x, y);
        await sleep(R(5, 12));
      }
      await this.m.move(p.x, p.y);
    }
    this.pos = p;
  }

  async press() {
    const s = this.style;
    const hold = s === 'teleport' || s === 'linear' || s === 'agent' ? 0 : s === 'eased' ? 30 : s === 'bezier' ? R(40, 120) : s === 'ghost' ? Math.max(30, 95 + gauss() * 25) : R(80, 120);
    if (s === 'linear' || s === 'eased' || s === 'ghost') await sleep(s === 'ghost' ? R(40, 200) : s === 'eased' ? 50 : 0);
    await this.m.down();
    if (hold) await sleep(hold);
    await this.m.up();
  }

  async click(sel: string) {
    if (this.style === 'dom') {
      await this.page.evaluate((q) => (document.querySelector(q) as HTMLElement)?.click(), sel);
      return;
    }
    const exact = this.style === 'teleport' || this.style === 'linear' || this.style === 'eased' || this.style === 'agent';
    const p = await this.pointIn(sel, exact);
    if (!p) return;
    if (this.style === 'teleport' && Math.random() < 0.5) { await this.page.click(sel); this.pos = p; return; }
    await this.moveTo(p);
    await this.press();
  }

  async type(text: string) {
    const s = this.style, kb = this.page.keyboard;
    await this.click('#field');
    if (s === 'dom') {
      await this.page.evaluate((t) => { const f = document.querySelector('#field') as HTMLInputElement; f.value = t; f.dispatchEvent(new Event('input', { bubbles: true })); }, text);
    } else if (s === 'agent') {
      if (Math.random() < 0.7) await this.page.fill('#field', text); else await kb.type(text);
    } else if (s === 'teleport') {
      await kb.type(text);
    } else if (s === 'linear' || s === 'wind') {
      await kb.type(text, { delay: this.typeDelay });
    } else if (s === 'eased') {
      for (const ch of text) { await kb.press(ch === ' ' ? 'Space' : ch, { delay: 20 }); await sleep(this.typeDelay + R(-20, 20)); }
    } else if (s === 'bezier') {
      for (const ch of text) { await kb.press(ch === ' ' ? 'Space' : ch, { delay: R(20, 80) }); await sleep(R(50, 200)); }
    } else if (s === 'ghost') {
      for (const ch of text) {
        await kb.press(ch === ' ' ? 'Space' : ch, { delay: Math.max(25, 90 + gauss() * 25) });
        await sleep(Math.max(20, 150 + gauss() * 50 + (ch === ' ' ? R(50, 250) : 0)));
      }
    }
  }

  async scroll() {
    const s = this.style, n = RI(2, 6), dir = Math.random() < 0.8 ? 1 : -1;
    if (s === 'dom' || (s === 'teleport' && Math.random() < 0.3)) {
      await this.page.evaluate((d) => window.scrollBy({ top: d, behavior: Math.random() < 0.5 ? 'smooth' : 'auto' }), dir * RI(200, 800));
      await sleep(400);
      return;
    }
    for (let i = 0; i < n; i++) {
      const dy = s === 'agent' ? 500 : s === 'teleport' || s === 'linear' ? 300 : s === 'eased' ? 100 : s === 'bezier' ? R(80, 200) : 100;
      await this.m.wheel(0, dir * dy);
      await sleep(s === 'teleport' ? 0 : s === 'linear' || s === 'eased' || s === 'agent' ? 100 : s === 'ghost' ? Math.max(20, 90 + gauss() * 40) : R(30, 200));
    }
  }

  async idle() {
    await sleep(this.style === 'agent' ? R(1000, 4000) : R(200, 1500));
  }
}

async function session(browser: Browser, style: string, idx: number) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  await page.goto(URL);
  await page.waitForFunction(() => (window as any).__rec);
  const bot = new Bot(page, style);
  const t0 = Date.now();
  const nActs = RI(6, 11);
  for (let i = 0; i < nActs && Date.now() - t0 < 14000; i++) {
    const r = Math.random();
    try {
      if (r < 0.5) await bot.click(`#${Math.random() < 0.75 ? 'a' + RI(1, 12) : 'b' + RI(1, 8)}`);
      else if (r < 0.7) await bot.type(SENTS[RI(0, SENTS.length - 1)]);
      else if (r < 0.9) await bot.scroll();
      else await bot.idle();
      if (style === 'agent') await sleep(R(500, 2500));
    } catch (e) { /* element offscreen etc */ }
  }
  const events = await page.evaluate(() => (window as any).__rec.events);
  await ctx.close();
  const f = join(OUT, `${style}-${HEADED ? 'headed' : 'headless'}-${Date.now()}-${idx}.json`);
  writeFileSync(f, JSON.stringify({ label: 'bot', style, headed: HEADED, events }));
  return events.length;
}

const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: !HEADED });
const jobs: [string, number][] = [];
for (const s of STYLES) for (let i = 0; i < N; i++) jobs.push([s, i]);
jobs.sort(() => Math.random() - 0.5);
let done = 0;
await Promise.all(Array.from({ length: CONC }, async () => {
  while (jobs.length) {
    const [s, i] = jobs.pop()!;
    const n = await session(browser, s, i).catch((e) => { console.error(s, e.message); return 0; });
    done++;
    if (done % 10 === 0) console.log(`${done} sessions (${s}: ${n} events)`);
  }
}));
await browser.close();
console.log('done', done);

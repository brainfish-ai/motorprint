// Off-the-shelf JS bot tools against the bench site, at their published defaults.
// Usage: node bench/tools/js-tools.mjs <tool> <from> <to>
//   tools: ghost-cursor | puppeteer-stealth | playwright-stealth | replay-cdp | playwright-mcp
import { readFileSync, existsSync, statSync } from 'node:fs';
import { join } from 'node:path';
const here = join(import.meta.dirname, '..');
const BASE = process.env.BENCH_URL || 'http://127.0.0.1:18790/';
const CHROME = process.env.CHROME || '/usr/bin/google-chrome';
const [tool, from = '0', to = '300'] = process.argv.slice(2);
const plan = JSON.parse(readFileSync(join(here, 'plan.json'), 'utf8')).slice(+from, +to);
const traces = existsSync(join(here, 'data', 'replay-traces.jsonl')) ? readFileSync(join(here, 'data', 'replay-traces.jsonl'), 'utf8').trim().split('\n').map(JSON.parse) : [];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const done = (sid) => { const f = join(here, 'data', 'raw', tool, sid + '.json'); return existsSync(f) && statSync(f).size > 400; };
const sidOf = (p) => `${tool}__${String(p.i).padStart(3, '0')}-${p.task}`;
const url = (p, task = p.task) => `${BASE}?task=${task}&sid=${sidOf(p)}`;
const ARGS = ['--no-sandbox', '--window-size=1280,800', '--disable-dev-shm-usage'];
const VIEW = { width: 1280, height: 800 };

// ---------- puppeteer family (ghost-cursor, puppeteer-extra stealth) ----------
async function puppeteerTool() {
  const puppeteer = (await import('puppeteer-extra')).default;
  const Stealth = (await import('puppeteer-extra-plugin-stealth')).default;
  puppeteer.use(Stealth());   // ghost-cursor users almost always pair it with stealth too
  const { createCursor } = await import('ghost-cursor');
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ARGS, defaultViewport: VIEW });
  for (const p of plan) {
    const sid = sidOf(p); if (done(sid)) continue;
    const page = await browser.newPage();
    try {
      await page.goto(url(p), { waitUntil: 'load' });
      if (tool === 'ghost-cursor') await ghostSession(page, createCursor(page), p);
      else await pptrSession(page, p);
      await sleep(300); await page.evaluate(() => window.__benchFlush()); await sleep(400);
    } catch (e) { console.error(sid, String(e).slice(0, 200)); }
    await page.close();
  }
  await browser.close();
}
async function ghostSession(page, cursor, p) {
  // ghost-cursor defaults: cursor.click(selector) moves along a Fitts-scaled bezier with overshoot, then clicks.
  // ghost-cursor does not type; page.type is what its README uses next to it.
  if (p.task === 'form') {
    for (const [sel, text] of [['#first', p.first], ['#last', p.last], ['#email', p.email]]) { await cursor.click(sel); await page.type(sel, text); }
    await cursor.click('#country'); await page.select('#country', p.country);
    await cursor.click('#msg'); await page.type('#msg', p.msg);
    await cursor.click('#agree'); await cursor.click('#submit');
  } else if (p.task === 'nav') {
    for (const c of p.nav) { await cursor.click(`#card-${c}`); await sleep(200); }
  } else if (p.task === 'read') {
    await cursor.move('#article');
    for (let k = 0; k < p.scrolls; k++) { await cursor.scroll({ y: p.scrollPx }); }
    await cursor.click('#read-done');
  } else {
    await cursor.click('#q'); await page.type('#q', p.query); await cursor.click('#go'); await cursor.click(`#res-${p.result}`);
  }
}
async function pptrSession(page, p) {
  // Plain Puppeteer API at defaults (what most stealth-plugin scripts do).
  if (p.task === 'form') {
    await page.type('#first', p.first); await page.type('#last', p.last); await page.type('#email', p.email);
    await page.select('#country', p.country); await page.type('#msg', p.msg); await page.click('#agree'); await page.click('#submit');
  } else if (p.task === 'nav') {
    for (const c of p.nav) { await page.click(`#card-${c}`); await sleep(300); }
  } else if (p.task === 'read') {
    await page.mouse.move(400, 300);
    for (let k = 0; k < p.scrolls; k++) { await page.mouse.wheel({ deltaY: p.scrollPx }); await sleep(250); }
    await page.click('#read-done');
  } else {
    await page.type('#q', p.query); await page.keyboard.press('Enter'); await sleep(200); await page.click(`#res-${p.result}`);
  }
}

// ---------- playwright-extra + stealth ----------
async function playwrightStealth() {
  const { chromium } = await import('playwright-extra');
  const Stealth = (await import('puppeteer-extra-plugin-stealth')).default;
  chromium.use(Stealth());
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ARGS });
  for (const p of plan) {
    const sid = sidOf(p); if (done(sid)) continue;
    const ctx = await browser.newContext({ viewport: VIEW }); const page = await ctx.newPage();
    try {
      await page.goto(url(p));
      // Playwright's recommended locator API at defaults: click() (actionability + single move), fill(), press().
      if (p.task === 'form') {
        await page.locator('#first').fill(p.first); await page.locator('#last').fill(p.last); await page.locator('#email').fill(p.email);
        await page.locator('#country').selectOption(p.country); await page.locator('#msg').fill(p.msg);
        await page.locator('#agree').check(); await page.locator('#submit').click();
      } else if (p.task === 'nav') {
        for (const c of p.nav) { await page.locator(`#card-${c}`).click(); await sleep(300); }
      } else if (p.task === 'read') {
        await page.mouse.move(400, 300);
        for (let k = 0; k < p.scrolls; k++) { await page.mouse.wheel(0, p.scrollPx); await sleep(250); }
        await page.locator('#read-done').click();
      } else {
        await page.locator('#q').click(); await page.locator('#q').pressSequentially(p.query); await page.keyboard.press('Enter'); await page.locator(`#res-${p.result}`).click();
      }
      await sleep(300); await page.evaluate(() => window.__benchFlush()); await sleep(400);
    } catch (e) { console.error(sid, String(e).slice(0, 200)); }
    await ctx.close();
  }
  await browser.close();
}

// ---------- replay of REAL held-out human traces through CDP Input.dispatch* ----------
const KEYMAP = (code) => {
  if (/^Key[A-Z]$/.test(code)) return { key: code[3].toLowerCase(), text: code[3].toLowerCase(), vk: code.charCodeAt(3) };
  if (/^Digit\d$/.test(code)) return { key: code[5], text: code[5], vk: code.charCodeAt(5) };
  const m = { Space: [' ', 32], Enter: ['Enter', 13], Backspace: ['Backspace', 8], Period: ['.', 190], Comma: [',', 188], ShiftLeft: ['Shift', 16], ShiftRight: ['Shift', 16], Tab: ['Tab', 9] }[code];
  return m ? { key: m[0], text: m[0].length === 1 ? m[0] : undefined, vk: m[1] } : { key: 'Unidentified', vk: 0 };
};
async function replayCdp() {
  // an attacker replaying traces would hide navigator.webdriver too, so use playwright-extra + stealth
  const { chromium } = await import('playwright-extra');
  const Stealth = (await import('puppeteer-extra-plugin-stealth')).default;
  chromium.use(Stealth());
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ARGS });
  for (const p of plan) {
    const tr = traces[p.i % traces.length]; if (!tr) break;
    const sidP = { ...p, task: tr.kind === 'keys' ? 'form' : 'read' };
    const sid = sidOf(sidP); if (done(sid)) continue;
    const ctx = await browser.newContext({ viewport: VIEW }); const page = await ctx.newPage();
    try {
      await page.goto(url(sidP) + `&trace=${tr.id}`);
      if (tr.kind === 'keys') await page.evaluate(() => document.getElementById('msg').focus());
      const cdp = await ctx.newCDPSession(page);
      const t0 = performance.now(); let x = 0, y = 0, down = false;
      for (const e of tr.events) {
        const wait = e.t - (performance.now() - t0); if (wait > 1) await sleep(wait);
        if (e.x !== undefined) { x = e.x; y = e.y; }
        if (e.k === 'm') await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y, button: down ? 'left' : 'none', buttons: down ? 1 : 0 });
        else if (e.k === 'd') { down = true; await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', buttons: 1, clickCount: 1 }); }
        else if (e.k === 'u') { down = false; await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', buttons: 0, clickCount: 1 }); }
        else if (e.k === 'w') await cdp.send('Input.dispatchMouseEvent', { type: 'mouseWheel', x, y, deltaX: 0, deltaY: e.dy || 100 });
        else if (e.k === 'kd' || e.k === 'ku') {
          const k = KEYMAP(e.kc || '');
          await cdp.send('Input.dispatchKeyEvent', { type: e.k === 'kd' ? (k.text ? 'keyDown' : 'rawKeyDown') : 'keyUp', code: e.kc, key: k.key, text: e.k === 'kd' ? k.text : undefined, windowsVirtualKeyCode: k.vk });
        }
      }
      await sleep(300); await page.evaluate(() => window.__benchFlush()); await sleep(400);
    } catch (e) { console.error(sid, String(e).slice(0, 200)); }
    await ctx.close();
  }
  await browser.close();
}

// ---------- the real @playwright/mcp server, driven by a scripted policy instead of an LLM ----------
async function playwrightMcp() {
  const { Client } = await import('@modelcontextprotocol/sdk/client/index.js');
  const { StdioClientTransport } = await import('@modelcontextprotocol/sdk/client/stdio.js');
  const think = (seed) => 1200 + (seed % 2300);   // stands in for model latency between tool calls (1.2-3.5 s)
  let c = null, call;
  for (const p of plan) {
    const sid = sidOf(p); if (done(sid)) continue;
    if (!c) {
    const transport = new StdioClientTransport({ command: process.execPath, args: [join(here, 'node_modules', '@playwright', 'mcp', 'cli.js'), '--headless', '--isolated', '--executable-path', CHROME, '--viewport-size', '1280x800', '--no-sandbox'] });
    c = new Client({ name: 'bench', version: '1' }); await c.connect(transport);
    call = async (name, args) => { const r = await c.callTool({ name, arguments: args }); const t = r.content?.map((x) => x.text).join('\n') || ''; if (t.startsWith('### Error')) throw new Error(name + ': ' + t.slice(0, 200)); return t; };
    }
    const refOf = (snap, label) => { const m = snap.match(new RegExp(`${label}[^\\n]*\\[ref=([^\\]]+)\\]`)); if (!m) throw new Error('no ref for ' + label); return m[1]; };
    let k = p.seed;
    const step = async (name, args) => { await sleep(think(k = (k * 48271) % 2147483647)); await call(name, args); return call('browser_snapshot', {}); };
    try {
      await call('browser_navigate', { url: url(p) }); let snap = await call('browser_snapshot', {});
      if (p.task === 'form') {
        for (const [lab, v] of [['textbox "First name"', p.first], ['textbox "Last name"', p.last], ['textbox "Email"', p.email], ['textbox "How did you hear about us\\?"', p.msg]]) snap = await step('browser_type', { element: lab, target: refOf(snap, lab), text: v });
        snap = await step('browser_select_option', { element: 'Country', target: refOf(snap, 'combobox "Country"'), values: [p.country] });
        snap = await step('browser_click', { element: 'agree', target: refOf(snap, 'checkbox "I agree to the terms"') });
        snap = await step('browser_click', { element: 'submit', target: refOf(snap, 'button "Create account"') });
      } else if (p.task === 'nav') {
        for (const ci of p.nav) { const names = [...snap.matchAll(/- link "([^"]+)" \[ref=([^\]]+)\]/g)].filter((m) => !['Home', 'Products', 'Help', 'Contact'].includes(m[1]) || true); const cards = names.slice(-4); const m = cards[ci % cards.length]; snap = await step('browser_click', { element: m[1], target: m[2] }); }
      } else if (p.task === 'read') {
        for (let s = 0; s < Math.min(4, p.scrolls); s++) snap = await step('browser_press_key', { key: 'PageDown' });
        snap = await step('browser_click', { element: 'Back to top', target: refOf(snap, 'button "Back to top"') });
      } else {
        snap = await step('browser_type', { element: 'search', target: refOf(snap, 'textbox "Search…"'), text: p.query, submit: true });
        const m = [...snap.matchAll(/- link "([^"]*result[^"]*)" \[ref=([^\]]+)\]/g)][p.result % 6];
        if (m) snap = await step('browser_click', { element: m[1], target: m[2] });
      }
      await sleep(1200);
    } catch (e) { console.error(sid, String(e).slice(0, 300)); }
  }
  if (c) await c.close().catch(() => {});
}

const T = { 'ghost-cursor': puppeteerTool, 'puppeteer-stealth': puppeteerTool, 'playwright-stealth': playwrightStealth, 'replay-cdp': replayCdp, 'playwright-mcp': playwrightMcp }[tool];
if (!T) { console.error('unknown tool', tool); process.exit(2); }
await T(); process.exit(0);

// Bench page: renders one task and streams the recorded input events to the bench server.
// The recorder is the library's own (src/recorder.ts), so events are exactly what motorprint sees in production.
import { createRecorder } from '../../src/recorder';

const q = new URLSearchParams(location.search);
const sid = q.get('sid') || 'manual-' + Date.now();
const task = q.get('task') || 'form';
document.getElementById('t-' + task)?.classList.add('on');

const words = 'shipping return refund parcel courier tracking warranty exchange label carrier delivery window customs duty'.split(' ');
const art = document.getElementById('article')!;
for (let i = 0; i < 26; i++) {
  const p = document.createElement('p');
  p.textContent = Array.from({ length: 60 }, (_, j) => words[(i * 7 + j * 3) % words.length]).join(' ') + '.';
  art.appendChild(p);
}
const PAGES: Record<string, string[]> = {
  home: ['products', 'help', 'contact', 'deals'], products: ['shoes', 'bags', 'hats', 'deals'], help: ['shipping', 'returns', 'contact', 'home'],
  contact: ['home', 'help', 'products', 'deals'], deals: ['shoes', 'hats', 'home', 'help'], shoes: ['bags', 'hats', 'home', 'deals'],
  bags: ['shoes', 'hats', 'home', 'products'], hats: ['shoes', 'bags', 'home', 'help'], shipping: ['returns', 'help', 'home', 'deals'], returns: ['shipping', 'help', 'home', 'products'],
};
const cards = document.getElementById('cards')!;
const render = () => {
  const page = (location.hash || '#home').slice(1);
  document.getElementById('nav-title')!.textContent = page[0].toUpperCase() + page.slice(1);
  cards.innerHTML = '';
  (PAGES[page] || PAGES.home).forEach((to, i) => {
    const d = document.createElement('div'); d.className = 'card';
    d.innerHTML = `<a id="card-${i}" data-to="${to}" href="#${to}">${to[0].toUpperCase() + to.slice(1)}</a><p>Browse ${to} and more. ${words.slice(i, i + 8).join(' ')}.</p>`;
    cards.appendChild(d);
  });
};
addEventListener('hashchange', render); render();
const go = () => {
  const term = (document.getElementById('q') as HTMLInputElement).value.trim() || 'all';
  const ol = document.getElementById('results')!; ol.innerHTML = '';
  for (let i = 0; i < 6; i++) ol.insertAdjacentHTML('beforeend', `<li><a id="res-${i}" href="#r${i}">${term} result ${i + 1}</a> <span>in stock</span></li>`);
};
document.getElementById('go')!.addEventListener('click', go);
document.getElementById('q')!.addEventListener('keydown', (e) => { if ((e as KeyboardEvent).key === 'Enter') go(); });
document.getElementById('results')!.addEventListener('click', (e) => { const a = (e.target as Element).closest('a'); if (a) document.getElementById('picked')!.textContent = 'Picked: ' + a.textContent; });
document.getElementById('submit')!.addEventListener('click', () => { document.getElementById('status')!.textContent = 'Account created.'; });
document.getElementById('read-done')!.addEventListener('click', () => scrollTo(0, 0));

// ---- provenance probe (bench-only diagnostics; candidates for the library) ----
// One compact record per event: what the browser says about where the event came from, never key characters.
const probe: any[] = [];
const pnow = () => performance.now();
let lastMX: number | null = null, lastMY: number | null = null;
const P = (e: Event, extra: any) => probe.push({ k: e.type, t: +e.timeStamp.toFixed(2), lag: +(pnow() - e.timeStamp).toFixed(2), tr: e.isTrusted ? 1 : 0, ...extra });
const mouseX = (e: MouseEvent) => {
  const o: any = { sx: e.screenX - e.clientX, sy: e.screenY - e.clientY, mx: e.movementX, my: e.movementY, b: e.buttons, d: e.detail };
  if (lastMX !== null) { o.dx = e.clientX - lastMX; o.dy = e.clientY - (lastMY as number); }
  if (e.type === 'mousemove') { lastMX = e.clientX; lastMY = e.clientY; }
  o.fx = e.clientX % 1 !== 0 ? 1 : 0;
  return o;
};
const po = { capture: true, passive: true } as const;
for (const n of ['mousemove', 'mousedown', 'mouseup', 'click']) addEventListener(n, (e) => P(e, mouseX(e as MouseEvent)), po);
for (const n of ['pointermove', 'pointerdown', 'pointerup', 'pointerover']) addEventListener(n, (e) => {
  const p = e as PointerEvent; const ce = (p as any).getCoalescedEvents ? (p as any).getCoalescedEvents().length : -1;
  P(e, { pt: p.pointerType, pr: p.pressure, w: p.width, h: p.height, tx: p.tiltX, ty: p.tiltY, prim: p.isPrimary ? 1 : 0, ce, pid: p.pointerId });
}, po);
for (const n of ['keydown', 'keyup', 'keypress']) addEventListener(n, (e) => { const k = e as KeyboardEvent; P(e, { rep: k.repeat ? 1 : 0, kl: k.key ? Math.min(k.key.length, 2) : 0, kc: !!k.code, loc: k.location, kcode: k.keyCode ? 1 : 0 }); }, po);
addEventListener('beforeinput', (e) => P(e, { it: (e as InputEvent).inputType, dl: ((e as InputEvent).data || '').length }), po);
addEventListener('input', (e) => P(e, { it: (e as InputEvent).inputType, dl: ((e as InputEvent).data || '').length }), po);
for (const n of ['focusin', 'focus']) addEventListener(n, (e) => P(e, { tag: ((e.target as Element)?.tagName || 'W').slice(0, 8) }), po);
addEventListener('wheel', (e) => { const w = e as WheelEvent; P(e, { dm: w.deltaMode, dy: w.deltaY, dx: w.deltaX, wd: (w as any).wheelDeltaY ?? null, fr: w.deltaY % 1 !== 0 ? 1 : 0 }); }, po);
addEventListener('touchstart', (e) => P(e, {}), po);
// rAF clock: frame times, so event timestamps can be compared with the frame grid
const frames: number[] = [];
const raf = (t: number) => { if (frames.length < 4000) frames.push(+t.toFixed(2)); requestAnimationFrame(raf); };
requestAnimationFrame(raf);
const env = { dpr: devicePixelRatio, sw: screen.width, sh: screen.height, ow: outerWidth, oh: outerHeight, iw: innerWidth, ih: innerHeight, wx: screenX, wy: screenY, hc: navigator.hardwareConcurrency, mtp: navigator.maxTouchPoints, vis: document.visibilityState, focus: document.hasFocus() };

const rec = createRecorder({ maxAgeMs: Infinity });
rec.start();
const meta = { sid, task, webdriver: !!(navigator as any).webdriver, ua: navigator.userAgent, w: innerWidth, h: innerHeight, start: performance.timeOrigin };
let sent = -1;
const flush = () => {
  if (rec.events.length + probe.length === sent) return;
  sent = rec.events.length + probe.length;
  const body = JSON.stringify({ ...meta, env, events: rec.events, probe, frames, signals: rec.signals });
  fetch('/save', { method: 'POST', headers: { 'content-type': 'application/json' }, body, keepalive: body.length < 60000 }).catch(() => {});
};
setInterval(flush, 700);
addEventListener('pagehide', flush);
(window as any).__benchFlush = flush;

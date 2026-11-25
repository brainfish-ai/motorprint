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

const rec = createRecorder({ maxAgeMs: Infinity });
rec.start();
const meta = { sid, task, webdriver: !!(navigator as any).webdriver, ua: navigator.userAgent, w: innerWidth, h: innerHeight, start: performance.timeOrigin };
let sent = -1;
const flush = () => {
  if (rec.events.length === sent) return;
  sent = rec.events.length;
  fetch('/save', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ ...meta, events: rec.events }), keepalive: rec.events.length < 5000 }).catch(() => {});
};
setInterval(flush, 700);
addEventListener('pagehide', flush);
(window as any).__benchFlush = flush;

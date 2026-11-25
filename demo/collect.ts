import { createRecorder } from '../src/recorder';
import type { Ev } from '../src/types';

const rec = createRecorder({ maxAgeMs: Infinity, onEvent: () => tick() });
rec.start();
(window as unknown as { __rec: typeof rec }).__rec = rec;

const mk = (host: HTMLElement, n: number, prefix: string) => {
  for (let i = 0; i < n; i++) {
    const b = document.createElement('button');
    b.textContent = `${prefix}${i + 1}`;
    b.className = 'tgt';
    b.id = `${prefix}${i + 1}`;
    b.style.width = `${60 + ((i * 37) % 140)}px`;
    b.addEventListener('click', () => highlightNext());
    host.appendChild(b);
  }
};
mk(document.getElementById('grid')!, 12, 'a');
mk(document.getElementById('grid2')!, 8, 'b');
const long = document.getElementById('long')!;
for (let i = 0; i < 30; i++) {
  const p = document.createElement('p');
  p.textContent = `Paragraph ${i + 1}. Scroll past this text at your own pace, then click a button further down.`;
  long.appendChild(p);
}
const btns = [...document.querySelectorAll<HTMLButtonElement>('button.tgt')];
let next = -1;
function highlightNext() {
  btns.forEach((b) => b.classList.remove('hot'));
  next = Math.floor(Math.random() * btns.length);
  btns[next].classList.add('hot');
}
highlightNext();

const status = document.getElementById('status')!;
let pending = false;
function tick() {
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => { pending = false; status.textContent = `${rec.events.length} events`; });
}
const payload = () => ({
  label: (document.getElementById('isbot') as HTMLInputElement).checked ? 'bot' : 'human',
  ua: navigator.userAgent,
  dpr: devicePixelRatio,
  viewport: [innerWidth, innerHeight],
  recordedAt: new Date().toISOString(),
  events: rec.events as Ev[],
});
document.getElementById('dl')!.addEventListener('click', () => {
  const blob = new Blob([JSON.stringify(payload())], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `session-${Date.now()}.json`;
  a.click();
});
document.getElementById('save')!.addEventListener('click', async () => {
  try {
    const r = await fetch('http://localhost:8787/session', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload()) });
    status.textContent = r.ok ? `saved (${rec.events.length} events)` : `save failed: ${r.status}`;
  } catch {
    status.textContent = 'local server not running: node tools/collect-server.mjs';
  }
});
document.getElementById('reset')!.addEventListener('click', () => rec.clear());

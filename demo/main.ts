import { createBotDetector, FEATURE_NAMES, MODEL, type BotScore } from '../src/index';

const $ = (id: string) => document.getElementById(id)!;
const grid = $('grid');
for (let i = 0; i < 9; i++) {
  const b = document.createElement('button');
  b.textContent = ['Sign up', 'Pricing', 'Docs', 'Buy now', 'Contact', 'Login', 'Blog', 'Careers', 'Demo'][i];
  b.id = `btn${i + 1}`;
  grid.appendChild(b);
}
const sb = $('scrollbox');
for (let i = 0; i < 40; i++) { const p = document.createElement('p'); p.textContent = `Line ${i + 1}: scroll me with the wheel or trackpad.`; sb.appendChild(p); }
let bytes = 0;
for (const l of MODEL.layers) bytes += l.w.length;
$('msize').textContent = `${MODEL.layers.map((l) => l.o).slice(0, -1).join('-')} hidden units, ${MODEL.layers[0].bits === 32 ? 'float32' : `int${MODEL.layers[0].bits}`} weights`;

const table = $('ftable') as HTMLTableElement;
const rows = FEATURE_NAMES.map((n) => {
  const tr = table.insertRow();
  tr.innerHTML = `<td class="n">${n}</td><td class="v">0</td><td class="b"><div style="width:0"></div></td>`;
  return tr;
});
// ---------- meter ticks ----------
const NS = 'http://www.w3.org/2000/svg';
for (let i = 0; i <= 10; i++) {
  const a = (Math.PI * i) / 10, r2 = i % 5 === 0 ? 99 : 96;
  const l = document.createElementNS(NS, 'line');
  l.setAttribute('x1', String(100 - 92 * Math.cos(a))); l.setAttribute('y1', String(110 - 92 * Math.sin(a)));
  l.setAttribute('x2', String(100 - r2 * Math.cos(a))); l.setAttribute('y2', String(110 - r2 * Math.sin(a)));
  $('ticks').appendChild(l);
}
[['0', 20], ['1', 180]].forEach(([s, x]) => {
  const t = document.createElementNS(NS, 'text');
  t.setAttribute('x', String(x)); t.setAttribute('y', '130'); t.textContent = String(s);
  $('ticks').appendChild(t);
});

// ---------- motor print pad and dynamic cursor ----------
// Both only draw; they are pointer-events:none and never feed the detector.
type Pt = { x: number; y: number; t: number; down?: boolean };
const pts: Pt[] = [];
const root = document.documentElement;
const fine = matchMedia('(pointer: fine)').matches;
const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
const GLOW: Record<string, string> = { wait: '#a3e635', human: '#a3e635', unsure: '#ffc857', bot: '#d4311f' };
const INK = '#262626';
let tone = 'wait';
const dpr = Math.min(window.devicePixelRatio || 1, 2);
const print = $('print') as HTMLCanvasElement;
const trail = document.createElement('canvas');
const ring = document.createElement('div');
const dot = document.createElement('div');
if (fine) {
  trail.className = 'cur-trail'; ring.className = 'cur-ring'; dot.className = 'cur-dot';
  [trail, ring, dot].forEach((e) => e.setAttribute('aria-hidden', 'true'));
  document.body.append(trail, ring, dot);
}
function fit() {
  const r = print.getBoundingClientRect();
  print.width = Math.round(r.width * dpr); print.height = Math.round(r.height * dpr);
  trail.width = Math.round(innerWidth * dpr); trail.height = Math.round(innerHeight * dpr);
}
fit();
addEventListener('resize', fit);
new ResizeObserver(fit).observe(print);

let mx = -100, my = -100, rx = -100, ry = -100, sc = 1, seen = false, down = false, over = '';
function track(e: PointerEvent, press?: boolean) {
  mx = e.clientX; my = e.clientY;
  pts.push({ x: mx, y: my, t: performance.now(), down: press });
  if (!live) drawPrint(performance.now());
  if (e.pointerType === 'touch') return;
  if (!seen) { rx = mx; ry = my; seen = true; }
  root.classList.add('cur-on');
  const el = e.target instanceof Element ? e.target : null;
  over = el?.closest('input, textarea') ? 'text' : el?.closest('button, a, label') ? 'hot' : '';
  root.classList.toggle('cur-text', over === 'text');
}
addEventListener('pointermove', (e) => track(e), { passive: true });
addEventListener('pointerdown', (e) => { down = true; track(e, true); }, { passive: true });
addEventListener('pointerup', () => { down = false; }, { passive: true });
root.addEventListener('pointerleave', () => root.classList.remove('cur-on'));

// motor print: the last 3 s of the pointer, scaled from the viewport into the pad
function drawPrint(now: number) {
  while (pts.length && now - pts[0].t > 3000) pts.shift();

  const pc = print.getContext('2d')!, w = print.width / dpr, h = print.height / dpr;
  const px = (p: Pt) => 10 + (p.x / innerWidth) * (w - 20), py = (p: Pt) => 10 + (p.y / innerHeight) * (h - 20);
  pc.setTransform(dpr, 0, 0, dpr, 0, 0); pc.clearRect(0, 0, w, h);
  pc.lineCap = 'round'; pc.strokeStyle = INK; pc.lineWidth = 2;
  for (let i = 1; i < pts.length; i++) {
    pc.globalAlpha = Math.max(0, 1 - (now - pts[i].t) / 3000);
    pc.beginPath(); pc.moveTo(px(pts[i - 1]), py(pts[i - 1])); pc.lineTo(px(pts[i]), py(pts[i])); pc.stroke();
  }
  pc.lineWidth = 1.5;
  for (const p of pts) {
    if (!p.down) continue;
    pc.globalAlpha = Math.max(0, 1 - (now - p.t) / 3000);
    pc.fillStyle = GLOW[tone]; pc.beginPath(); pc.arc(px(p), py(p), 6, 0, 7); pc.fill(); pc.stroke();
  }
  pc.globalAlpha = 1;
  const head = pts[pts.length - 1];
  if (head) { pc.fillStyle = INK; pc.beginPath(); pc.arc(px(head), py(head), 3.5, 0, 7); pc.fill(); }
}

// `live` is only true while animation frames are really running. A hidden or throttled page gets
// no frames, so it keeps the native cursor and unanimated meter instead of a frozen custom one.
let live = false;
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { live = false; root.classList.remove('live', 'has-cursor'); }
});
function frame(now: number) {
  if (!live) { live = true; root.classList.add('live'); root.classList.toggle('has-cursor', fine); }
  drawPrint(now);

  if (fine) {
    // the dot is exact; the ring follows on a spring, stretches with speed, swells over controls
    const k = calm ? 1 : 0.2;
    rx += (mx - rx) * k; ry += (my - ry) * k;
    const dx = mx - rx, dy = my - ry;
    const stretch = calm ? 0 : Math.min(Math.hypot(dx, dy) / 70, 0.55);
    sc += ((down ? 0.6 : over === 'hot' ? 1.55 : 1) - sc) * (calm ? 1 : 0.25);
    dot.style.transform = `translate(${mx}px, ${my}px)`;
    ring.style.transform = `translate(${rx}px, ${ry}px) rotate(${Math.atan2(dy, dx)}rad) scale(${sc * (1 + stretch)}, ${sc * (1 - stretch * 0.45)})`;

    const tc = trail.getContext('2d')!;
    tc.setTransform(dpr, 0, 0, dpr, 0, 0); tc.clearRect(0, 0, innerWidth, innerHeight);
    if (!calm) {
      tc.lineCap = 'round'; tc.strokeStyle = tone === 'bot' ? GLOW.bot : INK;
      for (let i = 1; i < pts.length; i++) {
        const life = 1 - (now - pts[i].t) / 450;
        if (life <= 0) continue;
        tc.globalAlpha = life * 0.5; tc.lineWidth = 1 + life * 3;
        tc.beginPath(); tc.moveTo(pts[i - 1].x, pts[i - 1].y); tc.lineTo(pts[i].x, pts[i].y); tc.stroke();
      }
      tc.globalAlpha = 1;
    }
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

const history: number[] = [];
const spark = $('spark') as HTMLCanvasElement;
function drawSpark() {
  const c = spark.getContext('2d')!, w = spark.width, h = spark.height;
  c.clearRect(0, 0, w, h);
  c.strokeStyle = '#e5e5e5'; c.beginPath(); c.moveTo(0, h / 2); c.lineTo(w, h / 2); c.stroke();
  c.strokeStyle = '#262626'; c.lineWidth = 2; c.beginPath();
  history.forEach((v, i) => { const x = (i / 59) * w, y = h - v * (h - 4) - 2; i ? c.lineTo(x, y) : c.moveTo(x, y); });
  c.stroke();
}
function render(s: BotScore) {
  (window as unknown as { __score: BotScore }).__score = s;
  $('score').textContent = s.score.toFixed(2);
  ($('arc') as unknown as SVGPathElement).style.strokeDashoffset = String(251.3 * (1 - s.score));
  $('needle').style.transform = `rotate(${-90 + 180 * s.score}deg)`;
  const v = $('verdict');
  const cls = s.windows < 3 ? 'unsure' : s.score >= 0.7 ? 'bot' : s.score <= 0.3 ? 'human' : 'unsure';
  tone = cls; root.dataset.tone = cls;
  v.className = `verdict ${cls}`;
  v.textContent = cls === 'bot' ? 'looks automated' : cls === 'human' ? 'looks human' : s.windows < 3 ? 'gathering signal' : 'uncertain';
  $('windows').textContent = `${s.windows} windows`;
  $('raw').textContent = `raw ${s.raw.toFixed(2)}`;
  $('inf').textContent = `${(s.inferenceMs * 1000).toFixed(0)} µs`;
  FEATURE_NAMES.forEach((n, i) => {
    const val = s.features[n];
    rows[i].cells[1].textContent = val.toFixed(2);
    const z = Math.min(1, Math.abs((val - MODEL.mean[i]) / MODEL.std[i]) / 3);
    (rows[i].cells[2].firstChild as HTMLElement).style.width = `${z * 100}%`;
  });
  history.push(s.score); if (history.length > 60) history.shift();
  drawSpark();
}
const det = createBotDetector({ onScore: render });

// ---------- floating mini-meter when scrolled out of view ----------
const gaugeSlot = $('gauge-slot');
const gaugeBox = $('gaugebox');
let isFloating = false;
function setFloating(next: boolean) {
  if (next === isFloating) return;
  isFloating = next;
  if (next) {
    gaugeSlot.style.minHeight = `${gaugeBox.offsetHeight}px`;
    gaugeBox.classList.add('floating');
  } else {
    gaugeBox.classList.remove('floating');
    gaugeSlot.style.minHeight = '';
  }
}
new IntersectionObserver(
  ([entry]) => {
    setFloating(!entry.isIntersecting && entry.boundingClientRect.top < 0);
  },
  { threshold: 0.1 },
).observe(gaugeSlot);

// ---------- bot simulation ----------
const simBtn = $('sim-bot') as HTMLButtonElement;
const fieldEl = $('field') as HTMLInputElement;
let simStop: (() => void) | null = null;

function resetAll() {
  simStop?.();
  det.reset();
  pts.length = 0;
  history.length = 0;
  tone = 'wait';
  delete root.dataset.tone;
  $('score').textContent = '--';
  ($('arc') as unknown as SVGPathElement).style.strokeDashoffset = '251.3';
  $('needle').style.transform = 'rotate(-90deg)';
  const v = $('verdict');
  v.className = 'verdict wait';
  v.textContent = 'waiting for input';
  $('windows').textContent = '0 windows';
  $('raw').textContent = 'raw --';
  $('inf').textContent = '-- ms';
  rows.forEach((tr) => {
    tr.cells[1].textContent = '0';
    (tr.cells[2].firstChild as HTMLElement).style.width = '0';
  });
  fieldEl.value = '';
  sb.scrollTop = 0;
  drawPrint(performance.now());
  drawSpark();
}

function startBotSim() {
  resetAll();
  let stopped = false;
  const timers = new Set<number>();
  const wait = (ms: number) =>
    new Promise<void>((resolve) => {
      const id = window.setTimeout(() => {
        timers.delete(id);
        resolve();
      }, ms);
      timers.add(id);
    });

  const center = (el: Element) => {
    const r = el.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  };

  let curX = innerWidth * 0.5;
  let curY = innerHeight * 0.5;

  const emitMove = (target: EventTarget, x: number, y: number) => {
    target.dispatchEvent(new PointerEvent('pointermove', { clientX: x, clientY: y, bubbles: true, pointerType: 'mouse' }));
    target.dispatchEvent(new MouseEvent('mousemove', { clientX: x, clientY: y, bubbles: true }));
  };

  const focusTarget = async (el: Element) => {
    if (stopped) return;
    const r = el.getBoundingClientRect();
    const pad = 110;
    if (r.top < pad || r.bottom > innerHeight - pad) {
      el.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'center' });
      await wait(calm ? 40 : 320);
    }
  };

  const glideTo = async (el: Element, steps = 16, stepMs = 14) => {
    await focusTarget(el);
    if (stopped) return;
    const sx = curX;
    const sy = curY;
    for (let i = 1; i <= steps; i++) {
      if (stopped) return;
      const { x: tx, y: ty } = center(el);
      const t = i / steps;
      curX = sx + (tx - sx) * t;
      curY = sy + (ty - sy) * t;
      emitMove(el, curX, curY);
      await wait(stepMs);
    }
  };

  const botClick = async (el: Element) => {
    if (stopped) return;
    el.dispatchEvent(new PointerEvent('pointerdown', { clientX: curX, clientY: curY, bubbles: true, pointerType: 'mouse', pressure: 0 }));
    el.dispatchEvent(new MouseEvent('mousedown', { clientX: curX, clientY: curY, bubbles: true, button: 0 }));
    await wait(8);
    if (stopped) return;
    el.dispatchEvent(new MouseEvent('mouseup', { clientX: curX, clientY: curY, bubbles: true, button: 0 }));
    el.dispatchEvent(new MouseEvent('click', { clientX: curX, clientY: curY, bubbles: true, button: 0 }));
    el.classList.add('sim-hit');
    const id = window.setTimeout(() => el.classList.remove('sim-hit'), 180);
    timers.add(id);
  };

  simStop = () => {
    stopped = true;
    timers.forEach((id) => clearTimeout(id));
    timers.clear();
    simBtn.textContent = 'Simulate bot';
    simBtn.classList.remove('running');
    simStop = null;
  };

  simBtn.textContent = 'Stop bot';
  simBtn.classList.add('running');

  (async () => {
    const btns = Array.from(grid.querySelectorAll('button'));
    const pick = [btns[0], btns[3], btns[5], btns[1], btns[8]].filter(Boolean);
    await focusTarget(pick[0] ?? fieldEl);
    if (stopped) return;
    const startPt = center(pick[0] ?? fieldEl);
    curX = startPt.x;
    curY = startPt.y;

    for (const b of pick) {
      if (stopped) return;
      await glideTo(b, 14, 14);
      await botClick(b);
      await wait(120);
    }

    if (!stopped) {
      await glideTo(fieldEl, 16, 14);
      await botClick(fieldEl);
      fieldEl.focus({ preventScroll: true });
      const text = 'automated checkout bot';
      for (const ch of text) {
        if (stopped) return;
        const code = ch === ' ' ? 'Space' : `Key${ch.toUpperCase()}`;
        fieldEl.dispatchEvent(new KeyboardEvent('keydown', { key: ch, code, bubbles: true }));
        fieldEl.value += ch;
        fieldEl.dispatchEvent(new InputEvent('input', { data: ch, inputType: 'insertText', bubbles: true }));
        await wait(24);
        if (stopped) return;
        fieldEl.dispatchEvent(new KeyboardEvent('keyup', { key: ch, code, bubbles: true }));
        await wait(28);
      }
    }

    if (!stopped) {
      await glideTo(sb, 14, 14);
      for (let i = 0; i < 10; i++) {
        if (stopped) return;
        sb.dispatchEvent(new WheelEvent('wheel', { deltaY: 120, clientX: curX, clientY: curY, bubbles: true }));
        sb.scrollTop += 40;
        await wait(65);
      }
    }

    for (const b of [btns[2], btns[4], btns[6], btns[7]].filter(Boolean)) {
      if (stopped) return;
      await glideTo(b, 14, 14);
      await botClick(b);
      await wait(140);
    }

    if (!stopped) simStop?.();
  })();
}

simBtn.addEventListener('click', () => {
  if (simStop) simStop();
  else startBotSim();
});

// ---------- copy buttons in install panel ----------
document.querySelectorAll<HTMLButtonElement>('.copy-btn').forEach((btn) => {
  let timer: number | undefined;
  btn.addEventListener('click', async () => {
    const codeEl = btn.closest('.codeblock')?.querySelector('code');
    const lines = codeEl?.querySelectorAll('.line');
    const code = lines?.length
      ? Array.from(lines, (el) => el.textContent ?? '').join('\n')
      : (codeEl?.textContent ?? '');
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = code;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    btn.textContent = 'Copied';
    btn.classList.add('copied');
    clearTimeout(timer);
    timer = window.setTimeout(() => {
      btn.textContent = 'Copy';
      btn.classList.remove('copied');
    }, 1500);
  });
});

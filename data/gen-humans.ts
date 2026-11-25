// Synthetic HUMAN sessions, grounded in published motor-control models.
//  - Pointing time: Fitts's law, MT = a + b*log2(D/W + 1)  (Fitts 1954; MacKenzie 1992)
//  - Aimed movements: primary ballistic submovement + corrective submovements (Meyer et al. 1988)
//  - Velocity profiles: minimum-jerk (Flash & Hogan 1985) or sigma-lognormal (Plamondon 1995)
//  - Curved paths with per-person arc bias, endpoint scatter ~ W/4 (effective width, Soukoreff & MacKenzie 2004)
//  - Physiological tremor 8-12 Hz, sub-pixel amplitude, plus slow postural drift (OU process)
//  - Browser emulation: OS mouse polling (125-1000 Hz) coalesced to display frames (60-144 Hz),
//    integer client coordinates, 0.1 ms timestamp coarsening, occasional dropped/long frames
//  - Typing: log-normal inter-key intervals with per-person tempo, digraph bursts, word-boundary pauses,
//    key rollover (next keydown before previous keyup), occasional backspace corrections (Salthouse 1986)
//  - Scrolling: wheel notches in irregular bursts with smooth-scroll animation, or trackpad momentum
// THIS IS SYNTHETIC. Replace/augment with real recordings (demo/collect.html) before production use.
// Usage: npx tsx data/gen-humans.ts --n 1500 [--seed 1]
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import type { Ev } from '../src/types';

const args = process.argv.slice(2);
const arg = (k: string, d: string) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
let seed = +arg('seed', '1');
const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
const R = (a: number, b: number) => a + rnd() * (b - a);
const RI = (a: number, b: number) => Math.floor(R(a, b + 1));
const gauss = () => { let u = 0; while (!u) u = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rnd()); };
const logn = (median: number, sigma: number) => median * Math.exp(sigma * gauss());
const pick = <T,>(xs: T[], ws?: number[]) => { if (!ws) return xs[Math.floor(rnd() * xs.length)]; let r = rnd() * ws.reduce((a, b) => a + b, 0); for (let i = 0; i < xs.length; i++) { r -= ws[i]; if (r <= 0) return xs[i]; } return xs[xs.length - 1]; };
const erf = (x: number) => { const s = Math.sign(x); x = Math.abs(x); const t = 1 / (1 + 0.3275911 * x); const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x); return s * y; };

const VW = 1280, VH = 800;
const SENTS = ['the quick brown fox jumps over the lazy dog', 'hello world', 'sign me up please', 'john.smith@example.com', 'order 4521 status', 'reset my password', 'can you help me with billing', 'ok thanks'];
const COMMON = new Set(['th', 'he', 'in', 'er', 'an', 're', 'on', 'at', 'en', 'nd', 'ti', 'es', 'or', 'te', 'of', 'ed', 'is', 'it', 'al', 'ar', 'st', 'to', 'nt', 'ng', 'se', 'ha', 'as', 'ou', 'io', 'le']);

interface Person {
  fa: number; fb: number; frame: number; poll: number; tremA: number; tremF: number; drift: number;
  arcMu: number; arcSd: number; overshoot: number; profile: number; pressMed: number; pressSd: number;
  dwellMed: number; ikiMed: number; ikiSd: number; holdMed: number; holdSd: number; errRate: number;
  wheel: 'notch' | 'trackpad'; notch: number; readMed: number; precise: number;
}
const person = (): Person => ({
  fa: R(0.05, 0.25), fb: R(0.08, 0.22),
  frame: pick([1000 / 60, 1000 / 120, 1000 / 144, 1000 / 75, 1000 / 90], [55, 20, 10, 8, 7]),
  poll: pick([8, 2, 1, 4], [35, 25, 30, 10]),
  tremA: R(0.05, 0.9), tremF: R(8, 12), drift: R(0.1, 0.8),
  arcMu: R(-0.12, 0.12), arcSd: R(0.02, 0.09), overshoot: R(0.15, 0.7), profile: rnd(),
  pressMed: R(60, 140), pressSd: R(0.15, 0.4), dwellMed: R(40, 260),
  ikiMed: R(100, 320), ikiSd: R(0.25, 0.6), holdMed: R(55, 130), holdSd: R(0.15, 0.35), errRate: R(0, 0.05),
  wheel: rnd() < 0.6 ? 'notch' : 'trackpad', notch: pick([100, 120, 53, 40, 33]), readMed: R(300, 1500), precise: R(4, 9),
});

class Sim {
  t = R(300, 900);              // ms since page load
  x = R(100, VW - 100); y = R(100, VH - 100); // true (sub-pixel) hand position
  lastEmit = { x: -1, y: -1 };
  ev: Ev[] = [];
  frame0 = R(0, 16);
  ou = { x: 0, y: 0 };
  tremPh = [R(0, 6.28), R(0, 6.28)];
  constructor(public p: Person) {}

  q(t: number) { return Math.round(t * 10) / 10; }
  /** Browser-visible timestamp for something that happened at true time `t` and was delivered at the next frame. */
  nextFrame(t: number) { const f = this.p.frame; return this.frame0 + Math.ceil((t - this.frame0) / f) * f; }

  /** Drive the hand along pos(τ) for `dur` ms; emit coalesced mousemoves at frame boundaries. */
  move(pos: (tau: number) => [number, number], dur: number) {
    const p = this.p, t0 = this.t;
    let ft = this.nextFrame(t0 + 0.01);
    while (ft <= t0 + dur + 1e-6) {
      if (rnd() < 0.02) { ft += p.frame; continue; }          // dropped frame
      if (rnd() < 0.005) ft += R(15, 45);                        // long task
      // event timestamp = last OS poll before this frame
      const pollT = Math.floor((ft - R(0, 0.3)) / p.poll) * p.poll + R(0, 0.15);
      const tt = Math.min(Math.max(pollT, t0), t0 + dur);
      const [bx, by] = pos(Math.min(1, (tt - t0) / Math.max(dur, 1)));
      const [nx, ny] = this.noise(tt);
      this.x = bx; this.y = by;
      this.emitMove(tt, bx + nx, by + ny);
      ft += p.frame + gauss() * 0.15;
    }
    this.t = t0 + dur;
  }
  noise(t: number): [number, number] {
    const p = this.p, s = t / 1000;
    this.ou.x += -this.ou.x * 0.05 + gauss() * p.drift * 0.15;
    this.ou.y += -this.ou.y * 0.05 + gauss() * p.drift * 0.15;
    return [p.tremA * Math.sin(2 * Math.PI * p.tremF * s + this.tremPh[0]) + this.ou.x, p.tremA * Math.sin(2 * Math.PI * (p.tremF * 1.07) * s + this.tremPh[1]) + this.ou.y];
  }
  emitMove(t: number, x: number, y: number) {
    const ix = Math.round(Math.min(VW - 1, Math.max(0, x))), iy = Math.round(Math.min(VH - 1, Math.max(0, y)));
    if (ix === this.lastEmit.x && iy === this.lastEmit.y) return;
    this.lastEmit = { x: ix, y: iy };
    this.ev.push({ k: 'm', t: this.q(t), x: ix, y: iy, tr: 1 });
  }
  /** Hold still-ish (tremor + drift only) for `dur` ms. */
  hold(dur: number) { const x = this.x, y = this.y; this.move(() => [x, y], dur); }

  profile(sigma: number): (tau: number) => number {
    if (rnd() < this.p.profile) {
      return (tau) => tau * tau * tau * (10 - 15 * tau + 6 * tau * tau); // minimum jerk
    }
    const mu = -2.6 * sigma; // lognormal on normalised time: ~99.5% complete at tau=1
    const t0 = -0.05;
    return (tau) => { const tt = tau - t0; if (tt <= 0) return 0; return Math.min(1, 0.5 * (1 + erf((Math.log(tt / (1 - t0)) - mu) / (sigma * Math.SQRT2)))); };
  }
  submove(tx: number, ty: number, dur: number, arc: number) {
    const ax = this.x, ay = this.y, dx = tx - ax, dy = ty - ay, D = Math.hypot(dx, dy);
    const nx = -dy / (D || 1), ny = dx / (D || 1);
    const s = this.profile(R(0.18, 0.45));
    const h2 = gauss() * 0.02;
    this.move((tau) => {
      const u = s(tau);
      const off = (arc * Math.sin(Math.PI * u) + h2 * Math.sin(2 * Math.PI * u)) * D;
      return [ax + dx * u + nx * off, ay + dy * u + ny * off];
    }, dur);
  }
  /** Aimed pointing to a target rect (cx,cy,w,h) following Fitts + Meyer's optimised submovements. */
  pointTo(cx: number, cy: number, w: number, h: number) {
    const p = this.p;
    const tx = cx + Math.max(-w / 2 + 2, Math.min(w / 2 - 2, gauss() * w / p.precise));
    const ty = cy + Math.max(-h / 2 + 2, Math.min(h / 2 - 2, gauss() * h / p.precise));
    const D = Math.hypot(tx - this.x, ty - this.y);
    if (D < 3) return { tx, ty };
    const W = Math.min(w, h * 2);
    const MT = (p.fa + p.fb * Math.log2(D / W + 1)) * 1000 * logn(1, 0.15);
    const over = rnd() < p.overshoot ? R(1.02, 1.12) : R(0.88, 1.0);
    const ux = (tx - this.x) / D, uy = (ty - this.y) / D;
    const ex = this.x + ux * D * over + gauss() * 0.025 * D * -uy;
    const ey = this.y + uy * D * over + gauss() * 0.025 * D * ux;
    this.submove(ex, ey, MT * R(0.65, 0.8), p.arcMu + gauss() * p.arcSd);
    let err = Math.hypot(tx - this.x, ty - this.y);
    for (let k = 0; k < 2 && err > 1.5; k++) {
      if (rnd() < 0.5) this.hold(R(10, 60));
      this.submove(tx + gauss() * err * 0.15, ty + gauss() * err * 0.15, (60 + 70 * Math.log2(err / 4 + 1)) * logn(1, 0.2), gauss() * 0.08);
      err = Math.hypot(tx - this.x, ty - this.y);
    }
    return { tx: this.x, ty: this.y };
  }
  click(cx: number, cy: number, w: number, h: number) {
    this.pointTo(cx, cy, w, h);
    this.hold(logn(this.p.dwellMed, 0.5));
    const rect = { cx, cy, w, h };
    const pos = () => ({ x: Math.round(this.x), y: Math.round(this.y) });
    this.ev.push({ k: 'd', t: this.q(this.t + R(0, 1)), ...pos(), tr: 1, ...rect });
    this.hold(Math.max(25, logn(this.p.pressMed, this.p.pressSd)));
    const ut = this.q(this.t + R(0, 1));
    this.ev.push({ k: 'u', t: ut, ...pos(), tr: 1, ...rect });
    this.ev.push({ k: 'c', t: this.q(ut + R(0.1, 1.5)), ...pos(), tr: 1, ...rect });
  }
  type(text: string) {
    const p = this.p;
    const keys: string[] = [];
    for (const ch of text) {
      if (rnd() < p.errRate) keys.push('KeyQ', 'Backspace');
      keys.push(ch === ' ' ? 'Space' : ch === '.' ? 'Period' : ch === '@' ? 'Digit2' : /\d/.test(ch) ? 'Digit' + ch : 'Key' + ch.toUpperCase());
    }
    let t = this.t + logn(250, 0.4);
    let prev = '';
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i];
      const big = (prev + k.slice(-1)).toLowerCase().slice(-2);
      let iki = logn(p.ikiMed, p.ikiSd);
      if (COMMON.has(big)) iki *= R(0.55, 0.8);
      if (k === 'Space' || prev === 'Space') iki *= R(1.0, 1.6);
      if (k === 'Backspace') iki += logn(200, 0.5);
      if (rnd() < 0.04) iki += logn(600, 0.6); // thinking pause
      if (i) t += Math.max(25, Math.min(iki, 2500));
      const kd = this.q(t);
      const hold = Math.max(20, logn(p.holdMed, p.holdSd));
      this.ev.push({ k: 'kd', t: kd, tr: 1, kc: k });
      this.ev.push({ k: 'i', t: this.q(kd + R(0.2, 2)), tr: 1 });
      this.ev.push({ k: 'ku', t: this.q(kd + hold), tr: 1, kc: k }); // rollover happens naturally when hold > next iki
      prev = k.replace(/^Key/, '').toLowerCase();
    }
    // the hand is mostly off the mouse while typing; occasional tiny bumps
    const dur = t + 100 - this.t;
    if (rnd() < 0.3) this.hold(dur); else this.t += dur;
  }
  scroll() {
    const p = this.p, dir = rnd() < 0.8 ? 1 : -1;
    let t = this.t;
    if (p.wheel === 'notch') {
      const bursts = RI(1, 3);
      for (let b = 0; b < bursts; b++) {
        const n = RI(1, 7);
        for (let i = 0; i < n; i++) {
          t += i ? logn(R(35, 90), 0.45) : 0;
          this.ev.push({ k: 'w', t: this.q(t), dy: dir * p.notch, tr: 1 });
          // smooth-scroll animation: scroll events on following frames for ~120-200 ms
          let st = this.nextFrame(t + 1), end = t + R(120, 200);
          while (st < end) { this.ev.push({ k: 's', t: this.q(st), dy: dir * R(5, 30), tr: 1 }); st += p.frame; }
        }
        t += logn(400, 0.6);
      }
    } else {
      const n = RI(8, 40);
      let v = R(8, 40);
      for (let i = 0; i < n; i++) {
        t = this.nextFrame(t + 1) + R(0, 2);
        const ramp = i < 3 ? (i + 1) / 3 : Math.exp(-(i - 3) * R(0.05, 0.15));
        const dy = Math.round(dir * Math.max(1, v * ramp + gauss() * 2));
        this.ev.push({ k: 'w', t: this.q(t), dy, tr: 1 });
        this.ev.push({ k: 's', t: this.q(this.nextFrame(t + 0.5)), dy, tr: 1 });
      }
      v = 0;
    }
    if (rnd() < 0.4) this.hold(t - this.t + 50); else this.t = t + 50;
  }
  idle() {
    const dur = logn(this.p.readMed, 0.7);
    if (rnd() < 0.4) {
      // drift the cursor somewhere while reading
      const tx = Math.min(VW - 20, Math.max(20, this.x + gauss() * 150)), ty = Math.min(VH - 20, Math.max(20, this.y + gauss() * 100));
      this.hold(dur * 0.4);
      this.submove(tx, ty, R(300, 900), gauss() * 0.15);
      this.hold(dur * 0.3);
    } else this.t += dur;
  }
}

function target() {
  const w = R(60, 200), h = rnd() < 0.8 ? 44 : R(24, 60);
  return { cx: R(w / 2 + 20, VW - w / 2 - 20), cy: R(h / 2 + 20, VH - h / 2 - 20), w, h };
}

function session() {
  const p = person();
  const s = new Sim(p);
  const tEnd = R(8000, 20000);
  let field = { cx: R(340, 400), cy: R(300, 650), w: 640, h: 44 };
  while (s.t < tEnd) {
    const r = rnd();
    if (r < 0.45) { const g = target(); s.click(g.cx, g.cy, g.w, g.h); }
    else if (r < 0.65) { s.click(field.cx, field.cy, field.w, field.h); s.type(pick(SENTS)); }
    else if (r < 0.85) { s.scroll(); field = { ...field, cy: R(100, 700) }; }
    else s.idle();
    if (rnd() < 0.5) s.hold(logn(150, 0.8));
  }
  s.ev.sort((a, b) => a.t - b.t);
  return { label: 'human', style: 'synthetic', synthetic: true, events: s.ev };
}

const N = +arg('n', '1500');
const out = join(import.meta.dirname, 'sessions', 'human');
mkdirSync(out, { recursive: true });
const lines: string[] = [];
for (let i = 0; i < N; i++) lines.push(JSON.stringify(session()));
writeFileSync(join(out, `synthetic-seed${arg('seed', '1')}.jsonl`), lines.join('\n'));
console.log('wrote', N, 'synthetic human sessions');

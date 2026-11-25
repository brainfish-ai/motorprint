import type { Ev } from './types';

export const FEATURE_NAMES = [
  'has_mouse', 'n_moves', 'speed_mean', 'speed_cv', 'accel_mean', 'jerk_mean',
  'straightness', 'max_dev', 'peak_pos', 'end_speed_ratio',
  'turn_mean', 'turn_entropy', 'turn_zero_frac', 'step_cv',
  'dt_mean', 'dt_cv', 'dt_mode_share', 'dt_sub4_frac', 'pause_frac',
  'has_click', 'click_offset', 'press_ms', 'press_cv', 'moves_before_press', 'still_before_press', 'click_no_press_frac',
  'has_keys', 'iki_mean', 'iki_cv', 'hold_ms', 'hold_cv', 'input_no_key_frac',
  'has_scroll', 'wheel_dy_cv', 'wheel_dt_cv', 'scroll_no_input_frac',
  'untrusted_frac', 'event_rate',
] as const;

export const N_FEATURES = FEATURE_NAMES.length;

const L = (v: number) => Math.log1p(Math.max(0, v));

function mean(a: number[]): number {
  if (!a.length) return 0;
  let s = 0;
  for (const v of a) s += v;
  return s / a.length;
}
function std(a: number[], m = mean(a)): number {
  if (a.length < 2) return 0;
  let s = 0;
  for (const v of a) s += (v - m) * (v - m);
  return Math.sqrt(s / (a.length - 1));
}
function cv(a: number[]): number {
  const m = mean(a);
  return m > 1e-9 ? Math.min(5, std(a, m) / m) : 0;
}
function median(a: number[]): number {
  if (!a.length) return 0;
  const s = [...a].sort((p, q) => p - q);
  const h = s.length >> 1;
  return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2;
}

const PAUSE_MS = 120;
const SEG_GAP_MS = 150;

/**
 * Turn a window of events into a fixed-length feature vector.
 * Pure function, shared by training (Node) and inference (browser).
 */
export function extractFeatures(evsIn: Ev[], windowMs = 3000): number[] {
  const f = new Array<number>(N_FEATURES).fill(0);
  if (!evsIn.length) return f;
  // Quantise to 1 ms: browsers differ (Chrome 0.1 ms / 5 us, Firefox and Safari 1 ms) and so do datasets.
  const evs = evsIn.map((e) => (e.t % 1 === 0 ? e : { ...e, t: Math.round(e.t) }));
  const set = (name: (typeof FEATURE_NAMES)[number], v: number) => {
    f[FEATURE_NAMES.indexOf(name)] = Number.isFinite(v) ? v : 0;
  };

  // ---------- mouse movement ----------
  const mv = evs.filter((e) => e.k === 'm' && e.x !== undefined);
  if (mv.length >= 3) {
    set('has_mouse', 1);
    set('n_moves', L(mv.length));
    const dts: number[] = [], speeds: number[] = [], accs: number[] = [], jerks: number[] = [];
    const steps: number[] = [], turns: number[] = [];
    let pauses = 0, prevV = NaN, prevA = NaN, prevDt = NaN, prevAng = NaN;
    for (let i = 1; i < mv.length; i++) {
      const dt = mv[i].t - mv[i - 1].t;
      const dx = mv[i].x! - mv[i - 1].x!, dy = mv[i].y! - mv[i - 1].y!;
      const d = Math.hypot(dx, dy);
      if (dt > PAUSE_MS) { pauses++; prevV = prevA = prevAng = NaN; continue; }
      dts.push(dt);
      if (d > 0) steps.push(d);
      if (dt <= 0) continue;
      const v = d / dt;
      speeds.push(v);
      if (!Number.isNaN(prevV)) {
        const a = (v - prevV) / ((dt + prevDt) / 2);
        accs.push(Math.abs(a));
        if (!Number.isNaN(prevA)) jerks.push(Math.abs((a - prevA) / ((dt + prevDt) / 2)));
        prevA = a;
      }
      prevV = v; prevDt = dt;
      if (d > 0.5) {
        const ang = Math.atan2(dy, dx);
        if (!Number.isNaN(prevAng)) {
          let da = ang - prevAng;
          while (da > Math.PI) da -= 2 * Math.PI;
          while (da < -Math.PI) da += 2 * Math.PI;
          turns.push(da);
        }
        prevAng = ang;
      }
    }
    set('speed_mean', L(mean(speeds)));
    set('speed_cv', cv(speeds));
    set('accel_mean', L(mean(accs) * 100));
    set('jerk_mean', L(mean(jerks) * 1000));
    set('step_cv', cv(steps));
    if (turns.length) {
      const abs = turns.map(Math.abs);
      set('turn_mean', mean(abs));
      set('turn_zero_frac', abs.filter((v) => v < 0.02).length / abs.length);
      const bins = new Array(8).fill(0);
      for (const t of turns) bins[Math.min(7, Math.floor(((t + Math.PI) / (2 * Math.PI)) * 8))]++;
      let H = 0;
      for (const b of bins) if (b) { const p = b / turns.length; H -= p * Math.log2(p); }
      set('turn_entropy', H / 3);
    }
    if (dts.length) {
      set('dt_mean', L(mean(dts)));
      set('dt_cv', cv(dts));
      const med = median(dts);
      set('dt_mode_share', dts.filter((d) => Math.abs(d - med) <= 0.5).length / dts.length);
      set('dt_sub4_frac', dts.filter((d) => d < 4).length / dts.length);
    }
    set('pause_frac', pauses / (mv.length - 1));

    // segments split by pauses or button presses
    const presses = evs.filter((e) => e.k === 'd' || e.k === 'u').map((e) => e.t);
    const segs: Ev[][] = [];
    let cur: Ev[] = [mv[0]];
    let pi = 0;
    for (let i = 1; i < mv.length; i++) {
      let split = mv[i].t - mv[i - 1].t > SEG_GAP_MS;
      while (pi < presses.length && presses[pi] <= mv[i].t) { if (presses[pi] > mv[i - 1].t) split = true; pi++; }
      if (split) { segs.push(cur); cur = []; }
      cur.push(mv[i]);
    }
    segs.push(cur);
    const straight: number[] = [], devs: number[] = [], peaks: number[] = [], ends: number[] = [];
    for (const s of segs) {
      if (s.length < 4) continue;
      let path = 0;
      const sp: number[] = [];
      for (let i = 1; i < s.length; i++) {
        const d = Math.hypot(s[i].x! - s[i - 1].x!, s[i].y! - s[i - 1].y!);
        path += d;
        sp.push(d / Math.max(1, s[i].t - s[i - 1].t));
      }
      if (path < 20) continue;
      const cx = s[s.length - 1].x! - s[0].x!, cy = s[s.length - 1].y! - s[0].y!;
      const chord = Math.hypot(cx, cy);
      straight.push(chord / path);
      let md = 0;
      if (chord > 1) for (const p of s) md = Math.max(md, Math.abs((p.x! - s[0].x!) * cy - (p.y! - s[0].y!) * cx) / chord);
      devs.push(Math.min(1, md / Math.max(chord, 1)));
      const dur = s[s.length - 1].t - s[0].t;
      let pk = 0;
      for (let i = 1; i < sp.length; i++) if (sp[i] > sp[pk]) pk = i;
      peaks.push(dur > 0 ? (s[pk + 1].t - s[0].t) / dur : 0.5);
      const tail = sp.slice(Math.floor(sp.length * 0.8));
      ends.push(sp[pk] > 0 ? Math.min(1.5, mean(tail) / sp[pk]) : 0);
    }
    if (straight.length) {
      set('straightness', mean(straight));
      set('max_dev', mean(devs));
      set('peak_pos', mean(peaks));
      set('end_speed_ratio', mean(ends));
    } else {
      set('straightness', 1);
      set('peak_pos', 0.5);
    }
  }

  // ---------- clicks ----------
  const downs = evs.filter((e) => e.k === 'd');
  const ups = evs.filter((e) => e.k === 'u');
  const clicks = evs.filter((e) => e.k === 'c');
  if (downs.length || clicks.length) {
    set('has_click', 1);
    const offs: number[] = [], press: number[] = [], before: number[] = [], still: number[] = [];
    for (const d of downs) {
      if (d.w && d.h && d.cx !== undefined && d.x !== undefined) {
        offs.push(Math.min(2, Math.hypot(d.x - d.cx, d.y! - d.cy!) / Math.hypot(d.w / 2, d.h / 2)));
      }
      const u = ups.find((e) => e.t >= d.t);
      if (u && u.t - d.t < 2000) press.push(u.t - d.t);
      let n = 0, last = -Infinity;
      for (const m of mv) {
        if (m.t > d.t) break;
        if (d.t - m.t <= 300) n++;
        last = m.t;
      }
      before.push(n);
      still.push(Math.min(2000, d.t - last));
    }
    set('click_offset', offs.length ? mean(offs) : 0);
    set('press_ms', L(mean(press)));
    set('press_cv', cv(press));
    set('moves_before_press', L(mean(before)));
    set('still_before_press', L(mean(still)));
    const noPress = clicks.filter((c) => !downs.some((d) => c.t - d.t >= 0 && c.t - d.t < 2000)).length;
    set('click_no_press_frac', clicks.length ? noPress / clicks.length : 0);
  }

  // ---------- keys ----------
  const kds = evs.filter((e) => e.k === 'kd');
  const kus = evs.filter((e) => e.k === 'ku');
  const inputs = evs.filter((e) => e.k === 'i');
  if (kds.length || inputs.length) {
    set('has_keys', 1);
    const iki: number[] = [];
    for (let i = 1; i < kds.length; i++) iki.push(Math.min(1500, kds[i].t - kds[i - 1].t));
    set('iki_mean', L(mean(iki)));
    set('iki_cv', cv(iki));
    const holds: number[] = [];
    for (const d of kds) {
      const u = kus.find((e) => e.t >= d.t && e.kc === d.kc);
      if (u && u.t - d.t < 1500) holds.push(u.t - d.t);
    }
    set('hold_ms', L(mean(holds)));
    set('hold_cv', cv(holds));
    const nk = inputs.filter((ie) => !kds.some((d) => ie.t - d.t >= 0 && ie.t - d.t < 60)).length;
    set('input_no_key_frac', inputs.length ? nk / inputs.length : 0);
  }

  // ---------- scroll ----------
  const wheels = evs.filter((e) => e.k === 'w');
  const scrolls = evs.filter((e) => e.k === 's');
  if (wheels.length || scrolls.length) {
    set('has_scroll', 1);
    set('wheel_dy_cv', cv(wheels.map((w) => Math.abs(w.dy ?? 0))));
    const wdt: number[] = [];
    for (let i = 1; i < wheels.length; i++) { const d = wheels[i].t - wheels[i - 1].t; if (d < 400) wdt.push(d); }
    set('wheel_dt_cv', cv(wdt));
    const causes = evs.filter((e) => e.k === 'w' || e.k === 'kd' || e.k === 'd' || e.k === 'm');
    const noInput = scrolls.filter((s) => !causes.some((c) => s.t - c.t >= 0 && s.t - c.t < 800)).length;
    set('scroll_no_input_frac', scrolls.length ? noInput / scrolls.length : 0);
  }

  // ---------- global ----------
  set('untrusted_frac', evs.filter((e) => e.tr === 0).length / evs.length);
  set('event_rate', L(evs.length / (windowMs / 1000)));
  return f;
}

/** Slice events that fall inside (tEnd - windowMs, tEnd]. Assumes sorted by t. */
export function windowAt(evs: Ev[], tEnd: number, windowMs = 3000): Ev[] {
  const out: Ev[] = [];
  for (const e of evs) if (e.t > tEnd - windowMs && e.t <= tEnd) out.push(e);
  return out;
}

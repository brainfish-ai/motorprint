import { extractFeatures, FEATURE_NAMES, windowAt } from './features';
import { createModel, type ModelSpec } from './model';
import { createRecorder, type Signals } from './recorder';
import type { Ev } from './types';
import { MODEL } from './weights';

export interface BotScore {
  /** Smoothed probability (0..1) that the current visitor is automated. */
  score: number;
  /** Score of the latest window alone. */
  raw: number;
  /** score >= threshold */
  isBot: boolean;
  threshold: number;
  /** Number of windows scored so far. More windows = more reliable. */
  windows: number;
  /** Events in the latest window. */
  events: number;
  /** Named feature values for the latest window (for debugging / display). */
  features: Record<string, number>;
  /** ms spent extracting features + running the model for the latest window. */
  inferenceMs: number;
  /** Provenance tells seen so far (see Signals). Any non-zero count sets isBot regardless of the motion score. */
  signals: Signals;
  /** Why isBot is true: 'motion' and/or the names of the provenance signals that fired. */
  reasons: string[];
}

export interface BotDetectorOptions {
  onScore?: (s: BotScore) => void;
  /** How often to score, ms. Default 500. */
  intervalMs?: number;
  /** Sliding window length, ms. Must match training (3000). */
  windowMs?: number;
  /** Minimum events in a window before scoring. Default 4. */
  minEvents?: number;
  /** EMA factor on log-odds, 0..1. Higher = more reactive. Default 0.35. */
  smoothing?: number;
  /** Override the bundled model. */
  model?: ModelSpec;
  root?: Document;
  /** Start listening immediately. Default true. */
  autoStart?: boolean;
  /** Let provenance signals (teleportClick, pressure0, keylessInsert) set isBot. Default true. */
  useSignals?: boolean;
}

export interface BotDetector {
  start(): void;
  stop(): void;
  reset(): void;
  /** Score the current window now (also called on every interval tick). */
  evaluate(): BotScore | null;
  readonly score: BotScore | null;
  readonly events: readonly Ev[];
}

const now = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());

/** Score raw events offline (e.g. a recorded session). Returns per-window scores. */
export function scoreEvents(events: Ev[], opts: { windowMs?: number; stepMs?: number; model?: ModelSpec } = {}) {
  const W = opts.windowMs ?? 3000, step = opts.stepMs ?? 750, m = createModel(opts.model ?? MODEL);
  const ev = [...events].sort((a, b) => a.t - b.t);
  const out: { t: number; score: number }[] = [];
  if (!ev.length) return out;
  for (let t = ev[0].t + Math.min(W, ev[ev.length - 1].t - ev[0].t); t <= ev[ev.length - 1].t + 1e-6; t += step) {
    const w = windowAt(ev, t, W);
    if (w.length >= 4) out.push({ t, score: m.predict(extractFeatures(w, W)) });
  }
  return out;
}

export function createBotDetector(opts: BotDetectorOptions = {}): BotDetector {
  const W = opts.windowMs ?? 3000;
  const minEv = opts.minEvents ?? 4;
  const alpha = opts.smoothing ?? 0.35;
  const model = createModel(opts.model ?? MODEL);
  const thr = model.spec.thr ?? 0.5;
  const rec = createRecorder({ maxAgeMs: W * 2, root: opts.root });
  let timer: ReturnType<typeof setInterval> | undefined;
  let logit: number | null = null;
  let windows = 0;
  let lastSig = '';
  let current: BotScore | null = null;

  const evaluate = (): BotScore | null => {
    const evs = rec.events;
    if (!evs.length) return current;
    const tEnd = Math.max(evs[evs.length - 1].t, now());
    const w = windowAt(evs, tEnd, W);
    if (w.length < minEv) return current;
    // skip if nothing new happened since the last scored window
    const sig = `${w.length}:${w[w.length - 1].t}`;
    if (sig === lastSig) return current;
    lastSig = sig;
    const t0 = now();
    const f = extractFeatures(w, W);
    const raw = model.predict(f);
    const inferenceMs = now() - t0;
    const l = Math.log(Math.max(1e-6, raw) / Math.max(1e-6, 1 - raw));
    logit = logit === null ? l : logit + alpha * (l - logit);
    windows++;
    const score = 1 / (1 + Math.exp(-logit));
    const features: Record<string, number> = {};
    FEATURE_NAMES.forEach((n, i) => (features[n] = f[i]));
    const signals = { ...rec.signals };
    const reasons = (opts.useSignals === false ? [] : (Object.keys(signals) as (keyof Signals)[]).filter((k) => signals[k] > 0)) as string[];
    if (score >= thr) reasons.unshift('motion');
    current = { score, raw, isBot: reasons.length > 0, threshold: thr, windows, events: w.length, features, inferenceMs, signals, reasons };
    opts.onScore?.(current);
    return current;
  };

  const det: BotDetector = {
    start() {
      if (timer) return;
      rec.start();
      timer = setInterval(evaluate, opts.intervalMs ?? 500);
    },
    stop() {
      rec.stop();
      if (timer) clearInterval(timer);
      timer = undefined;
    },
    reset() {
      rec.clear();
      logit = null; windows = 0; current = null; lastSig = '';
    },
    evaluate,
    get score() { return current; },
    get events() { return rec.events; },
  };
  if (opts.autoStart !== false && typeof document !== 'undefined') det.start();
  return det;
}

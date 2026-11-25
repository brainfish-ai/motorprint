import type { Ev } from './types';

const TARGET_SEL = 'button,a,input,textarea,select,label,summary,[role="button"],[role="link"],[data-hl-target]';

export interface RecorderOptions {
  /** Drop events older than this (ms). Default 10000. Use Infinity to keep all (for collection). */
  maxAgeMs?: number;
  /** Called for every recorded event. */
  onEvent?: (e: Ev) => void;
  root?: Document;
}

/** Sticky provenance evidence (counts since start/clear). Each is a hard tell of injected input, not a score. */
export interface Signals {
  /** mousedown with exactly one mousemove in the previous 1 s, <= 30 ms before it, and mouseup < 5 ms later (scripted move-press-release) */
  teleportClick: number;
  /** pointerdown from a 'mouse' with pressure 0 (spec: 0.5 while a button is down; CDP without `force` sends 0) */
  pressure0: number;
  /** beforeinput 'insertText' with no keydown in the previous 100 ms (CDP Input.insertText / fill) */
  keylessInsert: number;
}

export interface Recorder {
  readonly events: Ev[];
  readonly signals: Signals;
  start(): void;
  stop(): void;
  clear(): void;
}

/** Records the low-level input stream. Nothing leaves the page. Key characters are never stored. */
export function createRecorder(opts: RecorderOptions = {}): Recorder {
  const maxAge = opts.maxAgeMs ?? 10000;
  const doc = opts.root ?? document;
  const win = doc.defaultView ?? window;
  const events: Ev[] = [];
  const signals: Signals = { teleportClick: 0, pressure0: 0, keylessInsert: 0 };
  let lastScrollY = 0, lastKd = -1e9;

  const push = (e: Ev) => {
    events.push(e);
    if (maxAge !== Infinity) {
      const cut = e.t - maxAge;
      let i = 0;
      while (i < events.length && events[i].t < cut) i++;
      if (i) events.splice(0, i);
    }
    opts.onEvent?.(e);
  };
  const tr = (e: Event): 0 | 1 => (e.isTrusted ? 1 : 0);
  const rect = (e: Event) => {
    const el = e.target as Element | null;
    const t = (el && typeof el.closest === 'function' && el.closest(TARGET_SEL)) || el;
    if (!t || typeof (t as Element).getBoundingClientRect !== 'function') return {};
    const r = (t as Element).getBoundingClientRect();
    return { cx: r.left + r.width / 2, cy: r.top + r.height / 2, w: r.width, h: r.height };
  };

  const onMove = (e: MouseEvent) => push({ k: 'm', t: e.timeStamp, x: e.clientX, y: e.clientY, tr: tr(e) });
  const onDown = (e: MouseEvent) => push({ k: 'd', t: e.timeStamp, x: e.clientX, y: e.clientY, tr: tr(e), ...rect(e) });
  const onUp = (e: MouseEvent) => {
    // teleport click: find the last press; count moves in the second before it
    let d: Ev | undefined, n = 0, lastM = -1e9;
    for (let i = events.length - 1; i >= 0; i--) { if (events[i].k === 'd') { d = events[i]; break; } }
    if (d && e.timeStamp - d.t < 5) {
      for (const v of events) if (v.k === 'm' && v.t <= d.t && v.t >= d.t - 1000) { n++; lastM = v.t; }
      if (n === 1 && d.t - lastM <= 30) signals.teleportClick++;
    }
    push({ k: 'u', t: e.timeStamp, x: e.clientX, y: e.clientY, tr: tr(e), ...rect(e) });
  };
  const onPDown = (e: PointerEvent) => { if (e.pointerType === 'mouse' && e.pressure === 0) signals.pressure0++; };
  const onBefore = (e: InputEvent) => { if (e.inputType === 'insertText' && e.timeStamp - lastKd > 100) signals.keylessInsert++; };
  const onClick = (e: MouseEvent) => push({ k: 'c', t: e.timeStamp, x: e.clientX, y: e.clientY, tr: tr(e), ...rect(e) });
  const onKd = (e: KeyboardEvent) => (lastKd = e.timeStamp, push({ k: 'kd', t: e.timeStamp, tr: tr(e), kc: e.code || 'x' }));
  const onKu = (e: KeyboardEvent) => push({ k: 'ku', t: e.timeStamp, tr: tr(e), kc: e.code || 'x' });
  const onInput = (e: Event) => push({ k: 'i', t: e.timeStamp, tr: tr(e) });
  const onWheel = (e: WheelEvent) => push({ k: 'w', t: e.timeStamp, dy: e.deltaY, tr: tr(e) });
  const onScroll = (e: Event) => {
    const y = win.scrollY;
    push({ k: 's', t: e.timeStamp, dy: y - lastScrollY, tr: tr(e) });
    lastScrollY = y;
  };

  const L: [string, (e: never) => void][] = [
    ['mousemove', onMove], ['mousedown', onDown], ['mouseup', onUp], ['click', onClick],
    ['keydown', onKd], ['keyup', onKu], ['input', onInput], ['wheel', onWheel], ['pointerdown', onPDown], ['beforeinput', onBefore],
  ];
  const o = { capture: true, passive: true } as const;
  return {
    events,
    signals,
    start() {
      lastScrollY = win.scrollY;
      for (const [n, h] of L) doc.addEventListener(n, h as EventListener, o);
      win.addEventListener('scroll', onScroll, o);
    },
    stop() {
      for (const [n, h] of L) doc.removeEventListener(n, h as EventListener, o);
      win.removeEventListener('scroll', onScroll, o);
    },
    clear() { events.length = 0; signals.teleportClick = signals.pressure0 = signals.keylessInsert = 0; },
  };
}

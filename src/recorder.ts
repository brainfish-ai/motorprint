import type { Ev } from './types';

const TARGET_SEL = 'button,a,input,textarea,select,label,summary,[role="button"],[role="link"],[data-hl-target]';

export interface RecorderOptions {
  /** Drop events older than this (ms). Default 10000. Use Infinity to keep all (for collection). */
  maxAgeMs?: number;
  /** Called for every recorded event. */
  onEvent?: (e: Ev) => void;
  root?: Document;
}

export interface Recorder {
  readonly events: Ev[];
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
  let lastScrollY = 0;

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
  const onUp = (e: MouseEvent) => push({ k: 'u', t: e.timeStamp, x: e.clientX, y: e.clientY, tr: tr(e), ...rect(e) });
  const onClick = (e: MouseEvent) => push({ k: 'c', t: e.timeStamp, x: e.clientX, y: e.clientY, tr: tr(e), ...rect(e) });
  const onKd = (e: KeyboardEvent) => push({ k: 'kd', t: e.timeStamp, tr: tr(e), kc: e.code || 'x' });
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
    ['keydown', onKd], ['keyup', onKu], ['input', onInput], ['wheel', onWheel],
  ];
  const o = { capture: true, passive: true } as const;
  return {
    events,
    start() {
      lastScrollY = win.scrollY;
      for (const [n, h] of L) doc.addEventListener(n, h as EventListener, o);
      win.addEventListener('scroll', onScroll, o);
    },
    stop() {
      for (const [n, h] of L) doc.removeEventListener(n, h as EventListener, o);
      win.removeEventListener('scroll', onScroll, o);
    },
    clear() { events.length = 0; },
  };
}

/** Compact event record. All times are ms (performance.now / event.timeStamp). */
export type EvKind =
  | 'm'  // mousemove
  | 'd'  // mousedown
  | 'u'  // mouseup
  | 'c'  // click
  | 'kd' // keydown
  | 'ku' // keyup
  | 'i'  // input (value changed)
  | 'w'  // wheel
  | 's'; // scroll (document scrolled, from any cause)

export interface Ev {
  k: EvKind;
  t: number;
  x?: number;
  y?: number;
  /** isTrusted: 1 = real browser input (or CDP), 0 = dispatched by script */
  tr?: 0 | 1;
  /** target rect centre and size for d/u/c */
  cx?: number;
  cy?: number;
  w?: number;
  h?: number;
  /** wheel / scroll delta */
  dy?: number;
  /** key code (for matching keydown/keyup); never the typed character */
  kc?: string;
}

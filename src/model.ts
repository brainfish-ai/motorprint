/** Tiny MLP runtime. Weights can be stored as float32, int8 or packed int4 (base64), with per-row scales. */
export interface LayerSpec {
  /** inputs, outputs */
  i: number;
  o: number;
  /** 32 = float32, 8 = int8, 4 = packed int4 (two's complement nibbles) */
  bits: 32 | 8 | 4;
  /** per-output-row scales (ignored for float32) */
  s?: number[];
  /** base64 weights, row-major [o][i] */
  w: string;
  b: number[];
}
export interface ModelSpec {
  v: 1;
  names: readonly string[];
  mean: number[];
  std: number[];
  layers: LayerSpec[];
  /** decision threshold on the 0..1 score */
  thr?: number;
  /** feature indices the model was trained without (they are neutralised at inference) */
  off?: number[];
}

function b64(s: string): Uint8Array {
  const bin = atob(s);
  const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u;
}

function decode(l: LayerSpec): Float32Array {
  const n = l.i * l.o, out = new Float32Array(n), raw = b64(l.w);
  if (l.bits === 32) return new Float32Array(raw.buffer, raw.byteOffset, n).slice();
  for (let k = 0; k < n; k++) {
    let q: number;
    if (l.bits === 8) q = (raw[k] << 24) >> 24;
    else { const nib = (raw[k >> 1] >> ((k & 1) * 4)) & 15; q = (nib << 28) >> 28; }
    out[k] = q * l.s![Math.floor(k / l.i)];
  }
  return out;
}

export interface Model {
  /** probability that the window was produced by automation */
  predict(x: ArrayLike<number>): number;
  spec: ModelSpec;
}

export function createModel(spec: ModelSpec): Model {
  const W = spec.layers.map(decode);
  const bufs = spec.layers.map((l) => new Float32Array(l.o));
  const z = new Float32Array(spec.mean.length);
  const off = new Set(spec.off ?? []);
  return {
    spec,
    predict(x) {
      for (let i = 0; i < z.length; i++) z[i] = off.has(i) ? 0 : Math.max(-6, Math.min(6, (x[i] - spec.mean[i]) / spec.std[i]));
      let inp: Float32Array = z;
      for (let li = 0; li < spec.layers.length; li++) {
        const l = spec.layers[li], w = W[li], out = bufs[li], last = li === spec.layers.length - 1;
        for (let o = 0; o < l.o; o++) {
          let a = l.b[o];
          const r = o * l.i;
          for (let i = 0; i < l.i; i++) a += w[r + i] * inp[i];
          out[o] = last ? a : a > 0 ? a : 0;
        }
        inp = out;
      }
      return 1 / (1 + Math.exp(-inp[0]));
    },
  };
}

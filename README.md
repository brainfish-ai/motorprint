# motorprint

**A tiny bot detector that runs on the device.** It reads how the pointer, clicks, scrolling and typing *move* (speed, jerk, curvature, timing rhythm), scores each 3 second window with a 165-weight int8 neural net, and returns a bot score from 0 to 1. It needs no server, no LLM and no network calls, and nothing leaves the tab.

- **4.7 KB gzipped** for the whole library (minified ESM, model included). The `motorprint/react` entry is 4.6 KB on its own, because it bundles the core it needs.
- **About 55 µs per window** in Node (feature extraction ~55 µs, model ~0.5 µs). It scores every 500 ms by default.
- Comes with a vanilla `createBotDetector({ onScore })` and a React `useBotScore()` hook.
- Inspired by Jakub Antalik's [mood-recognition](https://libraries.dev/mood-recognition), which uses the same idea (on-device motion features into a tiny model) to tell humans from automation.

> ⚠️ **The human training data is synthetic.** No real human sessions were available when this model was trained. Human sessions come from a motor-control simulator (see [Data](#data)). Before you rely on it in production, collect real sessions with `demo/collect.html` and retrain. The accuracy numbers below are measured on synthetic humans versus real Playwright bots, so treat them as a smoke test, not a production estimate.

## Install and use

```ts
import { createBotDetector } from 'motorprint';

const detector = createBotDetector({
  onScore: ({ score, isBot, windows }) => {
    // score: 0..1 smoothed over windows. Wait for a few windows before acting on it.
    if (windows >= 4 && isBot) markSessionSuspicious(score);
  },
});
// later: detector.stop()
```

```tsx
import { useBotScore } from 'motorprint/react';

function Checkout() {
  const bot = useBotScore();
  return <input type="hidden" name="motorprint" value={bot ? bot.score.toFixed(3) : ''} />;
}
```

Options: `intervalMs` (500), `windowMs` (3000, must match training), `minEvents` (4), `smoothing` (EMA on log-odds, 0.35), `model` (bring your own retrained spec), `autoStart` (true). `scoreEvents(events)` scores a recorded session offline. `createRecorder()` gives you the raw event stream.

`BotScore` = `{ score, raw, isBot, threshold, windows, events, features, inferenceMs }`. `threshold` is 0.696, calibrated for at most 0.5% false positives on validation humans.

## Demo

```bash
cd /workspace/bot-detect
export PATH=$HOME/.local/node22/bin:$PATH
npm install
npm run demo:dev                 # http://localhost:5173  (live gauge + feature readout; /collect.html records sessions)
# or the static build:
npm run demo:build && npm run demo:serve   # http://localhost:4173
npm run demo:bot                 # Playwright drives the built demo: a replayed human trace, then a scripted bot
```

`demo:bot` saves screenshots and a video to `../bot-detect-artifacts/`. In the last run the replayed human trace scored **0.00** and the scripted bot climbed to **0.99 after its first round and 1.00 by the end**.

## How it works

1. **Recorder** (`src/recorder.ts`) listens passively, in the capture phase, to `mousemove`, `mousedown/up`, `click`, `keydown/up` (it stores the key *code* only, never the text), `input`, `wheel` and `scroll`. It keeps about 6 s of events.
2. **Features** (`src/features.ts`, 38 per window). These include speed, acceleration and jerk; straightness and maximum lateral deviation of each movement segment; where the speed peaks and how much it slows at the end; turn-angle mean, entropy and the share of zero turns; step regularity; event timestamp regularity (interval CV, mode share, sub-4 ms bursts); pause share; click offset from the target centre; press duration and its CV; movement just before a press; clicks without a press; inter-key interval and hold time with their CVs; input with no keypress; wheel delta and timing regularity; scroll with no input; the untrusted-event share; and event rate.
3. **Model** (`src/model.ts`, `src/weights.ts`). It's a 38 → 8 → 1 ReLU MLP with 50% of its weights pruned and per-row int8 weights stored as base64. The runtime is 50 lines of TypeScript.
4. **Smoothing.** An EMA over window log-odds, so a single odd window does not flip the verdict.

## Data

| set | how | sessions | windows |
|---|---|---|---|
| Bots (train styles) | Playwright against `demo/collect.html`, headless and headed (xvfb), real Chrome 156: **teleport** (`page.click`, instant type, fixed wheel), **linear** (`mouse.move` with steps, constant typing delay), **eased** (ease-in-out path, fixed 16 ms frames, fixed-delay typing), **bezier** (random cubic bezier, random waits, random point in element), **dom** (`el.click()`, `value=` + dispatched `input`, `window.scrollBy`) | 260 | 1,302 |
| Bots (held out, never trained on) | **ghost** (ghost-cursor style: Fitts-scaled bezier, overshoot, per-point jitter, gaussian key timing), **wind** (WindMouse physics), **agent** (AI-agent style: teleport to element, `fill()`, long thinking pauses, 500 px wheels) | 156 | 1,821 |
| Humans (**synthetic**) | `data/gen-humans.ts`: Fitts's-law timing, primary plus corrective submovements (Meyer 1988), minimum-jerk or sigma-lognormal velocity, per-person arc bias, endpoint scatter, 8 to 12 Hz tremor plus OU drift. It emulates the browser too: OS polling coalesced to 60 to 144 Hz frames, integer coordinates, 0.1 ms timestamps, dropped and long frames. Log-normal inter-key intervals with digraph bursts, word pauses, rollover and typos. Wheel notches with smooth-scroll, or trackpad momentum | 1,500 | 26,411 |
| Replay attack (eval only) | 30 *other* synthetic human sessions replayed through Playwright in real time | 30 | 405 |

Splits are by session (70/15/15). Held-out styles appear only at evaluation, where they are scored against the same held-out human test windows.

## Results (window level, shipped model)

| | baseline (float32, 16-8, 769 weights) | **shipped** (8 hidden, 50% pruned, int8, calibrated) |
|---|---|---|
| Test accuracy (train styles + synthetic humans) | 0.9958 | 0.9941 |
| Test ROC-AUC | 0.9999 | 0.9998 |
| Test confusion (TP / FN / FP / TN) | 314 / 0 / 17 / 3746 | 312 / 2 / 22 / 3741 |
| Held-out bot styles ROC-AUC | 0.9456 | 0.9498 |
| Flagged: ghost / wind / agent | 0.10 / 0.92 / 0.79 | 0.08 / 0.92 / 0.73 |
| Session-level accuracy: test / held-out | 1.000 / 0.845 | 1.000 / 0.834 |
| Replay attack flagged | 0.03 | 0.03 |
| Model gzipped | 3.87 KB | 1.08 KB |
| Library gzipped | 7.67 KB | **4.66 KB** |
| Inference per window (model / features + model) | 0.97 µs / ~57 µs | 0.47 µs / ~56 µs |

The full stage-by-stage table (sweep, soups, pruning, quantization, calibration) is in [`tune/REPORT.md`](tune/REPORT.md), and all 109 runs are in [`tune/RUNS.md`](tune/RUNS.md).

**What this says.** Classic automation (teleports, linear or eased moves, constant-rate typing, DOM events, programmatic scroll) is trivially separable from the synthetic humans. Physics-based WindMouse transfers well (92% of windows flagged) and so does agent-style behaviour (73 to 84%). A good humanizer (ghost-cursor style, with jitter, overshoot and gaussian timing) mostly gets through: only 8 to 20% of its windows are flagged. Replaying human traces gets through almost completely (3%).

## Limitations (please read)

- **It's a signal, not proof.** Use the score as one input to a risk decision (step-up challenge, rate limit, review), never as the only reason to block a person.
- **It can be beaten by replaying recorded human traces.** We measured this: replayed traces were flagged 3% of the time. Good humanizers (ghost-cursor style) also mostly pass. Anyone who can read this README can train against it.
- **The human data is synthetic.** Real people use trackpads, touchscreens, accessibility tools, voice input, password managers and autofill (which looks like `input` without keys), and they have tremors or motor impairments. None of this is in the training set yet. Expect a higher false-positive rate on real traffic until you retrain on real sessions, and make sure assistive technology users are never locked out.
- **The score is client-side, so it can be forged.** A bot can just report `score = 0`. Pair it with server checks: rate limits, IP and ASN reputation, TLS/JA4 fingerprints, proof of work or Turnstile-style challenges, and server-side verification of anything that matters.
- **Touch is not modelled.** Pointer events from touch devices are not used yet, so mobile sessions get fewer features (keys and scroll only).
- **Short sessions are weak.** Wait for a few windows (`windows >= 3` or 4) before trusting the score.

## Retraining

```bash
npm run data:humans    # synthetic humans  -> data/sessions/human/
npm run data:bots      # Playwright bots   -> data/sessions/bot/   (needs a demo server on :5173: npm run demo:dev)
npm run data:replay    # replay-attack eval set
npm run collect:server # optional: real sessions from /collect.html -> data/sessions-real/
npm run tune           # featurize + sweep + soups + pruning + int8/int4 + calibration, writes src/weights.ts
npm run build:lib
```

See [`tune/README.md`](tune/README.md) for details on the tuning pass.

## Privacy

Only timings, coordinates, key *codes* and element rectangles are kept in memory, for about 6 seconds. Nothing is persisted or transmitted by the library. The `/collect` page only saves when you press Download or Save.

## License

MIT

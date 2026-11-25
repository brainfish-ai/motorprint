# motorprint

**A tiny bot detector that runs on the device.** It reads how the pointer, clicks, scrolling and typing *move* (speed, jerk, curvature, timing rhythm), scores each 3 second window with a small int8 neural net (38 → 32 → 16 → 1, 80% pruned), and returns a bot score from 0 to 1. It needs no server, no LLM and no network calls, and nothing leaves the tab.

- **About 5.4 KB gzipped** for the whole library (minified ESM, model included).
- **About 85 µs per window** in Node (feature extraction is most of it; the model is ~2 µs). It scores every 500 ms by default.
- Comes with a vanilla `createBotDetector({ onScore })` and a React `useBotScore()` hook.
- Inspired by Jakub Antalik's [mood-recognition](https://libraries.dev/mood-recognition), which uses the same idea (on-device motion features into a tiny model) to tell humans from automation.

> **The human class is real people.** The model is trained on six openly licensed datasets of real mouse and keyboard recordings (421 people, 5,657 sessions; see [DATA.md](DATA.md)). They are **desktop/laptop recordings from research tasks, not browser traffic from your site, and contain no touch input.** False-positive rates below are measured on people the model never saw, but your users will differ. Collect your own sessions with `demo/collect.html` and check before relying on it.

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

`BotScore` = `{ score, raw, isBot, threshold, windows, events, features, inferenceMs }`. `threshold` is 0.5. Calibrating lower raised the false-positive rate on held-out real users, so it stays at 0.5 (see [`tune/REPORT.md`](tune/REPORT.md)).

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
3. **Model** (`src/model.ts`, `src/weights.ts`). It's a 38 → 32 → 16 → 1 ReLU MLP with 80% of its weights pruned (398 non-zero) and per-row int8 weights stored as base64. One unit was written by hand rather than trained ([WSP.md](WSP.md)). Two features (`click_offset`, `wheel_dy_cv`) are switched off (`off` in the spec) because no real-human dataset records target rectangles or wheel deltas. The runtime is about 50 lines of TypeScript.
4. **Smoothing.** An EMA over window log-odds, so a single odd window does not flip the verdict.

## Data

| set | source | users | sessions |
|---|---|---|---|
| Humans (**real**) | AdSERP, Freihaut & Göritz MouseTask, DUX, Bogazici mouse dynamics (mouse); KeyRecs, CMU keystroke benchmark (typing). All CC BY 4.0 except CMU ("freely available"). Converted to browser events and coalesced to 60/120/144 Hz frames like Chrome does; timestamps quantised to 1 ms. Details, citations and re-download commands: [DATA.md](DATA.md) | 421 | 5,657 |
| Bots (train styles) | Playwright against `demo/collect.html`, headless and headed (xvfb), real Chrome: **teleport**, **linear**, **eased**, **bezier**, **dom** (`el.click()`, `value=` + dispatched `input`, `window.scrollBy`) | | 460 |
| Bots (held out, never trained on) | **ghost** (ghost-cursor style: Fitts-scaled bezier, overshoot, per-point jitter, gaussian key timing), **wind** (WindMouse physics), **agent** (AI-agent style: teleport to element, `fill()`, long thinking pauses, 500 px wheels) | | 276 |
| Replay attack (eval only) | 30 synthetic human sessions replayed through Playwright in real time | | 30 |

Raw data is downloaded to `data/external/raw/` and is not committed. Real humans are split **by user** (70/15/15), so every number below is on people the model never saw. Bots are split by session. The old motor-control simulator (`data/gen-humans.ts`) is kept as an optional extra (`HUMANS=both`).

## Results (window level, held-out users, threshold 0.5)

| | old model (synthetic humans) | **shipped** (real humans, 32-16, 80% pruned, int8, + 1 hand-programmed unit) |
|---|---|---|
| False positives on held-out **real** users (3 s windows) | 16.2% | **0.33%** (82 of 25,168) |
| False positives, session level (majority of windows flagged) | 5.31% | **0.00%** of 904 sessions |
| Per dataset FPR: adserp / boun / dux / mousetask / keyrecs / cmu | 26.8 / 47.0 / 35.2 / 11.2 / 0.97 / 0% | 0.18 / 0 / 0.51 / 0 / 0.73 / 0% |
| Test ROC-AUC (train bot styles vs real users) | 0.9812 | 0.9999 |
| Held-out bot styles ROC-AUC | 0.813 | 0.973 (0.961 before the hand-programmed unit) |
| Flagged: ghost / wind / agent | 0.27 / 0.97 / 0.74 | 0.45 / 0.96 / 0.31 |
| Replay attack flagged | 0.09 | 0.46 |
| Model gzipped / library gzipped | 1.07 KB / 4.7 KB | 1.72 KB / 5.4 KB |

Adding the synthetic humans to the real ones (`HUMANS=both`, [`tune/REPORT-both.md`](tune/REPORT-both.md)) gives a slightly lower real FPR (0.26% at int8) but transfers worse to unseen bots (held-out AUC 0.925, ghost 0.12), so the shipped model uses real humans only.

**Leave one dataset out** ([`train/lodo-report.md`](train/lodo-report.md)): training on five human datasets and testing on the sixth gives FPRs of 0% (MouseTask, CMU), 4 to 6% (Bogazici, KeyRecs, DUX) and **35% for AdSERP**. A new population of people, devices or tasks can look very different, so expect a higher FPR on your own traffic than the 0.33% above until you add your own data.

The full stage-by-stage tables are in [`tune/REPORT.md`](tune/REPORT.md) (real), [`tune/REPORT-synthetic.md`](tune/REPORT-synthetic.md) and [`tune/REPORT-both.md`](tune/REPORT-both.md).

**What this says.** Classic automation (teleports, linear or eased moves, constant-rate typing, DOM events, programmatic scroll) is trivially separable from real people. WindMouse transfers well (96% flagged). Agent-style bots mostly get through on single windows (31%). Ghost-cursor-style humanizers were caught 22% of the time until one hand-programmed unit (see [WSP.md](WSP.md)) raised that to 45% without changing the real-human false-positive rate. The old synthetic-only model looked fine on synthetic humans but flagged one in six real windows.

## Limitations (please read)

- **It's a signal, not proof.** Use the score as one input to a risk decision (step-up challenge, rate limit, review), never as the only reason to block a person.
- **It can be beaten.** Replays of real recorded human traces would very likely pass (our replay set is synthetic traces, flagged 29%). Good humanizers (ghost-cursor style) and agent-style bots also mostly pass. Anyone who can read this README can train against it.
- **The human data is research recordings, desktop only.** Six lab/online-study datasets of mouse or typing tasks. No touch, no phones, few trackpads, no browser autofill or password managers, no assistive technology; mouse and typing are never mixed in one human window (the bots do mix them). The cross-dataset test shows FPR can jump to 35% on a new population. Make sure assistive technology users are never locked out.
- **Two features are off.** No real dataset records click target rectangles or wheel deltas, so `click_offset` and `wheel_dy_cv` are disabled.
- **The score is client-side, so it can be forged.** A bot can just report `score = 0`. Pair it with server checks: rate limits, IP and ASN reputation, TLS/JA4 fingerprints, proof of work or Turnstile-style challenges, and server-side verification of anything that matters.
- **Touch is not modelled.** Pointer events from touch devices are not used yet, so mobile sessions get fewer features (keys and scroll only).
- **Short sessions are weak.** Wait for a few windows (`windows >= 3` or 4) before trusting the score.

## Retraining

```bash
python3 data/external/convert/convert.py   # real humans -> data/external/sessions/ (download first, see DATA.md)
npm run data:humans    # optional synthetic humans -> data/sessions/human/
npm run data:bots      # Playwright bots   -> data/sessions/bot/   (needs a demo server on :5173: npm run demo:dev)
npm run data:replay    # replay-attack eval set
npm run collect:server # optional: real sessions from /collect.html -> data/sessions-real/
npm run tune           # featurize + sweep + soups + pruning + int8/int4 + calibration + LODO, writes src/weights.ts
                       # HUMANS=real (default) | both | synthetic; extra args go to tune.py (--tag, --no-write)
npm run build:lib
```

See [`tune/README.md`](tune/README.md) for details on the tuning pass.

## Privacy

Only timings, coordinates, key *codes* and element rectangles are kept in memory, for about 6 seconds. Nothing is persisted or transmitted by the library. The `/collect` page only saves when you press Download or Save.

## License

MIT

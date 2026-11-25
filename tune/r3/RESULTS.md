# Round 3: pushing the bench score (held-out, val-calibrated)

## Protocol
- **Bots:** the eval half of the plan only, `(i//4)%2 == 1`. Nothing in this round was fitted on those sessions.
- **Two recording sets:**
  - A = `bench/data/raw`: 300/tool, motion recorder; eval half 148/tool.
  - B = `bench/data/raw2`: 80/tool, recorded with the new provenance probe in `bench/site/bench.ts`; eval half 40/tool.
- **Humans:** the 79 held-out test users (16,590 ten-second segments over all splits).
- **Threshold:** calibrated on validation users only, with the rules included (worst val dataset ≤0.5% session FPR). It is then applied unchanged to the test users. The score is 0 if any test dataset exceeds 1%.
- **Leave-tool-out (LOTO):** each tool is scored by a fine-tune that never saw it, at that model's own val-calibrated threshold.
- **Reproduce:**
  1. `bash bench/record2.sh 80`
  2. `BENCH_RAW=raw2 BENCH_WINDOWS=windows2.jsonl BENCH_NO_HUMANS=1 npx tsx bench/featurize.ts`
  3. `python3 tune/r3/rules.py`
  4. `python3 tune/r3/loto_ft.py`
  5. `python3 tune/r3/combined.py`

## Headline (`combined.md`)
| detector | ghost | pptr-st | pw-st | uc | nodriver | botasaurus | pyautogui | MCP | replay-CDP | replay-xdo | worst test FPR | pooled test FPR | score | without replays |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pre-WSP-2 model (fair baseline, `bench/results/RESULTS-eval-baseline.md`) | 57.4 | 45.9 | 49.3 | 29.1 | 47.3 | 7.4 | 75.0 | 45.9 | 2.0 | 31.1 | 0.5% | 0.2% | 39.1 | 44.7 |
| A: WSP-2 model | 76.4 | 45.9 | 49.3 | 29.1 | 46.6 | 64.9 | 85.8 | 45.9 | 2.0 | 31.1 | 0.54% | 0.16% | 47.7 | 55.5 |
| A: + F1 teleport-instant-click | 76.4 | 100 | 100 | 98.6 | 46.6 | 64.9 | 85.8 | 100 | 2.0 | 31.1 | 0.54% | 0.20% | 70.5 | 84.0 |
| A: fine-tune LOTO + F1 (not shipped) | 93.2 | 100 | 100 | 98.6 | 73.0 | 69.6 | 85.1 | 100 | 2.7 | 31.1 | 0.56% | 0.20% | 75.3 | 89.9 |
| A: fine-tune, in-sample tools + F1 | 94.6 | 100 | 100 | 98.6 | 73.6 | 85.1 | 85.8 | 100 | 2.7 | 31.1 | 0.50% | 0.20% | 77.2 | 92.2 |
| B: WSP-2 model | 77.5 | 45.0 | 47.5 | 32.5 | 47.5 | 70.0 | 90.0 | 47.5 | 0 | 0 | 0.54% | 0.16% | 45.8 | 57.2 |
| B: + F1 | 77.5 | 100 | 100 | 100 | 47.5 | 70.0 | 90.0 | 100 | 0 | 0 | 0.54% | 0.20% | 68.5 | 85.6 |
| **B: + F1 + F2 pressure0 (shipped)** | **100** | **100** | **100** | **100** | **100** | **100** | **90.0** | **100** | **87.5** | **0** | **0.54%** | **0.20%** | **87.8** | **98.8** |
| B: + F3 keyless insert | same | | | | | | | | | | | | 87.8 | 98.8 |
| B: rules only, no model | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 100 | 87.5 | 0 | 0.50% | 0.04% | 78.8 | 87.5 |

- **Pooled window FPR of the motion model is 0.12%,** down from 0.28% for the pre-WSP-2 model at 0.5. The rules act at session level: they add 0.04 pts of pooled session FPR, all of it F1 on BOUN.
- **Per-dataset test FPR for the shipped combination:** AdSERP 0.21%, BOUN 0.50%, KeyRecs 0.54%, all others 0.
- **LODO:** the rules don't depend on training data. LODO FPR is the WSP-2 LODO FPR (worst AdSERP 43.7%) plus F1's ≤0.21% on BOUN.
- **The B replay-xdotool rows are 0** because the first 80 plan slots replay mouse-only traces. In A, the 31% comes from key traces.

## What each signal contributed (score on the eval half, all 10 tools)
| lever | gain | human-FPR evidence | status |
|---|---|---|---|
| WSP-2 units (B, W, R) | 39.1 → 47.7 | human datasets: unchanged; LODO better | shipped (round 2) |
| **F1 teleport-instant-click**: a press with exactly 1 move in the prior 1 s, that move ≤30 ms before the press, and a release <5 ms later | +22.8 (A) | **verified on human data:** AdSERP 0/2785, DUX 0/3266, mousetask 0/3423, BOUN 8/3742 (0.21%; BOUN logs some press/release pairs in the same OS tick, likely touchpad taps) | shipped |
| **F2 pressure0**: a pointerdown with pointerType mouse and pressure 0 | +19.3 (B) | **unverifiable on human datasets** (no pointer attributes). 0 of 160 real-OS-input sessions (pyautogui + xdotool through X into Chrome) fired; the Pointer Events spec requires 0.5 while a button is down. Unverified: Firefox/Safari, pens, touch→mouse compatibility, remote-desktop/VNC injectors | shipped, flagged |
| F3 keyless insert: beforeinput insertText with no keydown in 100 ms | +0 (everything it catches, F1/F2 already catch) | unverifiable (our converters synthesise human input events from keys). Risks: dictation, some IMEs, password managers | shipped as a signal (catches fill-only bots that use force:0.5), flagged |
| isTrusted | +0.1 | humans can't produce untrusted events, but site scripts can | not shipped (redundant) |
| F4 causeless focus | report-only | page scripts may focus fields | dropped |
| Session aggregation (`aggregate.md`) | EMA α=0.6: +2.5; top-2 mean: +0.9; mean logit / CUSUM fail the 1% FPR | — | not shipped (small) |
| Fine-tune of 3 dead slots on top of WSP-2 (`loto_ft.json`) | A: +4.8 LOTO (+6.7 in-sample); B: +0 (the rules saturate) | worst test 0.56%; needs threshold p=0.9957; LODO can't be measured (the LODO models have no dead slots) | not shipped |
| Probe-only candidates checked and rejected: movementX vs clientX deltas (equal for every tool), coalesced-event count (always 1 for CDP; also 1 for most real 60 Hz mice), event-vs-handler lag (CDP 0.1–1 ms vs real 1–4 ms, but load-dependent), window/screen offsets (depend on the harness), wheel delta size (platform-specific: 100/120/53/fractional) | — | — | rejected |

## Held-out against in-sample
- **The motion parts were measured both ways.** The fine-tune scores 92.2 (no replays) on tools it was trained on and 89.9 leave-tool-out: most of the gain holds on unseen tools. botasaurus is the exception (85→70 when held out).
- **The rules have almost no parameters,** but I found them by looking at these same tools. That makes held-out-tool claims meaningless for them. Their generality argument is the mechanism: F2 is CDP's default `force=0`; F1 is "move once, press, release in the same instant", the default click of Puppeteer/Playwright/Selenium.
- **The rules are trivial to evade** for an attacker who knows them (pass `force:0.5`, add `steps` and a press delay). Playwright already defeats F2.

## Replays (out of scope for motion)
- **Real human motion replayed through OS input** (replay-xdotool) is indistinguishable at the browser level. Nothing in this round catches it beyond the model's incidental 31% (key traces).
- **replay-CDP is caught by F2 (87.5%) because the replayer used CDP,** not because of the motion.
- **Prototype replay fingerprint (`replay_fp.py`, server-side):**
  - It hashes runs of 32 quantised (dx, dy) steps with ≥10 distinct steps.
  - It collides on 61% of replay-CDP and 41% of replay-xdotool sessions with a run, because the bench reuses traces about twice. Generated bots: 0%.
  - Humans collide across different sessions on 0.4% (AdSERP), 0.55% (BOUN), 0.95% (DUX) and 1.6% (mousetask, a fixed-target task).
  - It only works if the attacker reuses traces, and the human FPR is too high to ship as-is. Keep it as a server-side review signal.
- **Next step for replays:** a challenge-response, such as a target that moves after page load, which a pre-recorded trace can't follow, and rAF/timestamp provenance on the server.

## Size
5,783 B gzipped (esbuild, minified ESM). It was 5,445 B before round 2 and 5,481 B after. Budget ~6 KB.

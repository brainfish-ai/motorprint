# Weight-space programming on motorprint

This applies the idea from **"Sparks of Weight-Space Programming: LLMs can natively read & write neural network weights"**, by Rikiya Takehi, Jayden Teoh, Alex Zhang and Omar Khattab (MIT CSAIL, research blog post, 2 November 2026).
- Paper: https://rikiyat.github.io/blog/weight-space-programming/
- Released logs: https://github.com/RikiyaT/lm_understand-logs
- Summary: https://saanyaojha.substack.com/p/sparks-of-weight-space-programming

It is a blog report, not peer-reviewed. The paper's idea is to read the raw weights to work out what each unit computes, then edit the weights directly to change behaviour, with no gradient descent. Their closest experiment is the Kinetix car: an edit to 3.5% of the weights inserts a small handcrafted circuit.

Everything is in [`tune/wsp/`](tune/wsp/); reproduce it with `bash tune/wsp/run.sh`.

## 1. Interpret
See [`tune/wsp/INTERPRETATION.md`](tune/wsp/INTERPRETATION.md). The raw weights are in `weights-dump.md` and the probes in `probes.md`.
- **Structure.** Pruning left 9 live first-layer units, and layer 2 is a two-way bot-vs-human vote.
- **Ghost-style bots.** They get through because the net ignores the strongest cue against them: real cursors are clocked (high `dt_mode_share`) and pixel-quantised (high `turn_zero_frac`), while ghost-style bots are neither.
- **Agent bots.** They get through via two "human" units, h1_0 (mouse without typing) and h1_16 (low event rate).
- **Real-human false positives.** These are fast, regular typists (DUX, KeyRecs) who look like bot typing on every available feature.
- **A dataset artifact.** One bot unit (h1_13) partly keys on "mouse and keyboard in the same window", which the single-task human datasets almost never contain.

## 2. Program (no gradients)
[`tune/wsp/program.py`](tune/wsp/program.py) writes one detector unit, **G**, by hand in raw feature units, converts it to z-space, and drops it into the dead slots h1_1 and h2_0:

```
G = relu(3 * [ (0.15 - turn_zero_frac)/0.15 + (0.20 - dt_mode_share)/0.20
             + (turn_entropy - 0.55)/0.15 + (0.10 - pause_frac)/0.10 + (n_moves - 3.0) - 3.0 ])
h2_0 = relu(G);  logit += 1.0 * h2_0      (the output weight is snapped to the row's existing int8 grid)
```

- **What changed.** 9 parameters: 5 weights and 1 bias in h1_1, 1 relay weight and 1 bias in h2_0, and 1 output weight. That is 2.4% of the 376 non-zero weights and biases, or 0.5% of all 1,793.
- **What didn't.** Every other int8 code is bit-identical. Architecture and format are unchanged, and the model grows from 1,703 to 1,722 B gzipped.
- **Check.** The TS runtime matches Python to within 6e-7 on 2,000 windows.
- **How the thresholds were chosen.** I set them by reading the percentiles in `probes.md`. I then picked from about 15 variants, using catch rate and human fire rate on train/validation users and the *design* half of the ghost sessions. That was environment feedback, but not gradients.
- **The false-positive cluster was not programmed.** No feature separates it from bot typing (see the interpretation).

## 3. Evaluate
Real-human FPR is measured on 25,168 windows from test users. Catch rates are on the *eval* half of the held-out bot sessions, which neither method looked at. Full tables are in [`tune/wsp/RESULTS.md`](tune/wsp/RESULTS.md).

| model | changed | test AUC | real FPR @0.5 | held-out AUC | ghost | wind | agent | replay |
|---|---|---|---|---|---|---|---|---|
| shipped before (4_quant) | 0 | 0.9999 | 0.33% | 0.954 | 0.21 | 0.94 | 0.33 | 0.29 |
| **WSP (hand-programmed)** | 9 (2.4%) | 0.9999 | **0.33%** (identical per dataset) | 0.971 | **0.43** | 0.94 | 0.33 | 0.46 |
| fine-tune, all surviving weights, same mask, lr 1e-3 | 341 (91%) | 0.9998 | 2.61% | 0.988 | 0.86 | 0.99 | 0.77 | 0.77 |
| fine-tune, same 2 slots only, lr 3e-4 | 40 (11%) | 1.0000 | 0.57% | 0.967 | 0.49 | 0.97 | 0.56 | 0.43 |

The fine-tunes are trained on the training set plus the same ghost design windows, then quantised to int8. At the shipped 0.5 threshold they raise real-human false positives 2x to 8x. With each model's threshold re-picked on validation users to match the shipped validation FPR (0.13%), the comparison is:

| model | thr | real FPR (test) | ghost | wind | agent |
|---|---|---|---|---|---|
| WSP | 0.49 | 0.33% | 0.44 | 0.94 | 0.34 |
| fine-tune, all weights, lr 1e-3 | 0.94 | 0.41% | **0.61** | 0.98 | **0.66** |
| fine-tune, all weights, lr 3e-4 | 0.98 | 0.35% | 0.50 | 0.96 | 0.58 |
| fine-tune, same 2 slots, lr 3e-4 | 0.73 | **0.32%** | 0.43 | 0.95 | 0.45 |

**The honest verdict.**
- **Against the shipped model,** hand-programming is a strict improvement. Ghost catch doubles (0.21 to 0.43 on the eval half; 0.22 to 0.45 over all held-out ghost sessions), held-out AUC rises from 0.954 to 0.971 on the eval half (0.961 to 0.973 over all held-out sessions), and real-human FPR and every other metric are unchanged.
- **Against gradient fine-tuning on the same failure examples,** hand-programming **does not win**. Re-calibrated full fine-tunes catch more ghost and agent bots, at the cost of a slightly higher test FPR (0.35 to 0.41% versus 0.33%) and rewriting 91% of the weights. A gradient-trained unit in the same two slots matches WSP on ghost (0.43), beats it on agent (0.45 versus 0.34), and has a marginally lower FPR (0.32%), but needs its threshold moved to 0.73.
- **What WSP does better:** it is surgical. 9 readable weights, no recalibration, a guaranteed-identical FPR on the measured population, and a rule a person can audit.

## 4. Ship
The WSP model is strictly better than the previous default on held-out data and doesn't raise real-human false positives, so it is now `src/weights.ts`.
- Demo after the rebuild: replayed human trace 0.00007, scripted bot 0.99995. Library: 5,445 B gzipped.
- **The recalibrated fine-tunes were not shipped.** They change the threshold and raise real-human FPR at 0.5, which the brief ruled out. They are kept in `tune/wsp/models/` if you prefer catch rate over FPR.

## Caveats
- **G is easy to evade.** A bot that rounds coordinates to integers and paces events to `requestAnimationFrame` will beat it.
- **The ghost bots are our own ghost-cursor-style generator,** not the ghost-cursor library itself.
- **G also fires on 48% of replay windows.** Replay through Playwright loses the device clock too.
- **"Clocked" human data is partly our own emulation.** Several datasets were frame-coalesced during conversion (see DATA.md), so part of the clocked-human signal comes from that emulation. Real browsers do coalesce to frames, but check G's fire rate on your own traffic (0.1 to 1.8% of test-user windows here, highest on DUX).
- **No touch data.**

## Round 2: units guided by the real-tool benchmark (bench/)
Design data: bench sessions in plan blocks with even `(i//4)%2` plus train/val humans. Evaluation: the odd blocks (148 sessions per tool), the 79 held-out test users, and leave-one-dataset-out (LODO) models with the same units installed. Code: `tune/wsp/bench_wsp.py`, `tune/wsp/units.py`.

**Acceptance rule:** the bench score rises, the worst test-user dataset stays at ≤1% session FPR, and LODO FPR doesn't get worse.

| unit | target and intent | raw-feature params (`h=relu(gain·(Σw·x+b))`, `logit += out·h`) | design-half effect | verdict |
|---|---|---|---|---|
| B `early_peak_metronome` | botasaurus' humanised cursor peaks in speed at the very start of every move (peak_pos ≈0.005 against ≈0.4 for people) and runs on a steady clock (dt_cv ≈0.17 against ≈0.6) | w: peak_pos −1/0.03, dt_cv −1/0.3, n_moves +1; b −1.5; gain 2; out +1.6 | botasaurus 16→67%, ghost 62→85%, FPR unchanged | **kept** |
| W `wheel_burst` | `pyautogui.scroll(k)` sends k wheel notches less than 4 ms apart | w: dt_sub4_frac 1/0.04, has_scroll 3; b −4.25; gain 3; out +1.6 | pyautogui 75→90%, nodriver +4 pts, FPR unchanged | **kept, flagged:** of our humans, only AdSERP (16k windows) and DUX (0.9k) scroll |
| R `scroll_reader` | LODO suppressor: a window with scrolling only (no pointer, keys or clicks) is evidence of a human | w: has_scroll 1, has_mouse −1, has_keys −1, has_click −1; b −0.5; gain 6; out −1.6 | LODO AdSERP 47.0→43.7%, nodriver −1.4 pts | **kept, flagged:** keys on event absence |
| G `clocked_glide` (slack 1–4) | ghost-cursor's near-perfect clock (dt_cv ≈0.10, dt_mode_share ≈0.55), long paths, no pauses | w: dt_cv −1/0.15, dt_mode_share 1/0.15, n_moves 1, pause_frac −1/0.02 | slack 1: worst FPR 2.1%; slack 3: +0.4 pts score, but LODO AdSERP/BOUN +0.1 pt and pooled FPR up | rejected (B already covers ghost) |
| K `keyless_typing` | input with no keydown (CDP `insertText`/fill) | w: input_no_key_frac 1; b −0.08; gain 60; out 1.6 | botasaurus +37 pts | **vetoed:** our converters synthesise human `input` events from key presses, so the human FPR can't be measured |
| S `keys_scroll_no_mouse` | — | — | no effect | rejected |

**An install fix.** If a unit's output weight is larger than the LODO model's largest output code, installing it re-quantised the whole output row. That flipped 2–3 borderline human segments (0.498→0.502) in every LODO model. `units.py` now puts the excess into the unit's own layer-2 relay weight. With a null unit, LODO is now bit-identical to the baseline.

**Eval half (held out from design)**, session detection per tool:

| model | ghost | pptr-st | pw-st | uc | nodriver | botasaurus | pyautogui | MCP | replay-CDP | replay-xdo | worst LUO | pooled sess / window | LODO worst (AdSERP) | bench score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before @0.5 | 62.2 | 51.4 | 52.7 | 38.5 | 52.7 | 17.6 | 75.0 | 46.6 | 2.7 | 31.8 | 1.4% (fails) | 0.4% / 0.28% | 47.0% | 0 |
| before @0.55 (its best threshold) | 61.5 | 50.7 | 52.7 | 37.2 | 51.4 | 12.2 | 75.0 | 45.9 | 2.7 | 31.1 | 1.1% | 0.3% | 47.0% | 42.0 |
| **B+W+R, thr 0.65 (shipped)** | 78.4 | 48.6 | 49.3 | 29.1 | 49.3 | 67.6 | 85.8 | 45.9 | 3.4 | 31.1 | **0.5%** | 0.2% / 0.16% | **43.7%** | **48.9** |
| B+W+R @0.55 | 82.4 | 50.7 | 52.7 | 37.2 | 51.4 | 71.6 | 85.8 | 45.9 | 3.4 | 31.1 | 1.1% | 0.3% | 43.7% | 51.2 |

- **The 0.65 threshold was picked on validation users,** as the lowest threshold where the worst validation dataset is at ≤0.5%: half the 1% budget, because validation users never reproduced KeyRecs' 1.4% on test users.
- **The score drop for the stealth, uc and nodriver tools at 0.65 is the threshold, not the units.** The units leave those tools unchanged at a fixed threshold.

**Fine-tune comparison** (same design data, replays excluded, eval half; the threshold is the worst-test-group-1% threshold):

| model | params changed | bench score | threshold needed | worst LUO @0.5 |
|---|---|---|---|---|
| B+W+R (WSP) | 21 | 51.2 (48.9 at shipped 0.65) | 0.55 / 0.65 | 1.4% (as before; KeyRecs, keyboard-only) |
| fine-tune, 3 dead slots, lr 1e-3 | ~126 | **61.1** | 0.80 | 2.1% (AdSERP) |
| fine-tune, 3 dead slots, lr 3e-4 | ~126 | 58.4 | 0.68 | 2.7% |
| fine-tune, all surviving weights, lr 1e-3 | ~1.5k | 55.5 | 0.99 | 41.6% (calibration destroyed) |

**Verdict.**
- **Gradient slots beat the hand-written units on this eval half by about 10 points,** but they need a large threshold move.
- **The eval half shares tools with the design half,** so the fine-tune can memorise tool identity. Round 3 tests that with leave-one-tool-out.
- **LODO couldn't be measured for the fine-tunes.** The LODO models have no dead slots (`tune/wsp/benchft-lodo.json`).

**Out of scope for motion.** Replays of real human traces (replay-CDP 3%, replay-xdotool 31%) carry real human motion, so no motion unit can or should catch them.

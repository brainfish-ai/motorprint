# What the shipped network computes

Model: `base-4_quant.json` (the real-human model from `tune/REPORT.md`: 38 → 32 → 16 → 1, 80% globally pruned, int8 per row, threshold 0.5).
Raw weights with feature names: [`weights-dump.md`](weights-dump.md). Every claim below is checked with activation probes in [`probes.md`](probes.md), which use only train/validation users and the *design* half of the held-out bot sessions. Test users and the *eval* half are kept for [`RESULTS.md`](RESULTS.md).

## Structure

1. **Pruning left a much smaller network than the 32-16 shape suggests.** Only 9 of the 32 first-layer units are alive (h1_0, 6, 13, 16, 17, 18, 22, 25, 28). Only 8 of the 16 second-layer units have a non-zero output weight. h1_1 and h2_0 are completely dead: no inputs, and no outputs or an output weight of 0.
2. **Layer 2 is effectively a two-way vote.** Each live h2 unit reads the same nine h1 units, with one of two sign patterns:
   - **Bot units:** h2_3, h2_8 and h2_10, with output weights +0.84, +1.33 and +1.63. They are excited by h1_28, h1_22, h1_13 and h1_6, and inhibited by h1_25, h1_16, h1_0 and h1_18.
   - **Human units:** h2_2, h2_5, h2_6, h2_12 and h2_13, with negative output weights. They use the mirror-image pattern.

   So the logit is roughly *bot evidence (h1_28 + h1_22 + h1_13 + h1_6) minus human evidence (h1_25 + h1_16 + h1_18 + h1_0 + h1_17)*.
   - *Probe:* the human h2 units sit at 2.7 to 3.4 on every human dataset and 0.01 to 0.07 on every training bot style. The bot units are the mirror image: about 0.0 to 0.07 on humans and 1.7 to 4.3 on bots. ✔

## First-layer units

| unit | reading of the weights | probe (activation on, mean) | verdict |
|---|---|---|---|
| h1_25 | **Human typist.** Long key holds (hold_ms +1.52) and irregular inter-key intervals (iki_cv +0.72), with a low event rate | On in 100% of KeyRecs and CMU windows and 61% of DUX, about 0% of mouse-only datasets. Correlates with iki_cv at +0.90 and hold_ms at +0.87. Bots: 0 to 45% on, low amplitude | ✔ |
| h1_18 | **Human mouse, no keys.** Negative on hold_ms, has_keys, iki_mean and moves_before_press; positive on turn_zero_frac | On in 96% of AdSERP and 99% of MouseTask windows, versus 2 to 27% of bots | ✔ |
| h1_0 | **Clocked mouse, no typing.** Negative on press_cv, hold_ms and turn_zero_frac; positive on dt_mode_share | On in 85 to 99% of mouse-dataset windows. But also on in 73% of dom-bot and **96% of agent** windows (mean 1.79, the highest of any group) | ✔, with a side effect: this is one reason agent bots get through |
| h1_16 | **Slow, variable typing or clicking.** Low event_rate (-0.87), variable holds | High on DUX (0.97) and CMU (0.74), but also on **agent** (0.89, on 95%), because agents pause for a long time to "think" | ✔, and the second reason agents get through |
| h1_17 | **Many irregularly timed moves.** Correlates with n_moves (+0.89), turn_entropy (+0.85) and dt_cv (+0.79) | On for 100% of Bogazici and MouseTask windows, but also 66 to 90% of most bot styles. A weak discriminator with the smallest outgoing weight | ✔ (weak) |
| h1_28 | **Machine regularity.** Low iki_cv (-1.01), equal step lengths (step_cv -0.92), straight paths (turn_mean -0.82), short holds | dom 100% on (2.64), bezier 90%, eased 87%, linear 71%. Humans are on in 4 to 65% of windows but at small amplitude (0.01 to 0.43). It is highest on KeyRecs and CMU, which is the false-positive pathway (see below) | ✔ |
| h1_22 | **Fast, variable-speed, straight-to-target moves before clicks** (dt_mean, speed_cv, step_cv, speed_mean, has_click) | teleport 2.77, linear 1.82, eased 1.46; humans ≤ 0.35 | ✔ |
| h1_13 | **Busy window mixing modalities with regular timing.** has_scroll +0.61, has_click +0.39, has_keys +0.34, dt_cv -0.40 | Bots 2.1 to 6.0; humans 0 to 0.26 | ✔, **but partly a dataset artifact**: only 1.8% of real-human windows contain both a click and a key press, because each study recorded a single task. The bots mix modalities. Real web users filling in forms will mix them too, so this unit will over-fire on real traffic |
| h1_6 | **Regular typing with clicks** (low iki_cv, short holds, has_click) | linear, eased and dom 67 to 92% on; humans 2 to 20% | ✔ |

## Why ghost-cursor-style bots get through

Compare missed ghost windows with caught ones (design half, n=608 missed and 182 caught):
- **The human units are stronger:** h2_2 is 1.65 on missed windows versus 0.63 on caught ones.
- **The bot units are weaker:** h2_10 is 0.47 versus 1.62.
- **In layer 1, the missed windows look less "busy":** h1_13 is 1.06 versus 2.56, and h1_22 is 0.48 versus 1.27.
- **Their gaussian key timing looks human:** h1_25 is 0.54. Their jittered paths are not "regular" either: h1_28 is 0.42.

What the missed windows *do* differ on, measured against real cursors:
- turn_zero_frac: 99th percentile 0.20, versus a human median of 0.29;
- dt_mode_share: median 0.05, versus 0.36 for humans;
- turn_entropy: median 0.64, versus 0.46 for humans;
- pause_frac: about 0.01.

Real cursors arrive on a device and display clock (a dominant inter-event dt) and in integer pixels (many exactly collinear steps). A ghost-style bot sends events off-clock, with sub-pixel jitter on every point.

**The network barely uses this cue.** The only live unit that weights turn_zero_frac heavily is h1_0 (-0.39), and h1_0 is a *human* unit. So "no collinear steps" actually pushes slightly towards human. That gap is what the programmed unit fills.

## Why some real people are flagged

Validation users produce 35 false-positive windows out of 27,209 at threshold 0.5: 21 from DUX, 13 from KeyRecs and 1 from AdSERP. Across train and validation users there are 300 false positives, 79% of them in typing windows.
- **Who they are:** fast, rhythmically regular typists. Their iki_cv is about 0.24, against a median of 0.63 for typing humans and 0.20 for bot typing. They push h1_28 (machine regularity) up and h1_25 (human typist, which needs high iki_cv) down.
- **Why there's no fix in the current features:** no feature separates them from bot typing. A suppressor unit would also hand bots a pass.
- **So:** no unit was programmed for this cluster (see WSP.md).

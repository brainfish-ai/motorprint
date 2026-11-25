# motorprint bench

A reproducible benchmark for on-device bot detection. Off-the-shelf automation tools, run at their published defaults, perform four ordinary tasks on a test page. Real people come from six openly licensed datasets, split so the model never saw them. Results: [`results/RESULTS.md`](results/RESULTS.md). Tool versions: [`results/versions.json`](results/versions.json).

```bash
bash bench/run.sh                       # record any missing sessions (300 per tool), then featurize and score
BENCH_SKIP_RECORD=1 bash bench/run.sh   # re-score existing recordings only (deterministic)
python3 bench/score.py --model some-spec.json --tag mine   # score another model
```

## Protocol

**Page** (`site/`). One static page with four tasks, chosen by `?task=`:
- **form**: name, email, country select, textarea, checkbox, submit;
- **nav**: click-through over hash-routed cards;
- **read**: a long article with scrolling, then a button;
- **search**: type a query, submit, click a result.

The page records input with the library's own recorder (`src/recorder.ts`), so the events are exactly what motorprint sees in production. It also records `navigator.webdriver`. Events are streamed to `server.mjs`, which stores them in `data/raw/<tool>/` (gitignored).

**Plan** (`plan.mjs`, seeded). The same 300 session specs are used for every tool: task = index mod 4, plus the names, emails, queries and click paths.

**Bots** (`tools/`). Defaults everywhere, with stealth where the tool offers it:

| tool | how it acts |
|---|---|
| ghost-cursor 1.4.2 + puppeteer-extra stealth | `cursor.click`, `cursor.scroll`, `page.type` |
| puppeteer-extra + stealth | `page.click`, `page.type`, `mouse.wheel` |
| playwright-extra + stealth | `locator.click`, `fill`, `pressSequentially`, `mouse.wheel` |
| undetected-chromedriver (Selenium 4) | `element.click`, `send_keys`, `ActionChains.scroll_by_amount`; headed on Xvfb (uc's default) |
| nodriver | `element.mouse_move`, `mouse_click`, `send_keys`, `tab.scroll_down`; headed |
| botasaurus-driver | `enable_human_mode()` (humanised cursor), then `click`, `type`, `scroll` |
| pyautogui | OS-level XTest events (`isTrusted = true`) into a plain kiosk Chrome with no automation flags. Half the sessions use pyautogui defaults (instant moves, no typing interval). The other half use the documented "humanised" recipe (duration 0.25 to 0.9 s, `easeInOutQuad`, typing interval 40 to 120 ms) |
| Playwright MCP 0.0.86 (the real server over stdio) | Driven by a **scripted policy instead of an LLM**: snapshot, then `browser_type` / `browser_click` / `browser_select_option` / `browser_press_key` on snapshot refs, with 1.2 to 3.5 s "think" pauses between calls |
| replay-CDP | 300 **real** 12 s trace segments from **held-out test users** (50 per dataset, `replay_traces.py`), replayed at their original timing through `Input.dispatchMouseEvent` / `dispatchKeyEvent` (playwright-extra + stealth) |
| replay-xdotool | The same 300 traces, replayed as OS-level XTest events with `xdotool` into a kiosk Chrome |

**Humans.** Two official human test sets:
- **Leave-users-out (LUO):** the shipped model's held-out test users (`human_split.json`, 79 users).
- **Leave-one-dataset-out (LODO):** the training recipe retrained without one dataset, then scored on every user of that dataset.

Each human session is cut into 10 s segments. A segment is the human counterpart of one bot session.

**Scoring** (`featurize.ts`, `score.py`). Every session is streamed exactly like the live detector: a tick every 500 ms, a 3 s window, at least 4 events, unchanged windows skipped, and an EMA on log-odds (0.35).
- **Window level:** per-tick raw score.
- **Session level:** the session is flagged if the smoothed score ever reaches the threshold.
- **Time to detection:** seconds from the first event to the first such tick.
- **Reported:**
  - detection at the shipped threshold;
  - TPR at 1% and 0.1% FPR on the pooled LUO humans;
  - window and session ROC-AUC;
  - FPR per dataset and the worst-group FPR.

**Bench score** (one number). The mean session detection rate over the 10 tools, at the operating point where the *worst* human dataset (LUO) has at most 1% session FPR. It is 0 if the detector cannot reach that point.

**Baselines:**
- **`navigator.webdriver`:** flags the session if it is true.
- **isTrusted check:** flags any untrusted event.
- **Event-rate rules:**
  1. a press with no earlier move in the window;
  2. median inter-key interval under 30 ms;
  3. median move interval under 4 ms;
  4. text input with no key events.
- **Conservative variant:** drops rule 1, the main source of human false positives.

Humans are assumed to have `webdriver = false` and all events trusted, which is true of real browsers. **Caveat:** the human datasets' `input` events are synthesised from key presses by our converters, so rule 4 cannot fire on them. Its real-world FPR (autofill, paste, IME) is unmeasured.

**Design/eval split for model changes.** Any change to the model that is guided by this benchmark must use only the **design half** (plan blocks of 4 with even `i // 4`) and train/val users. It is reported on the **eval half** (odd `i // 4`), the test users, and LODO.

## Limits
- **Real tools, our page.** The tools are real, but the tasks are ours. Real bot operators tune their settings, and per-site scripts may look different.
- **No LLM agent.** No model API key is available on the box and it can't run a local model, so the browser agent is the real Playwright MCP server with a scripted policy. Real agent timing would add model latency and different snapshot and scroll behaviour.
- **Replays are out of scope for motion features.** A replayed real trace *is* human motion. Catching it needs server-side signals (reuse of the same trace, timing relative to page content, environment fingerprints), not this model.
- **Load on the box varied.** Recording ran on a shared machine, with up to 9 parallel lanes near the end. Event timing includes that jitter, as it would on a cloud bot farm.
- **Desktop only.** The human data contains no touch.

## Round 3: provenance probe and rules
- **New recording set.** `bench/record2.sh` re-records 80 sessions per tool into `bench/data/raw2` on port 18791. The page now also logs a provenance probe: pointer, keyboard, wheel and focus attributes, event-vs-handler lag and rAF frames.
- **Headline:** `tune/r3/combined.py` scores the motion model OR the provenance rules on held-out sessions, with the threshold calibrated on validation users. Results and caveats are in `tune/r3/RESULTS.md`.
- **Score: 87.8 over all 10 tools, 98.8 without replays.** Test-dataset FPR stays ≤0.54%.

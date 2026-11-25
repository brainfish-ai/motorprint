# motorprint bench results (eval-W)

1480 bot sessions (eval half) from 10 tools; human test set = 2547 ten-second segments from 79 held-out users (leave-users-out) across 6 datasets. Model threshold 0.5.

## Headline: session-level detection per tool

**Bench score** = mean session detection rate over the tools, at an operating point where the *worst* human dataset has at most 1% session FPR (0 if the detector cannot get there).

| detector | ghost-cursor | pptr-stealth | pw-stealth | uc-selenium | nodriver | botasaurus | pyautogui | pw-MCP | replay-CDP | replay-xdo | worst-group session FPR | pooled session FPR | **bench score** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| motorprint model @ shipped thr | 62.2% | 51.4% | 52.7% | 38.5% | 54.1% | 19.6% | 85.8% | 46.6% | 2.7% | 31.8% | 1.4% | 0.4% | **0.0** |
| navigator.webdriver | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | **0.0** |
| isTrusted check | 25.0% | 25.0% | 25.0% | 25.0% | 0.0% | 0.0% | 0.0% | 21.6% | 0.0% | 0.0% | 0.0% | 0.0% | **12.2** |
| event-rate rules (all 4) | 65.5% | 62.2% | 60.8% | 54.7% | 50.0% | 67.6% | 30.4% | 51.4% | 13.5% | 10.8% | 38.8% | 8.6% | **0.0** |
| event-rate rules (conservative: 3, no press-without-move) | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| cheap checks: webdriver OR isTrusted OR conservative rules | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| model OR cheap checks | 62.2% | 52.0% | 53.4% | 58.1% | 55.4% | 55.4% | 85.8% | 50.0% | 3.4% | 31.8% | 1.4% | 0.5% | **0.0** |
| motorprint model @ worst-group-1% thr (0.550) | 61.5% | 50.7% | 52.7% | 37.2% | 52.7% | 14.2% | 85.8% | 45.9% | 2.7% | 31.1% | 1.1% | 0.3% | **43.4** |

## Model detail per tool

| tool | sessions | median length | no scorable window | webdriver=true | window det @thr | session det @thr | window TPR @1% / 0.1% FPR | session TPR @1% / 0.1% FPR | window AUC | session AUC | median time to detect | detected ≤2 s / ≤5 s | by task (form/nav/read/search) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ghost-cursor | 148 | 5.7 s | 0 | 0.0% | 56.1% | 62.2% | 63.2% / 51.9% | 76.4% / 54.7% | 0.965 | 0.986 | 3.0 s | 13.5% / 61.5% | 100.0% / 27.0% / 21.6% / 100.0% |
| puppeteer-stealth | 148 | 0.5 s | 0 | 0.0% | 26.6% | 51.4% | 36.7% / 23.1% | 52.0% / 41.9% | 0.880 | 0.950 | 0.5 s | 51.4% / 51.4% | 100.0% / 8.1% / 0.0% / 97.3% |
| playwright-stealth | 148 | 0.4 s | 0 | 0.0% | 27.1% | 52.7% | 37.2% / 25.0% | 53.4% / 48.6% | 0.884 | 0.951 | 0.5 s | 52.7% / 52.7% | 100.0% / 13.5% / 0.0% / 97.3% |
| undetected-chromedriver | 148 | 0.7 s | 0 | 0.0% | 23.1% | 38.5% | 37.7% / 18.7% | 48.6% / 27.0% | 0.879 | 0.944 | 0.5 s | 38.5% / 38.5% | 100.0% / 32.4% / 0.0% / 21.6% |
| nodriver | 148 | 1.7 s | 0 | 0.0% | 52.8% | 54.1% | 63.6% / 46.0% | 72.3% / 41.2% | 0.958 | 0.984 | 0.5 s | 52.0% / 54.1% | 97.3% / 16.2% / 5.4% / 97.3% |
| botasaurus-human | 148 | 4.7 s | 0 | 0.0% | 10.6% | 19.6% | 23.0% / 5.8% | 45.3% / 6.1% | 0.858 | 0.905 | 3.0 s | 4.7% / 16.9% | 21.6% / 0.0% / 21.6% / 35.1% |
| pyautogui | 148 | 2.7 s | 0 | 0.0% | 69.1% | 85.8% | 71.1% / 66.3% | 85.8% / 85.1% | 0.981 | 0.990 | 1.0 s | 83.1% / 85.8% | 100.0% / 100.0% / 43.2% / 100.0% |
| playwright-mcp | 148 | 9.3 s | 0 | 0.0% | 31.4% | 46.6% | 42.6% / 30.3% | 58.8% / 45.3% | 0.978 | 0.949 | 7.5 s | 6.8% / 18.2% | 86.5% / 0.0% / 97.3% / 2.7% |
| replay-cdp | 148 | 9.8 s | 0 | 0.0% | 2.1% | 2.7% | 3.4% / 1.3% | 4.7% / 1.4% | 0.563 | 0.555 | 4.5 s | 0.0% / 2.0% | 1.9% / – / 3.2% / – |
| replay-xdotool | 148 | 9.9 s | 2 | 0.0% | 16.7% | 31.8% | 20.0% / 15.6% | 31.8% / 31.1% | 0.644 | 0.646 | 0.5 s | 31.1% / 31.1% | 46.3% / – / 23.4% / – |

## Humans: false-positive rate by dataset

Leave-users-out = the shipped model on its held-out test users. Leave-one-dataset-out = the same recipe (best config, int8, thr 0.5) retrained without that dataset, scored on all of its users.

| dataset | LUO window FPR | LUO session FPR (10 s) | LODO window FPR | LODO session FPR | event-rate rule session FPR |
|---|---|---|---|---|---|
| adserp | 0.1% | 0.2% | 25.6% | 47.0% | 1.0% |
| boun | 0.0% | 0.0% | 3.3% | 4.7% | 38.8% |
| cmu | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| dux | 0.5% | 0.2% | 4.8% | 10.1% | 31.4% |
| keyrecs | 0.6% | 1.4% | 1.9% | 3.1% | 0.0% |
| mousetask | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **worst** | **0.6%** | **1.4%** | **25.6%** | **47.0%** | 38.8% |

Thresholds on pooled test humans: window 0.105 (1% FPR) / 0.758 (0.1%); session 0.166 / 0.792; worst-group-1% session threshold 0.550.

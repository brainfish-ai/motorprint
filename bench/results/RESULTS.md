# motorprint bench results

3000 bot sessions (all half) from 10 tools; human test set = 2547 ten-second segments from 79 held-out users (leave-users-out) across 6 datasets. Model threshold 0.5.

## Headline: session-level detection per tool

**Bench score** = mean session detection rate over the tools, at an operating point where the *worst* human dataset has at most 1% session FPR (0 if the detector cannot get there).

| detector | ghost-cursor | pptr-stealth | pw-stealth | uc-selenium | nodriver | botasaurus | pyautogui | pw-MCP | replay-CDP | replay-xdo | worst-group session FPR | pooled session FPR | **bench score** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| motorprint model @ shipped thr | 62.0% | 50.3% | 52.7% | 38.0% | 53.3% | 16.7% | 75.0% | 46.3% | 1.7% | 28.0% | 1.4% | 0.4% | **0.0** |
| navigator.webdriver | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | **0.0** |
| isTrusted check | 25.0% | 25.0% | 25.0% | 25.0% | 0.0% | 0.0% | 0.0% | 21.3% | 0.0% | 0.0% | 0.0% | 0.0% | **12.1** |
| event-rate rules (all 4) | 66.7% | 60.3% | 61.3% | 55.3% | 50.0% | 67.0% | 29.7% | 53.3% | 12.3% | 10.3% | 38.8% | 8.6% | **0.0** |
| event-rate rules (conservative: 3, no press-without-move) | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 0.7% | 0.0% | 0.9% | 0.2% | **35.1** |
| cheap checks: webdriver OR isTrusted OR conservative rules | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 0.7% | 0.0% | 0.9% | 0.2% | **35.1** |
| model OR cheap checks | 62.0% | 52.0% | 54.7% | 56.7% | 54.3% | 53.3% | 75.0% | 49.7% | 2.0% | 28.0% | 1.4% | 0.5% | **0.0** |
| motorprint model @ worst-group-1% thr (0.550) | 61.0% | 49.3% | 52.3% | 37.3% | 52.0% | 12.7% | 75.0% | 45.7% | 1.3% | 27.7% | 1.1% | 0.3% | **41.4** |

## Model detail per tool

| tool | sessions | median length | no scorable window | webdriver=true | window det @thr | session det @thr | window TPR @1% / 0.1% FPR | session TPR @1% / 0.1% FPR | window AUC | session AUC | median time to detect | detected ≤2 s / ≤5 s | by task (form/nav/read/search) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ghost-cursor | 300 | 5.7 s | 0 | 0.0% | 56.6% | 62.0% | 63.7% / 53.0% | 75.0% / 56.0% | 0.963 | 0.984 | 3.0 s | 15.0% / 61.3% | 100.0% / 28.0% / 20.0% / 100.0% |
| puppeteer-stealth | 300 | 0.5 s | 0 | 0.0% | 25.7% | 50.3% | 36.1% / 22.8% | 51.7% / 42.7% | 0.880 | 0.952 | 0.5 s | 50.3% / 50.3% | 98.7% / 8.0% / 0.0% / 94.7% |
| playwright-stealth | 300 | 0.4 s | 0 | 0.0% | 26.7% | 52.7% | 37.4% / 23.9% | 54.3% / 47.0% | 0.884 | 0.953 | 0.5 s | 52.7% / 52.7% | 100.0% / 18.7% / 0.0% / 92.0% |
| undetected-chromedriver | 300 | 0.7 s | 0 | 0.0% | 22.7% | 38.0% | 36.7% / 18.8% | 46.3% / 28.3% | 0.878 | 0.943 | 0.5 s | 38.0% / 38.0% | 100.0% / 26.7% / 0.0% / 25.3% |
| nodriver | 300 | 1.7 s | 0 | 0.0% | 51.2% | 53.3% | 59.9% / 43.2% | 65.0% / 40.3% | 0.952 | 0.963 | 0.5 s | 53.0% / 53.3% | 98.7% / 17.3% / 0.0% / 97.3% |
| botasaurus-human | 300 | 4.8 s | 0 | 0.0% | 9.6% | 16.7% | 21.2% / 5.8% | 35.7% / 5.0% | 0.851 | 0.897 | 3.0 s | 2.7% / 13.7% | 18.7% / 0.0% / 13.3% / 34.7% |
| pyautogui | 300 | 2.7 s | 0 | 0.0% | 66.2% | 75.0% | 67.1% / 64.3% | 75.0% / 74.7% | 0.883 | 0.977 | 1.5 s | 73.3% / 75.0% | 100.0% / 100.0% / 0.0% / 100.0% |
| playwright-mcp | 300 | 9.0 s | 0 | 0.0% | 30.8% | 46.3% | 41.8% / 29.3% | 58.7% / 44.0% | 0.978 | 0.950 | 9.0 s | 6.7% / 17.3% | 86.7% / 0.0% / 97.3% / 1.3% |
| replay-cdp | 300 | 9.7 s | 0 | 0.0% | 1.2% | 1.7% | 2.4% / 0.8% | 3.0% / 0.7% | 0.548 | 0.544 | 4.5 s | 0.0% / 1.0% | 0.9% / – / 2.1% / – |
| replay-xdotool | 300 | 9.7 s | 5 | 0.0% | 17.1% | 28.0% | 19.7% / 16.0% | 28.3% / 27.7% | 0.640 | 0.639 | 0.5 s | 27.7% / 27.7% | 38.9% / – / 21.9% / – |

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

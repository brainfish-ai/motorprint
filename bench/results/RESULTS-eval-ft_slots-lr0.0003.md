# motorprint bench results (eval-ft_slots-lr0.0003)

1480 bot sessions (eval half) from 10 tools; human test set = 2547 ten-second segments from 79 held-out users (leave-users-out) across 6 datasets. Model threshold 0.5.

## Headline: session-level detection per tool

**Bench score** = mean session detection rate over the tools, at an operating point where the *worst* human dataset has at most 1% session FPR (0 if the detector cannot get there).

| detector | ghost-cursor | pptr-stealth | pw-stealth | uc-selenium | nodriver | botasaurus | pyautogui | pw-MCP | replay-CDP | replay-xdo | worst-group session FPR | pooled session FPR | **bench score** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| motorprint model @ shipped thr | 92.6% | 52.0% | 53.4% | 58.1% | 84.5% | 74.3% | 85.8% | 60.1% | 4.7% | 31.8% | 2.7% | 0.9% | **0.0** |
| navigator.webdriver | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | **0.0** |
| isTrusted check | 25.0% | 25.0% | 25.0% | 25.0% | 0.0% | 0.0% | 0.0% | 21.6% | 0.0% | 0.0% | 0.0% | 0.0% | **12.2** |
| event-rate rules (all 4) | 65.5% | 62.2% | 60.8% | 54.7% | 50.0% | 67.6% | 30.4% | 51.4% | 13.5% | 10.8% | 38.8% | 8.6% | **0.0** |
| event-rate rules (conservative: 3, no press-without-move) | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| cheap checks: webdriver OR isTrusted OR conservative rules | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| model OR cheap checks | 92.6% | 52.0% | 53.4% | 60.1% | 84.5% | 74.3% | 85.8% | 60.1% | 5.4% | 31.8% | 2.7% | 1.1% | **0.0** |
| motorprint model @ worst-group-1% thr (0.677) | 87.8% | 52.0% | 53.4% | 56.8% | 81.8% | 72.3% | 85.1% | 60.1% | 3.4% | 31.1% | 1.0% | 0.4% | **58.4** |

## Model detail per tool

| tool | sessions | median length | no scorable window | webdriver=true | window det @thr | session det @thr | window TPR @1% / 0.1% FPR | session TPR @1% / 0.1% FPR | window AUC | session AUC | median time to detect | detected ≤2 s / ≤5 s | by task (form/nav/read/search) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ghost-cursor | 148 | 5.7 s | 0 | 0.0% | 70.7% | 92.6% | 78.4% / 64.2% | 93.9% / 71.6% | 0.985 | 0.997 | 2.5 s | 41.9% / 89.9% | 100.0% / 86.5% / 83.8% / 100.0% |
| puppeteer-stealth | 148 | 0.5 s | 0 | 0.0% | 39.5% | 52.0% | 51.0% / 31.8% | 52.0% / 51.4% | 0.949 | 0.980 | 0.5 s | 52.0% / 52.0% | 100.0% / 8.1% / 0.0% / 100.0% |
| playwright-stealth | 148 | 0.4 s | 0 | 0.0% | 40.3% | 53.4% | 50.7% / 31.6% | 53.4% / 52.7% | 0.950 | 0.980 | 0.5 s | 53.4% / 53.4% | 100.0% / 13.5% / 0.0% / 100.0% |
| undetected-chromedriver | 148 | 0.7 s | 0 | 0.0% | 43.3% | 58.1% | 50.5% / 32.7% | 58.1% / 45.3% | 0.949 | 0.978 | 0.5 s | 58.1% / 58.1% | 100.0% / 40.5% / 0.0% / 91.9% |
| nodriver | 148 | 1.7 s | 0 | 0.0% | 70.4% | 84.5% | 73.0% / 67.2% | 85.1% / 73.0% | 0.980 | 0.990 | 0.5 s | 79.1% / 84.5% | 100.0% / 100.0% / 37.8% / 100.0% |
| botasaurus-human | 148 | 4.7 s | 0 | 0.0% | 48.5% | 74.3% | 55.4% / 36.7% | 74.3% / 58.8% | 0.955 | 0.969 | 2.0 s | 37.8% / 73.6% | 100.0% / 0.0% / 97.3% / 100.0% |
| pyautogui | 148 | 2.7 s | 0 | 0.0% | 73.3% | 85.8% | 74.0% / 69.8% | 85.8% / 75.0% | 0.963 | 0.990 | 0.5 s | 85.8% / 85.8% | 100.0% / 100.0% / 43.2% / 100.0% |
| playwright-mcp | 148 | 9.3 s | 0 | 0.0% | 55.0% | 60.1% | 70.3% / 42.3% | 60.1% / 57.4% | 0.993 | 0.986 | 3.0 s | 14.2% / 33.1% | 100.0% / 0.0% / 100.0% / 40.5% |
| replay-cdp | 148 | 9.8 s | 0 | 0.0% | 2.7% | 4.7% | 3.4% / 1.7% | 4.7% / 2.0% | 0.569 | 0.556 | 7.5 s | 0.7% / 2.0% | 1.9% / – / 6.4% / – |
| replay-xdotool | 148 | 9.9 s | 2 | 0.0% | 17.3% | 31.8% | 19.7% / 15.5% | 31.8% / 31.1% | 0.642 | 0.641 | 0.5 s | 31.1% / 31.1% | 46.3% / – / 23.4% / – |

## Humans: false-positive rate by dataset

Leave-users-out = the shipped model on its held-out test users. Leave-one-dataset-out = the same recipe (best config, int8, thr 0.5) retrained without that dataset, scored on all of its users.

| dataset | LUO window FPR | LUO session FPR (10 s) | LODO window FPR | LODO session FPR | event-rate rule session FPR |
|---|---|---|---|---|---|
| adserp | 1.3% | 2.7% | 25.6% | 47.0% | 1.0% |
| boun | 0.0% | 0.0% | 3.3% | 4.7% | 38.8% |
| cmu | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| dux | 0.7% | 0.2% | 4.8% | 10.1% | 31.4% |
| keyrecs | 0.6% | 1.4% | 1.9% | 3.1% | 0.0% |
| mousetask | 0.0% | 0.2% | 0.0% | 0.0% | 0.0% |
| **worst** | **1.3%** | **2.7%** | **25.6%** | **47.0%** | 38.8% |

Thresholds on pooled test humans: window 0.220 (1% FPR) / 0.854 (0.1%); session 0.465 / 0.926; worst-group-1% session threshold 0.677.

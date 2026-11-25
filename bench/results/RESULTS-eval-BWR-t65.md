# motorprint bench results (eval-BWR-t65)

1480 bot sessions (eval half) from 10 tools; human test set = 2547 ten-second segments from 79 held-out users (leave-users-out) across 6 datasets. Model threshold 0.65.

## Headline: session-level detection per tool

**Bench score** = mean session detection rate over the tools, at an operating point where the *worst* human dataset has at most 1% session FPR (0 if the detector cannot get there).

| detector | ghost-cursor | pptr-stealth | pw-stealth | uc-selenium | nodriver | botasaurus | pyautogui | pw-MCP | replay-CDP | replay-xdo | worst-group session FPR | pooled session FPR | **bench score** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| motorprint model @ shipped thr | 78.4% | 48.6% | 49.3% | 29.1% | 49.3% | 67.6% | 85.8% | 45.9% | 3.4% | 31.1% | 0.5% | 0.2% | **48.9** |
| navigator.webdriver | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | **0.0** |
| isTrusted check | 25.0% | 25.0% | 25.0% | 25.0% | 0.0% | 0.0% | 0.0% | 21.6% | 0.0% | 0.0% | 0.0% | 0.0% | **12.2** |
| event-rate rules (all 4) | 65.5% | 62.2% | 60.8% | 54.7% | 50.0% | 67.6% | 30.4% | 51.4% | 13.5% | 10.8% | 38.8% | 8.6% | **0.0** |
| event-rate rules (conservative: 3, no press-without-move) | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| cheap checks: webdriver OR isTrusted OR conservative rules | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| model OR cheap checks | 78.4% | 50.0% | 50.0% | 50.0% | 52.0% | 70.3% | 85.8% | 49.3% | 4.1% | 31.1% | 0.9% | 0.3% | **52.1** |
| motorprint model @ worst-group-1% thr (0.550) | 82.4% | 50.7% | 52.7% | 37.2% | 51.4% | 71.6% | 85.8% | 45.9% | 3.4% | 31.1% | 1.1% | 0.3% | **51.2** |

## Model detail per tool

| tool | sessions | median length | no scorable window | webdriver=true | window det @thr | session det @thr | window TPR @1% / 0.1% FPR | session TPR @1% / 0.1% FPR | window AUC | session AUC | median time to detect | detected ≤2 s / ≤5 s | by task (form/nav/read/search) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ghost-cursor | 148 | 5.7 s | 0 | 0.0% | 71.2% | 78.4% | 84.0% / 68.6% | 92.6% / 73.0% | 0.983 | 0.996 | 1.5 s | 54.7% / 76.4% | 100.0% / 81.1% / 32.4% / 100.0% |
| puppeteer-stealth | 148 | 0.5 s | 0 | 0.0% | 25.2% | 48.6% | 36.7% / 23.1% | 52.0% / 41.9% | 0.623 | 0.819 | 0.5 s | 48.6% / 48.6% | 100.0% / 0.0% / 0.0% / 94.6% |
| playwright-stealth | 148 | 0.4 s | 0 | 0.0% | 25.3% | 49.3% | 37.2% / 25.0% | 53.4% / 48.6% | 0.629 | 0.819 | 0.5 s | 49.3% / 49.3% | 100.0% / 0.0% / 0.0% / 97.3% |
| undetected-chromedriver | 148 | 0.7 s | 0 | 0.0% | 18.7% | 29.1% | 37.7% / 18.7% | 48.6% / 27.0% | 0.659 | 0.803 | 0.5 s | 29.1% / 29.1% | 100.0% / 0.0% / 0.0% / 16.2% |
| nodriver | 148 | 1.7 s | 0 | 0.0% | 49.8% | 49.3% | 63.6% / 46.0% | 64.9% / 40.5% | 0.774 | 0.942 | 0.5 s | 48.6% / 49.3% | 94.6% / 8.1% / 0.0% / 94.6% |
| botasaurus-human | 148 | 4.7 s | 0 | 0.0% | 40.5% | 67.6% | 65.7% / 36.2% | 89.2% / 60.1% | 0.961 | 0.996 | 2.5 s | 26.4% / 67.6% | 100.0% / 0.0% / 81.1% / 89.2% |
| pyautogui | 148 | 2.7 s | 0 | 0.0% | 68.4% | 85.8% | 71.1% / 66.3% | 85.8% / 85.1% | 0.967 | 0.987 | 1.5 s | 81.1% / 85.8% | 100.0% / 100.0% / 43.2% / 100.0% |
| playwright-mcp | 148 | 9.3 s | 0 | 0.0% | 30.5% | 45.9% | 42.6% / 30.3% | 58.8% / 45.3% | 0.977 | 0.957 | 7.8 s | 6.8% / 17.6% | 86.5% / 0.0% / 94.6% / 2.7% |
| replay-cdp | 148 | 9.8 s | 0 | 0.0% | 1.9% | 3.4% | 4.3% / 1.5% | 5.4% / 1.4% | 0.585 | 0.581 | 4.5 s | 0.0% / 2.0% | 1.9% / – / 4.3% / – |
| replay-xdotool | 148 | 9.9 s | 2 | 0.0% | 15.9% | 31.1% | 20.1% / 15.6% | 31.8% / 31.1% | 0.651 | 0.651 | 0.5 s | 31.1% / 31.1% | 44.4% / – / 23.4% / – |

## Humans: false-positive rate by dataset

Leave-users-out = the shipped model on its held-out test users. Leave-one-dataset-out = the same recipe (best config, int8, thr 0.5) retrained without that dataset, scored on all of its users.

| dataset | LUO window FPR | LUO session FPR (10 s) | LODO window FPR | LODO session FPR | event-rate rule session FPR |
|---|---|---|---|---|---|
| adserp | 0.0% | 0.2% | 23.7% | 43.7% | 1.0% |
| boun | 0.0% | 0.0% | 3.3% | 4.7% | 38.8% |
| cmu | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| dux | 0.3% | 0.0% | 4.8% | 10.1% | 31.4% |
| keyrecs | 0.4% | 0.5% | 1.9% | 3.1% | 0.0% |
| mousetask | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **worst** | **0.4%** | **0.5%** | **23.7%** | **43.7%** | 38.8% |

Thresholds on pooled test humans: window 0.105 (1% FPR) / 0.758 (0.1%); session 0.166 / 0.792; worst-group-1% session threshold 0.550.

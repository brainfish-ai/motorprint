# motorprint bench results (eval-B)

1480 bot sessions (eval half) from 10 tools; human test set = 2547 ten-second segments from 79 held-out users (leave-users-out) across 6 datasets. Model threshold 0.5.

## Headline: session-level detection per tool

**Bench score** = mean session detection rate over the tools, at an operating point where the *worst* human dataset has at most 1% session FPR (0 if the detector cannot get there).

| detector | ghost-cursor | pptr-stealth | pw-stealth | uc-selenium | nodriver | botasaurus | pyautogui | pw-MCP | replay-CDP | replay-xdo | worst-group session FPR | pooled session FPR | **bench score** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| motorprint model @ shipped thr | 82.4% | 51.4% | 52.7% | 38.5% | 52.7% | 69.6% | 75.0% | 46.6% | 3.4% | 31.8% | 1.4% | 0.4% | **0.0** |
| navigator.webdriver | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | **0.0** |
| isTrusted check | 25.0% | 25.0% | 25.0% | 25.0% | 0.0% | 0.0% | 0.0% | 21.6% | 0.0% | 0.0% | 0.0% | 0.0% | **12.2** |
| event-rate rules (all 4) | 65.5% | 62.2% | 60.8% | 54.7% | 50.0% | 67.6% | 30.4% | 51.4% | 13.5% | 10.8% | 38.8% | 8.6% | **0.0** |
| event-rate rules (conservative: 3, no press-without-move) | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| cheap checks: webdriver OR isTrusted OR conservative rules | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| model OR cheap checks | 82.4% | 52.0% | 53.4% | 58.1% | 54.1% | 70.9% | 75.0% | 50.0% | 4.1% | 31.8% | 1.4% | 0.5% | **0.0** |
| motorprint model @ worst-group-1% thr (0.550) | 81.1% | 50.7% | 52.7% | 37.2% | 51.4% | 65.5% | 75.0% | 45.9% | 3.4% | 31.1% | 1.1% | 0.3% | **49.4** |

## Model detail per tool

| tool | sessions | median length | no scorable window | webdriver=true | window det @thr | session det @thr | window TPR @1% / 0.1% FPR | session TPR @1% / 0.1% FPR | window AUC | session AUC | median time to detect | detected ≤2 s / ≤5 s | by task (form/nav/read/search) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ghost-cursor | 148 | 5.7 s | 0 | 0.0% | 74.2% | 82.4% | 83.1% / 68.1% | 91.9% / 73.0% | 0.985 | 0.993 | 1.5 s | 60.1% / 81.1% | 100.0% / 89.2% / 40.5% / 100.0% |
| puppeteer-stealth | 148 | 0.5 s | 0 | 0.0% | 26.6% | 51.4% | 36.7% / 23.1% | 52.0% / 41.9% | 0.877 | 0.945 | 0.5 s | 51.4% / 51.4% | 100.0% / 8.1% / 0.0% / 97.3% |
| playwright-stealth | 148 | 0.4 s | 0 | 0.0% | 27.1% | 52.7% | 36.8% / 25.0% | 53.4% / 48.6% | 0.881 | 0.946 | 0.5 s | 52.7% / 52.7% | 100.0% / 13.5% / 0.0% / 97.3% |
| undetected-chromedriver | 148 | 0.7 s | 0 | 0.0% | 23.1% | 38.5% | 37.1% / 18.7% | 48.6% / 27.0% | 0.876 | 0.939 | 0.5 s | 38.5% / 38.5% | 100.0% / 32.4% / 0.0% / 21.6% |
| nodriver | 148 | 1.7 s | 0 | 0.0% | 50.9% | 52.7% | 59.2% / 44.2% | 64.9% / 40.5% | 0.950 | 0.959 | 0.5 s | 52.0% / 52.7% | 97.3% / 16.2% / 0.0% / 97.3% |
| botasaurus-human | 148 | 4.7 s | 0 | 0.0% | 46.8% | 69.6% | 64.7% / 36.1% | 88.5% / 56.1% | 0.957 | 0.995 | 2.5 s | 31.8% / 68.9% | 100.0% / 8.1% / 75.7% / 94.6% |
| pyautogui | 148 | 2.7 s | 0 | 0.0% | 66.3% | 75.0% | 67.2% / 64.0% | 75.0% / 74.3% | 0.895 | 0.975 | 1.5 s | 72.3% / 75.0% | 100.0% / 100.0% / 0.0% / 100.0% |
| playwright-mcp | 148 | 9.3 s | 0 | 0.0% | 31.4% | 46.6% | 42.6% / 30.3% | 58.8% / 45.3% | 0.977 | 0.944 | 7.5 s | 6.8% / 18.2% | 86.5% / 0.0% / 97.3% / 2.7% |
| replay-cdp | 148 | 9.8 s | 0 | 0.0% | 2.4% | 3.4% | 4.2% / 1.5% | 5.4% / 1.4% | 0.571 | 0.558 | 4.5 s | 0.7% / 2.7% | 1.9% / – / 4.3% / – |
| replay-xdotool | 148 | 9.9 s | 2 | 0.0% | 16.7% | 31.8% | 20.1% / 15.6% | 31.8% / 31.1% | 0.642 | 0.636 | 0.5 s | 31.1% / 31.1% | 46.3% / – / 23.4% / – |

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

Thresholds on pooled test humans: window 0.108 (1% FPR) / 0.758 (0.1%); session 0.166 / 0.792; worst-group-1% session threshold 0.550.

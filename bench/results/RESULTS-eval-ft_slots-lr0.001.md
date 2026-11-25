# motorprint bench results (eval-ft_slots-lr0.001)

1480 bot sessions (eval half) from 10 tools; human test set = 2547 ten-second segments from 79 held-out users (leave-users-out) across 6 datasets. Model threshold 0.5.

## Headline: session-level detection per tool

**Bench score** = mean session detection rate over the tools, at an operating point where the *worst* human dataset has at most 1% session FPR (0 if the detector cannot get there).

| detector | ghost-cursor | pptr-stealth | pw-stealth | uc-selenium | nodriver | botasaurus | pyautogui | pw-MCP | replay-CDP | replay-xdo | worst-group session FPR | pooled session FPR | **bench score** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| motorprint model @ shipped thr | 98.0% | 75.0% | 75.0% | 73.6% | 87.8% | 88.5% | 88.5% | 74.3% | 6.1% | 31.8% | 2.1% | 1.0% | **0.0** |
| navigator.webdriver | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | **0.0** |
| isTrusted check | 25.0% | 25.0% | 25.0% | 25.0% | 0.0% | 0.0% | 0.0% | 21.6% | 0.0% | 0.0% | 0.0% | 0.0% | **12.2** |
| event-rate rules (all 4) | 65.5% | 62.2% | 60.8% | 54.7% | 50.0% | 67.6% | 30.4% | 51.4% | 13.5% | 10.8% | 38.8% | 8.6% | **0.0** |
| event-rate rules (conservative: 3, no press-without-move) | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| cheap checks: webdriver OR isTrusted OR conservative rules | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| model OR cheap checks | 98.0% | 75.0% | 75.0% | 75.0% | 87.8% | 88.5% | 88.5% | 74.3% | 6.8% | 31.8% | 2.1% | 1.2% | **0.0** |
| motorprint model @ worst-group-1% thr (0.798) | 98.0% | 52.0% | 53.4% | 58.1% | 84.5% | 80.4% | 85.8% | 62.8% | 5.4% | 31.1% | 1.0% | 0.4% | **61.1** |

## Model detail per tool

| tool | sessions | median length | no scorable window | webdriver=true | window det @thr | session det @thr | window TPR @1% / 0.1% FPR | session TPR @1% / 0.1% FPR | window AUC | session AUC | median time to detect | detected ≤2 s / ≤5 s | by task (form/nav/read/search) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ghost-cursor | 148 | 5.7 s | 0 | 0.0% | 84.9% | 98.0% | 88.2% / 76.9% | 98.0% / 82.4% | 0.993 | 0.999 | 1.0 s | 84.5% / 98.0% | 100.0% / 100.0% / 91.9% / 100.0% |
| puppeteer-stealth | 148 | 0.5 s | 0 | 0.0% | 51.7% | 75.0% | 51.7% / 39.2% | 75.0% / 51.4% | 0.964 | 0.990 | 0.5 s | 75.0% / 75.0% | 100.0% / 100.0% / 0.0% / 100.0% |
| playwright-stealth | 148 | 0.4 s | 0 | 0.0% | 51.4% | 75.0% | 51.4% / 40.3% | 75.0% / 52.7% | 0.965 | 0.990 | 0.5 s | 75.0% / 75.0% | 100.0% / 100.0% / 0.0% / 100.0% |
| undetected-chromedriver | 148 | 0.7 s | 0 | 0.0% | 50.8% | 73.6% | 51.1% / 43.0% | 73.6% / 35.1% | 0.966 | 0.989 | 0.5 s | 73.6% / 73.6% | 100.0% / 100.0% / 0.0% / 94.6% |
| nodriver | 148 | 1.7 s | 0 | 0.0% | 71.9% | 87.8% | 73.2% / 70.0% | 87.8% / 71.6% | 0.982 | 0.991 | 0.5 s | 81.1% / 87.8% | 100.0% / 100.0% / 51.4% / 100.0% |
| botasaurus-human | 148 | 4.7 s | 0 | 0.0% | 68.7% | 88.5% | 74.1% / 57.4% | 88.5% / 66.9% | 0.983 | 0.993 | 1.5 s | 80.4% / 87.8% | 100.0% / 54.1% / 100.0% / 100.0% |
| pyautogui | 148 | 2.7 s | 0 | 0.0% | 76.0% | 88.5% | 79.9% / 74.3% | 88.5% / 75.0% | 0.982 | 0.994 | 0.5 s | 86.5% / 88.5% | 100.0% / 100.0% / 54.1% / 100.0% |
| playwright-mcp | 148 | 9.3 s | 0 | 0.0% | 68.9% | 74.3% | 97.8% / 53.6% | 74.3% / 58.1% | 0.998 | 0.996 | 3.0 s | 25.0% / 39.9% | 100.0% / 54.1% / 100.0% / 43.2% |
| replay-cdp | 148 | 9.8 s | 0 | 0.0% | 3.2% | 6.1% | 4.5% / 1.9% | 6.1% / 1.4% | 0.578 | 0.567 | 4.0 s | 1.4% / 4.7% | 1.9% / – / 8.5% / – |
| replay-xdotool | 148 | 9.9 s | 2 | 0.0% | 18.1% | 31.8% | 19.8% / 15.7% | 31.8% / 31.1% | 0.646 | 0.642 | 0.5 s | 31.1% / 31.1% | 46.3% / – / 23.4% / – |

## Humans: false-positive rate by dataset

Leave-users-out = the shipped model on its held-out test users. Leave-one-dataset-out = the same recipe (best config, int8, thr 0.5) retrained without that dataset, scored on all of its users.

| dataset | LUO window FPR | LUO session FPR (10 s) | LODO window FPR | LODO session FPR | event-rate rule session FPR |
|---|---|---|---|---|---|
| adserp | 1.2% | 2.1% | 25.6% | 47.0% | 1.0% |
| boun | 0.0% | 0.0% | 3.3% | 4.7% | 38.8% |
| cmu | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| dux | 0.8% | 0.5% | 4.8% | 10.1% | 31.4% |
| keyrecs | 0.7% | 2.0% | 1.9% | 3.1% | 0.0% |
| mousetask | 0.0% | 0.6% | 0.0% | 0.0% | 0.0% |
| **worst** | **1.2%** | **2.1%** | **25.6%** | **47.0%** | 38.8% |

Thresholds on pooled test humans: window 0.271 (1% FPR) / 0.933 (0.1%); session 0.514 / 0.997; worst-group-1% session threshold 0.798.

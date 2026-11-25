# motorprint bench results (eval-ft_masked-lr0.001)

1480 bot sessions (eval half) from 10 tools; human test set = 2547 ten-second segments from 79 held-out users (leave-users-out) across 6 datasets. Model threshold 0.5.

## Headline: session-level detection per tool

**Bench score** = mean session detection rate over the tools, at an operating point where the *worst* human dataset has at most 1% session FPR (0 if the detector cannot get there).

| detector | ghost-cursor | pptr-stealth | pw-stealth | uc-selenium | nodriver | botasaurus | pyautogui | pw-MCP | replay-CDP | replay-xdo | worst-group session FPR | pooled session FPR | **bench score** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| motorprint model @ shipped thr | 99.3% | 100.0% | 100.0% | 98.6% | 99.3% | 100.0% | 100.0% | 100.0% | 13.5% | 36.5% | 41.6% | 11.4% | **0.0** |
| navigator.webdriver | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | **0.0** |
| isTrusted check | 25.0% | 25.0% | 25.0% | 25.0% | 0.0% | 0.0% | 0.0% | 21.6% | 0.0% | 0.0% | 0.0% | 0.0% | **12.2** |
| event-rate rules (all 4) | 65.5% | 62.2% | 60.8% | 54.7% | 50.0% | 67.6% | 30.4% | 51.4% | 13.5% | 10.8% | 38.8% | 8.6% | **0.0** |
| event-rate rules (conservative: 3, no press-without-move) | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| cheap checks: webdriver OR isTrusted OR conservative rules | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| model OR cheap checks | 99.3% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 14.2% | 36.5% | 41.6% | 11.6% | **0.0** |
| motorprint model @ worst-group-1% thr (0.986) | 91.9% | 29.1% | 47.3% | 41.2% | 74.3% | 89.9% | 87.8% | 60.8% | 1.4% | 31.1% | 1.1% | 0.5% | **55.5** |

## Model detail per tool

| tool | sessions | median length | no scorable window | webdriver=true | window det @thr | session det @thr | window TPR @1% / 0.1% FPR | session TPR @1% / 0.1% FPR | window AUC | session AUC | median time to detect | detected ≤2 s / ≤5 s | by task (form/nav/read/search) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ghost-cursor | 148 | 5.7 s | 0 | 0.0% | 97.3% | 99.3% | 94.2% / 81.9% | 98.6% / 75.7% | 0.997 | 0.998 | 0.5 s | 96.6% / 99.3% | 100.0% / 100.0% / 97.3% / 100.0% |
| puppeteer-stealth | 148 | 0.5 s | 0 | 0.0% | 100.0% | 100.0% | 64.7% / 41.6% | 74.3% / 5.4% | 0.994 | 0.991 | 0.5 s | 100.0% / 100.0% | 100.0% / 100.0% / 100.0% / 100.0% |
| playwright-stealth | 148 | 0.4 s | 0 | 0.0% | 100.0% | 100.0% | 64.9% / 47.2% | 74.3% / 31.1% | 0.994 | 0.993 | 0.5 s | 100.0% / 100.0% | 100.0% / 100.0% / 100.0% / 100.0% |
| undetected-chromedriver | 148 | 0.7 s | 0 | 0.0% | 99.4% | 98.6% | 67.6% / 40.8% | 68.2% / 26.4% | 0.993 | 0.990 | 0.5 s | 98.6% / 98.6% | 100.0% / 100.0% / 100.0% / 94.6% |
| nodriver | 148 | 1.7 s | 0 | 0.0% | 94.9% | 99.3% | 74.5% / 66.8% | 93.2% / 62.8% | 0.993 | 0.996 | 0.5 s | 99.3% / 99.3% | 100.0% / 100.0% / 100.0% / 97.3% |
| botasaurus-human | 148 | 4.7 s | 0 | 0.0% | 94.9% | 100.0% | 92.9% / 77.0% | 99.3% / 68.9% | 0.994 | 0.998 | 0.5 s | 97.3% / 100.0% | 100.0% / 100.0% / 100.0% / 100.0% |
| pyautogui | 148 | 2.7 s | 0 | 0.0% | 98.0% | 100.0% | 93.4% / 78.3% | 96.6% / 85.8% | 0.998 | 0.998 | 0.5 s | 100.0% / 100.0% | 100.0% / 100.0% / 100.0% / 100.0% |
| playwright-mcp | 148 | 9.3 s | 0 | 0.0% | 100.0% | 100.0% | 99.2% / 67.6% | 100.0% / 45.3% | 0.999 | 0.997 | 1.5 s | 50.0% / 75.0% | 100.0% / 100.0% / 100.0% / 100.0% |
| replay-cdp | 148 | 9.8 s | 0 | 0.0% | 6.9% | 13.5% | 3.5% / 0.9% | 2.7% / 1.4% | 0.570 | 0.551 | 1.2 s | 8.1% / 10.8% | 0.0% / – / 21.3% / – |
| replay-xdotool | 148 | 9.9 s | 2 | 0.0% | 20.3% | 36.5% | 17.7% / 13.7% | 31.8% / 31.1% | 0.615 | 0.666 | 0.5 s | 35.1% / 35.1% | 44.4% / – / 31.9% / – |

## Humans: false-positive rate by dataset

Leave-users-out = the shipped model on its held-out test users. Leave-one-dataset-out = the same recipe (best config, int8, thr 0.5) retrained without that dataset, scored on all of its users.

| dataset | LUO window FPR | LUO session FPR (10 s) | LODO window FPR | LODO session FPR | event-rate rule session FPR |
|---|---|---|---|---|---|
| adserp | 18.2% | 41.6% | 25.6% | 47.0% | 1.0% |
| boun | 1.7% | 5.0% | 3.3% | 4.7% | 38.8% |
| cmu | 0.4% | 2.3% | 0.0% | 0.0% | 0.0% |
| dux | 0.5% | 1.6% | 4.8% | 10.1% | 31.4% |
| keyrecs | 0.2% | 0.7% | 1.9% | 3.1% | 0.0% |
| mousetask | 2.6% | 11.5% | 0.0% | 0.0% | 0.0% |
| **worst** | **18.2%** | **41.6%** | **25.6%** | **47.0%** | 38.8% |

Thresholds on pooled test humans: window 0.688 (1% FPR) / 0.979 (0.1%); session 0.908 / 0.998; worst-group-1% session threshold 0.986.

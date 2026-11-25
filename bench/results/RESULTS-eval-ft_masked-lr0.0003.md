# motorprint bench results (eval-ft_masked-lr0.0003)

1480 bot sessions (eval half) from 10 tools; human test set = 2547 ten-second segments from 79 held-out users (leave-users-out) across 6 datasets. Model threshold 0.5.

## Headline: session-level detection per tool

**Bench score** = mean session detection rate over the tools, at an operating point where the *worst* human dataset has at most 1% session FPR (0 if the detector cannot get there).

| detector | ghost-cursor | pptr-stealth | pw-stealth | uc-selenium | nodriver | botasaurus | pyautogui | pw-MCP | replay-CDP | replay-xdo | worst-group session FPR | pooled session FPR | **bench score** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| motorprint model @ shipped thr | 100.0% | 100.0% | 99.3% | 83.8% | 100.0% | 98.6% | 100.0% | 100.0% | 16.9% | 37.2% | 47.2% | 10.8% | **0.0** |
| navigator.webdriver | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | **0.0** |
| isTrusted check | 25.0% | 25.0% | 25.0% | 25.0% | 0.0% | 0.0% | 0.0% | 21.6% | 0.0% | 0.0% | 0.0% | 0.0% | **12.2** |
| event-rate rules (all 4) | 65.5% | 62.2% | 60.8% | 54.7% | 50.0% | 67.6% | 30.4% | 51.4% | 13.5% | 10.8% | 38.8% | 8.6% | **0.0** |
| event-rate rules (conservative: 3, no press-without-move) | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| cheap checks: webdriver OR isTrusted OR conservative rules | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 50.0% | 25.0% | 25.0% | 1.4% | 0.0% | 0.9% | 0.2% | **35.1** |
| model OR cheap checks | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 98.6% | 100.0% | 100.0% | 17.6% | 37.2% | 47.2% | 11.0% | **0.0** |
| motorprint model @ worst-group-1% thr (0.991) | 93.2% | 18.9% | 40.5% | 37.2% | 76.4% | 73.6% | 86.5% | 60.1% | 2.7% | 31.1% | 1.0% | 0.4% | **52.0** |

## Model detail per tool

| tool | sessions | median length | no scorable window | webdriver=true | window det @thr | session det @thr | window TPR @1% / 0.1% FPR | session TPR @1% / 0.1% FPR | window AUC | session AUC | median time to detect | detected ≤2 s / ≤5 s | by task (form/nav/read/search) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ghost-cursor | 148 | 5.7 s | 0 | 0.0% | 93.5% | 100.0% | 88.0% / 71.4% | 96.6% / 65.5% | 0.991 | 0.997 | 0.5 s | 92.6% / 100.0% | 100.0% / 100.0% / 100.0% / 100.0% |
| puppeteer-stealth | 148 | 0.5 s | 0 | 0.0% | 74.1% | 100.0% | 48.3% / 22.4% | 63.5% / 0.7% | 0.973 | 0.985 | 0.5 s | 100.0% / 100.0% | 100.0% / 100.0% / 100.0% / 100.0% |
| playwright-stealth | 148 | 0.4 s | 0 | 0.0% | 73.3% | 99.3% | 51.0% / 33.3% | 72.3% / 27.7% | 0.975 | 0.990 | 0.5 s | 99.3% / 99.3% | 100.0% / 100.0% / 100.0% / 97.3% |
| undetected-chromedriver | 148 | 0.7 s | 0 | 0.0% | 63.9% | 83.8% | 41.7% / 33.6% | 53.4% / 25.7% | 0.969 | 0.961 | 0.5 s | 83.8% / 83.8% | 100.0% / 100.0% / 100.0% / 35.1% |
| nodriver | 148 | 1.7 s | 0 | 0.0% | 99.4% | 100.0% | 75.1% / 71.7% | 91.9% / 71.6% | 0.990 | 0.997 | 0.5 s | 100.0% / 100.0% | 100.0% / 100.0% / 100.0% / 100.0% |
| botasaurus-human | 148 | 4.7 s | 0 | 0.0% | 81.7% | 98.6% | 72.1% / 50.0% | 89.2% / 51.4% | 0.972 | 0.991 | 1.5 s | 84.5% / 97.3% | 100.0% / 94.6% / 100.0% / 100.0% |
| pyautogui | 148 | 2.7 s | 0 | 0.0% | 87.0% | 100.0% | 82.8% / 70.4% | 92.6% / 75.0% | 0.969 | 0.996 | 0.5 s | 100.0% / 100.0% | 100.0% / 100.0% / 100.0% / 100.0% |
| playwright-mcp | 148 | 9.3 s | 0 | 0.0% | 100.0% | 100.0% | 98.1% / 42.8% | 73.6% / 45.3% | 0.997 | 0.995 | 1.5 s | 50.0% / 75.0% | 100.0% / 100.0% / 100.0% / 100.0% |
| replay-cdp | 148 | 9.8 s | 0 | 0.0% | 8.1% | 16.9% | 3.4% / 1.6% | 6.1% / 1.4% | 0.571 | 0.559 | 3.0 s | 8.1% / 10.8% | 1.9% / – / 25.5% / – |
| replay-xdotool | 148 | 9.9 s | 2 | 0.0% | 21.9% | 37.2% | 17.9% / 14.5% | 31.1% / 31.1% | 0.624 | 0.667 | 0.5 s | 35.1% / 35.8% | 44.4% / – / 33.0% / – |

## Humans: false-positive rate by dataset

Leave-users-out = the shipped model on its held-out test users. Leave-one-dataset-out = the same recipe (best config, int8, thr 0.5) retrained without that dataset, scored on all of its users.

| dataset | LUO window FPR | LUO session FPR (10 s) | LODO window FPR | LODO session FPR | event-rate rule session FPR |
|---|---|---|---|---|---|
| adserp | 26.3% | 47.2% | 25.6% | 47.0% | 1.0% |
| boun | 5.6% | 8.5% | 3.3% | 4.7% | 38.8% |
| cmu | 0.2% | 1.5% | 0.0% | 0.0% | 0.0% |
| dux | 1.2% | 2.6% | 4.8% | 10.1% | 31.4% |
| keyrecs | 0.3% | 0.9% | 1.9% | 3.1% | 0.0% |
| mousetask | 0.3% | 1.9% | 0.0% | 0.0% | 0.0% |
| **worst** | **26.3%** | **47.2%** | **25.6%** | **47.0%** | 38.8% |

Thresholds on pooled test humans: window 0.881 (1% FPR) / 0.995 (0.1%); session 0.946 / 0.999; worst-group-1% session threshold 0.991.

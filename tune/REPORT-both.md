# motorprint tuning report (both humans, both)

Generated 2026-11-25 17:26 AEDT. Every individual run: tune/runs.jsonl (RUNS.md).

Test = held-out sessions of the 5 training bot styles + held-out human users (both humans; window level, threshold 0.5 except 5_calibrated and ref_*).
Held-out styles = ghost-cursor-like, WindMouse and AI-agent bots never seen in training, scored against the same human test windows.
Real-human FPR = share of 3 s windows from held-out real users (people never seen in training) that score as bot.
Replay = synthetic human traces replayed through Playwright (an attack the model is NOT expected to catch).

| stage | what | nonzero/params | test acc | test AUC | real-human FPR (held-out users) | held-out AUC | flagged ghost / wind / agent | flagged replay | model KB gz | lib KB gz | µs model / µs feat+model per window |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ref_old_synthetic | previous main model (synthetic humans), thr 0.6955 | 165/321 | 0.8612 | 0.9838 | 0.1617 | 0.8354 | 0.27 / 0.97 / 0.74 | 0.09 | 1.07 | 0.00 | ? / ? |
| 0_baseline | float32 16-8, default hparams | 769/769 | 0.9975 | 0.9999 | 0.0023 | 0.9364 | 0.13 / 0.91 / 0.37 | 0.01 | 3.81 | 7.66 | 1.11 / 76.36 |
| 1_sweep | best of 90 configs by val log-loss: {'hidden': [16], 'lr': 0.01, 'wd': 0.0001, 'noise': 0.0, 'epochs': 30} | 641/641 | 0.9973 | 0.9999 | 0.0025 | 0.9097 | 0.12 / 0.94 / 0.25 | 0.02 | 3.28 | 7.10 | 1.051 / 99.97 |
| 2_soup | greedy_soup (picked by val log-loss among ['single', 'swa', 'uniform_soup', 'greedy_soup', 'best_ingredient', 'sweep_best']) | 641/641 | 0.9944 | 0.9999 | 0.0054 | 0.9094 | 0.17 / 0.96 / 0.29 | 0.03 | 3.28 | 7.10 | 0.932 / 80.79 |
| 3_prune | global magnitude pruning 70% + masked fine-tune | 204/641 | 0.9972 | 0.9999 | 0.0026 | 0.9245 | 0.13 / 0.94 / 0.32 | 0.04 | 1.94 | 5.61 | 0.913 / 82.36 |
| 4_quant | int8 per-row symmetric | 204/641 | 0.9972 | 0.9999 | 0.0026 | 0.9247 | 0.12 / 0.94 / 0.32 | 0.04 | 1.25 | 4.90 | 1.131 / 82.65 |
| 5_calibrated | stage 4 model, threshold 0.300 (<=0.25% FPR on val humans) | 204/641 | 0.9955 | 0.9999 | 0.0043 | 0.9247 | 0.17 / 0.96 / 0.35 | 0.06 | 1.25 | 4.90 | 0.949 / 76.68 |

Shipped: **5_calibrated**


## False-positive rate on held-out human users, per dataset (shipped threshold for 5_calibrated)

- ref_old_synthetic: adserp 26.80% (n=3895), boun 46.95% (n=1753), cmu 0.00% (n=4056), dux 35.18% (n=4898), keyrecs 0.97% (n=6874), mousetask 11.16% (n=3692), synthetic 0.83% (n=4102) | session-level real-human FPR 5.31% of 904 sessions
- 0_baseline: adserp 0.18% (n=3895), boun 0.00% (n=1753), cmu 0.00% (n=4056), dux 0.29% (n=4898), keyrecs 0.54% (n=6874), mousetask 0.00% (n=3692), synthetic 0.37% (n=4102) | session-level real-human FPR 0.00% of 904 sessions
- 1_sweep: adserp 0.21% (n=3895), boun 0.00% (n=1753), cmu 0.00% (n=4056), dux 0.29% (n=4898), keyrecs 0.60% (n=6874), mousetask 0.00% (n=3692), synthetic 0.39% (n=4102) | session-level real-human FPR 0.00% of 904 sessions
- 2_soup: adserp 0.31% (n=3895), boun 0.00% (n=1753), cmu 0.00% (n=4056), dux 0.57% (n=4898), keyrecs 1.40% (n=6874), mousetask 0.00% (n=3692), synthetic 0.73% (n=4102) | session-level real-human FPR 0.00% of 904 sessions
- 3_prune: adserp 0.15% (n=3895), boun 0.00% (n=1753), cmu 0.00% (n=4056), dux 0.29% (n=4898), keyrecs 0.65% (n=6874), mousetask 0.00% (n=3692), synthetic 0.44% (n=4102) | session-level real-human FPR 0.00% of 904 sessions
- 4_quant: adserp 0.18% (n=3895), boun 0.00% (n=1753), cmu 0.00% (n=4056), dux 0.29% (n=4898), keyrecs 0.64% (n=6874), mousetask 0.00% (n=3692), synthetic 0.41% (n=4102) | session-level real-human FPR 0.00% of 904 sessions
- 5_calibrated: adserp 0.46% (n=3895), boun 0.17% (n=1753), cmu 0.00% (n=4056), dux 0.33% (n=4898), keyrecs 1.02% (n=6874), mousetask 0.00% (n=3692), synthetic 0.63% (n=4102) | session-level real-human FPR 0.00% of 904 sessions

## Confusion matrices

- 0_baseline: test TP 292 FN 1 FP 73 TN 29197 | held-out styles TP 1392 FN 1932 (vs same humans FP 73 TN 29197) | session-level test acc 1.000, held-out 0.886
- 1_sweep: test TP 292 FN 1 FP 79 TN 29191 | held-out styles TP 1314 FN 2010 (vs same humans FP 79 TN 29191) | session-level test acc 1.000, held-out 0.877
- 2_soup: test TP 292 FN 1 FP 166 TN 29104 | held-out styles TP 1440 FN 1884 (vs same humans FP 166 TN 29104) | session-level test acc 1.000, held-out 0.881
- 3_prune: test TP 292 FN 1 FP 83 TN 29187 | held-out styles TP 1391 FN 1933 (vs same humans FP 83 TN 29187) | session-level test acc 1.000, held-out 0.883
- 4_quant: test TP 292 FN 1 FP 82 TN 29188 | held-out styles TP 1382 FN 1942 (vs same humans FP 82 TN 29188) | session-level test acc 1.000, held-out 0.883
- 5_calibrated: test TP 292 FN 1 FP 133 TN 29137 | held-out styles TP 1488 FN 1836 (vs same humans FP 133 TN 29137) | session-level test acc 0.999, held-out 0.909

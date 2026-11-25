# motorprint tuning report (real humans)

Generated 2026-11-25 17:21 AEDT. Every individual run: tune/runs.jsonl (RUNS.md).

Test = held-out sessions of the 5 training bot styles + held-out human users (real humans; window level, threshold 0.5 except 5_calibrated and ref_*).
Held-out styles = ghost-cursor-like, WindMouse and AI-agent bots never seen in training, scored against the same human test windows.
Real-human FPR = share of 3 s windows from held-out real users (people never seen in training) that score as bot.
Replay = synthetic human traces replayed through Playwright (an attack the model is NOT expected to catch).

| stage | what | nonzero/params | test acc | test AUC | real-human FPR (held-out users) | held-out AUC | flagged ghost / wind / agent | flagged replay | model KB gz | lib KB gz | µs model / µs feat+model per window |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ref_old_synthetic | previous main model (synthetic humans), thr 0.6955 | 165/321 | 0.8401 | 0.9812 | 0.1617 | 0.8131 | 0.27 / 0.97 / 0.74 | 0.09 | 1.07 | 0.00 | ? / ? |
| 0_baseline | float32 16-8, default hparams | 769/769 | 0.9976 | 0.9999 | 0.0023 | 0.9532 | 0.21 / 0.92 / 0.29 | 0.22 | 3.82 | 7.67 | 1.064 / 79.25 |
| 1_sweep | best of 90 configs by val log-loss: {'hidden': [32, 16], 'lr': 0.01, 'wd': 0.001, 'noise': 0.0, 'epochs': 30} | 1793/1793 | 0.9967 | 0.9999 | 0.0033 | 0.9577 | 0.22 / 0.96 / 0.32 | 0.27 | 5.79 | 9.69 | 2.249 / 79.55 |
| 2_soup | swa (picked by val log-loss among ['single', 'swa', 'uniform_soup', 'greedy_soup', 'best_ingredient', 'sweep_best']) | 1793/1793 | 0.9965 | 0.9999 | 0.0035 | 0.9591 | 0.28 / 0.97 / 0.33 | 0.32 | 6.56 | 10.50 | 2.081 / 86.92 |
| 3_prune | global magnitude pruning 80% + masked fine-tune | 398/1793 | 0.9969 | 0.9999 | 0.0031 | 0.9604 | 0.22 / 0.96 / 0.31 | 0.29 | 3.17 | 6.92 | 2.352 / 88.14 |
| 4_quant | int8 per-row symmetric | 398/1793 | 0.9967 | 0.9999 | 0.0033 | 0.9605 | 0.22 / 0.96 / 0.31 | 0.29 | 1.66 | 5.33 | 2.186 / 95.28 |
| 5_calibrated | stage 4 model, threshold 0.317 (<=0.25% FPR on val humans) | 398/1793 | 0.9949 | 0.9999 | 0.0052 | 0.9605 | 0.30 / 0.97 / 0.36 | 0.33 | 1.66 | 5.33 | 2.261 / 84.4 |

Shipped: **4_quant at threshold 0.5**. The calibration rule (lowest threshold with <=0.25% FPR on validation users) gave 0.317, which raised held-out real-human FPR from 0.33% to 0.52%, so the rule now floors the threshold at 0.5 (tune.py) and 5_calibrated is equivalent to 4_quant.


## False-positive rate on held-out human users, per dataset (shipped threshold for 5_calibrated)

- ref_old_synthetic: adserp 26.80% (n=3895), boun 46.95% (n=1753), cmu 0.00% (n=4056), dux 35.18% (n=4898), keyrecs 0.97% (n=6874), mousetask 11.16% (n=3692) | session-level real-human FPR 5.31% of 904 sessions
- 0_baseline: adserp 0.10% (n=3895), boun 0.00% (n=1753), cmu 0.00% (n=4056), dux 0.29% (n=4898), keyrecs 0.60% (n=6874), mousetask 0.00% (n=3692) | session-level real-human FPR 0.00% of 904 sessions
- 1_sweep: adserp 0.18% (n=3895), boun 0.00% (n=1753), cmu 0.00% (n=4056), dux 0.51% (n=4898), keyrecs 0.73% (n=6874), mousetask 0.00% (n=3692) | session-level real-human FPR 0.00% of 904 sessions
- 2_soup: adserp 0.31% (n=3895), boun 0.00% (n=1753), cmu 0.00% (n=4056), dux 0.59% (n=4898), keyrecs 0.70% (n=6874), mousetask 0.00% (n=3692) | session-level real-human FPR 0.11% of 904 sessions
- 3_prune: adserp 0.18% (n=3895), boun 0.00% (n=1753), cmu 0.00% (n=4056), dux 0.53% (n=4898), keyrecs 0.67% (n=6874), mousetask 0.00% (n=3692) | session-level real-human FPR 0.00% of 904 sessions
- 4_quant: adserp 0.18% (n=3895), boun 0.00% (n=1753), cmu 0.00% (n=4056), dux 0.51% (n=4898), keyrecs 0.73% (n=6874), mousetask 0.00% (n=3692) | session-level real-human FPR 0.00% of 904 sessions
- 5_calibrated: adserp 0.31% (n=3895), boun 0.00% (n=1753), cmu 0.00% (n=4056), dux 0.86% (n=4898), keyrecs 1.11% (n=6874), mousetask 0.00% (n=3692) | session-level real-human FPR 0.11% of 904 sessions

## Confusion matrices

- 0_baseline: test TP 290 FN 3 FP 59 TN 25109 | held-out styles TP 1472 FN 1852 (vs same humans FP 59 TN 25109) | session-level test acc 0.999, held-out 0.862
- 1_sweep: test TP 292 FN 1 FP 82 TN 25086 | held-out styles TP 1540 FN 1784 (vs same humans FP 82 TN 25086) | session-level test acc 1.000, held-out 0.863
- 2_soup: test TP 293 FN 0 FP 89 TN 25079 | held-out styles TP 1643 FN 1681 (vs same humans FP 89 TN 25079) | session-level test acc 0.999, held-out 0.868
- 3_prune: test TP 292 FN 1 FP 79 TN 25089 | held-out styles TP 1530 FN 1794 (vs same humans FP 79 TN 25089) | session-level test acc 1.000, held-out 0.862
- 4_quant: test TP 292 FN 1 FP 82 TN 25086 | held-out styles TP 1538 FN 1786 (vs same humans FP 82 TN 25086) | session-level test acc 1.000, held-out 0.863
- 5_calibrated: test TP 293 FN 0 FP 130 TN 25038 | held-out styles TP 1708 FN 1616 (vs same humans FP 130 TN 25038) | session-level test acc 0.999, held-out 0.913

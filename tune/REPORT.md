# motorprint tuning report

Generated 2026-11-25 15:42 AEDT. Every individual run: tune/runs.jsonl (RUNS.md).

Test = held-out sessions of the 5 training bot styles + held-out synthetic humans (window level, threshold 0.5 except 5_calibrated).
Held-out styles = ghost-cursor-like, WindMouse and AI-agent bots never seen in training, scored against the same human test windows.
Replay = synthetic human traces replayed through Playwright (an attack the model is NOT expected to catch).

| stage | what | nonzero/params | test acc | test AUC | held-out AUC | flagged ghost / wind / agent | flagged replay | model KB gz | lib KB gz | µs model / µs feat+model per window |
|---|---|---|---|---|---|---|---|---|---|---|
| 0_baseline | float32 16-8, default hparams | 769/769 | 0.9958 | 0.9999 | 0.9456 | 0.10 / 0.92 / 0.79 | 0.03 | 3.87 | 7.67 | 0.97 / 57.14 |
| 1_sweep | best of 90 configs by val log-loss: {'hidden': [8], 'lr': 0.003, 'wd': 0.0, 'noise': 0.15, 'epochs': 30} | 321/321 | 0.9880 | 0.9998 | 0.9575 | 0.20 / 0.94 / 0.76 | 0.06 | 2.06 | 5.72 | 0.479 / 78.39 |
| 2_soup | greedy_soup (picked by val log-loss among ['single', 'swa', 'uniform_soup', 'greedy_soup', 'best_ingredient', 'sweep_best']) | 321/321 | 0.9887 | 0.9998 | 0.9569 | 0.18 / 0.93 / 0.75 | 0.05 | 2.06 | 5.72 | 0.477 / 56.38 |
| 3_prune | global magnitude pruning 50% + masked fine-tune | 165/321 | 0.9885 | 0.9998 | 0.9495 | 0.15 / 0.93 / 0.86 | 0.06 | 1.62 | 5.21 | 0.505 / 52.84 |
| 4_quant | int8 per-row symmetric | 165/321 | 0.9890 | 0.9998 | 0.9498 | 0.14 / 0.93 / 0.84 | 0.05 | 1.08 | 4.66 | 0.463 / 54.33 |
| 5_calibrated | stage 4 model, threshold 0.696 (<=0.5% FPR on val humans) | 165/321 | 0.9941 | 0.9998 | 0.9498 | 0.08 / 0.92 / 0.73 | 0.03 | 1.08 | 4.66 | 0.47 / 56.15 |

Shipped: **5_calibrated**

## Confusion matrices (window level)

- 0_baseline: test TP 314 FN 0 FP 17 TN 3746 | held-out styles TP 943 FN 878 (vs same humans FP 17 TN 3746) | session-level test acc 1.000, held-out 0.845
- 1_sweep: test TP 314 FN 0 FP 49 TN 3714 | held-out styles TP 1024 FN 797 (vs same humans FP 49 TN 3714) | session-level test acc 1.000, held-out 0.856
- 2_soup: test TP 314 FN 0 FP 46 TN 3717 | held-out styles TP 998 FN 823 (vs same humans FP 46 TN 3717) | session-level test acc 1.000, held-out 0.853
- 3_prune: test TP 314 FN 0 FP 47 TN 3716 | held-out styles TP 1023 FN 798 (vs same humans FP 47 TN 3716) | session-level test acc 1.000, held-out 0.858
- 4_quant: test TP 314 FN 0 FP 45 TN 3718 | held-out styles TP 1011 FN 810 (vs same humans FP 45 TN 3718) | session-level test acc 1.000, held-out 0.858
- 5_calibrated: test TP 312 FN 2 FP 22 TN 3741 | held-out styles TP 901 FN 920 (vs same humans FP 22 TN 3741) | session-level test acc 1.000, held-out 0.834

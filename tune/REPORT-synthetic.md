# motorprint tuning report (synthetic humans, synthetic)

Generated 2026-11-25 17:09 AEDT. Every individual run: tune/runs.jsonl (RUNS.md).

Test = held-out sessions of the 5 training bot styles + held-out human sessions (synthetic humans; window level, threshold 0.5 except 5_calibrated and ref_*).
Held-out styles = ghost-cursor-like, WindMouse and AI-agent bots never seen in training, scored against the same human test windows.
Real-human FPR = share of 3 s windows from held-out real users (people never seen in training) that score as bot.
Replay = synthetic human traces replayed through Playwright (an attack the model is NOT expected to catch).

| stage | what | nonzero/params | test acc | test AUC | real-human FPR (held-out users) | held-out AUC | flagged ghost / wind / agent | flagged replay | model KB gz | lib KB gz | µs model / µs feat+model per window |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ref_old_synthetic | previous main model (synthetic humans), thr 0.6955 | 165/321 | 0.9960 | 0.9998 | nan | 0.9742 | 0.27 / 0.97 / 0.74 | 0.09 | 1.07 | 0.00 | ? / ? |
| 0_baseline | float32 16-8, default hparams | 769/769 | 0.9949 | 0.9996 | nan | 0.9734 | 0.18 / 0.95 / 0.83 | 0.06 | 3.80 | 7.64 | 1.077 / 81.51 |
| 1_sweep | best of 90 configs by val log-loss: {'hidden': [24, 12], 'lr': 0.01, 'wd': 0.0, 'noise': 0.0, 'epochs': 30} | 1249/1249 | 0.9981 | 0.9999 | nan | 0.9728 | 0.20 / 0.97 / 0.86 | 0.04 | 5.67 | 9.61 | 1.676 / 78.72 |
| 2_soup | greedy_soup (picked by val log-loss among ['single', 'swa', 'uniform_soup', 'greedy_soup', 'best_ingredient', 'sweep_best']) | 1249/1249 | 0.9979 | 0.9999 | nan | 0.9720 | 0.20 / 0.96 / 0.85 | 0.03 | 5.67 | 9.61 | 1.608 / 81.59 |
| 3_prune | global magnitude pruning 70% + masked fine-tune | 401/1249 | 0.9972 | 0.9999 | nan | 0.9781 | 0.17 / 0.97 / 0.99 | 0.04 | 3.04 | 6.77 | 1.666 / 80.27 |
| 4_quant | int4 per-row symmetric | 401/1249 | 0.9967 | 0.9999 | nan | 0.9778 | 0.18 / 0.97 / 0.95 | 0.05 | 1.48 | 5.15 | 1.627 / 75.41 |
| 4b_int8 | int8 per-row (for comparison) | 401/1249 | 0.9972 | 0.9999 | nan | 0.9781 | 0.17 / 0.97 / 0.99 | 0.04 | 1.81 | 5.48 | 1.608 / 77.47 |
| 5_calibrated | stage 4 model, threshold 0.752 (<=0.25% FPR on val humans) | 401/1249 | 0.9979 | 0.9999 | nan | 0.9778 | 0.14 / 0.95 / 0.84 | 0.04 | 1.48 | 5.15 | 1.606 / 78.41 |

Shipped: **5_calibrated**


## False-positive rate on held-out human users, per dataset (shipped threshold for 5_calibrated)

- ref_old_synthetic: synthetic 0.42% (n=3812)
- 0_baseline: synthetic 0.34% (n=3812)
- 1_sweep: synthetic 0.13% (n=3812)
- 2_soup: synthetic 0.16% (n=3812)
- 3_prune: synthetic 0.26% (n=3812)
- 4_quant: synthetic 0.29% (n=3812)
- 4b_int8: synthetic 0.26% (n=3812)
- 5_calibrated: synthetic 0.13% (n=3812)

## Confusion matrices

- 0_baseline: test TP 467 FN 9 FP 13 TN 3799 | held-out styles TP 1905 FN 1419 (vs same humans FP 13 TN 3799) | session-level test acc 1.000, held-out 0.805
- 1_sweep: test TP 473 FN 3 FP 5 TN 3807 | held-out styles TP 1978 FN 1346 (vs same humans FP 5 TN 3807) | session-level test acc 1.000, held-out 0.811
- 2_soup: test TP 473 FN 3 FP 6 TN 3806 | held-out styles TP 1971 FN 1353 (vs same humans FP 6 TN 3806) | session-level test acc 1.000, held-out 0.813
- 3_prune: test TP 474 FN 2 FP 10 TN 3802 | held-out styles TP 2045 FN 1279 (vs same humans FP 10 TN 3802) | session-level test acc 1.000, held-out 0.819
- 4_quant: test TP 473 FN 3 FP 11 TN 3801 | held-out styles TP 2021 FN 1303 (vs same humans FP 11 TN 3801) | session-level test acc 1.000, held-out 0.817
- 4b_int8: test TP 474 FN 2 FP 10 TN 3802 | held-out styles TP 2041 FN 1283 (vs same humans FP 10 TN 3802) | session-level test acc 1.000, held-out 0.819
- 5_calibrated: test TP 472 FN 4 FP 5 TN 3807 | held-out styles TP 1855 FN 1469 (vs same humans FP 5 TN 3807) | session-level test acc 1.000, held-out 0.793

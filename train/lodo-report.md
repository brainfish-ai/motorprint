# Leave-one-dataset-out (human generalisation)

Config: `{"hidden": [32, 16], "lr": 0.01, "wd": 0.001, "noise": 0.0, "epochs": 30}`, float32, 30 epochs. Each row: the model never saw any window from that dataset.

| held-out human dataset | users | windows | threshold | FPR @ threshold | FPR @ 0.5 | bot test TPR | held-out-style bot TPR |
|---|---|---|---|---|---|---|---|
| adserp | 47 | 24320 | 0.300 | 35.05% | 33.10% | 99.7% | 70.1% |
| boun | 19 | 35239 | 0.300 | 4.26% | 3.29% | 99.7% | 56.5% |
| cmu | 50 | 12402 | 0.300 | 0.00% | 0.00% | 100.0% | 50.9% |
| dux | 36 | 36314 | 0.300 | 6.32% | 5.17% | 100.0% | 58.0% |
| keyrecs | 95 | 28960 | 0.300 | 4.03% | 2.47% | 100.0% | 52.6% |
| mousetask | 174 | 23507 | 0.300 | 0.00% | 0.00% | 99.7% | 50.3% |

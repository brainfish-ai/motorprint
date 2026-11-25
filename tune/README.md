# Weight-space tuning

`bash tune/run.sh` reruns everything: featurize -> sweep -> SWA/soups -> pruning -> quantization -> threshold calibration -> writes `src/weights.ts`.

- Fully seeded and deterministic for a given `data/features.json` (about 2 minutes on 8 cores).
- `--quick` runs a 4-config sweep for smoke tests. `--no-write` leaves `src/weights.ts` alone.
- Every run is logged to `runs.jsonl` (machine readable) and `RUNS.md` (table). Stage winners and the before/after table go to `REPORT.md` and `summary.json`. Candidate model specs land in `models/`.
- Selection never looks at test or held-out-style data: the sweep and soups are picked by validation log-loss, pruning and quantization are accepted only if validation AUC drops by at most 0.001 / 0.002 and log-loss rises by at most 10%, and the threshold is the lowest one with at most 0.5% false positives on validation humans.
- `measure.ts` bundles the library with a candidate model (esbuild, minified, gzip -9) and times feature extraction + inference per window in Node.

When real human sessions arrive (drop JSON files from `demo/collect.html` into `data/sessions-real/`), just rerun `bash tune/run.sh`. Real sessions get style `real_human` / `real_bot` and join the session-level train/val/test split automatically. Once there are a few hundred, consider down-weighting or dropping the synthetic humans.

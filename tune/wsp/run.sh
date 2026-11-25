#!/usr/bin/env bash
# Weight-space programming experiment. Needs data/features-real.json (HUMANS=real bash tune/run.sh, or npm run featurize -- --humans real).
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 tune/wsp/dump.py > /dev/null      # weights-dump.md
python3 tune/wsp/probe.py > /dev/null     # probes.md
python3 tune/wsp/program.py               # models/wsp.json (hand-written unit, no gradients)
python3 tune/wsp/finetune.py              # models/ft_*.json (gradient baselines on the same failure examples)
python3 tune/wsp/evaluate.py              # RESULTS.md, results.json

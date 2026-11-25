#!/usr/bin/env bash
# Regenerate the whole benchmark: recordings (resumable), features, scores, report.
#   bash bench/run.sh                    # record missing sessions (300 per tool) + score
#   BENCH_SKIP_RECORD=1 bash bench/run.sh  # re-score existing recordings only (fully deterministic)
#   BENCH_N=40 bash bench/run.sh         # smaller run
# Prerequisites: real-human data converted (data/external/sessions, see DATA.md) and data/features-real.json
# (both produced by `HUMANS=real bash tune/run.sh`), Google Chrome, xvfb-run, xdotool, Node 22, Python 3.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH=$HOME/.local/node22/bin:$PATH
[ -f data/features-real.json ] || { echo "missing data/features-real.json: run HUMANS=real bash tune/run.sh first"; exit 1; }
[ -d bench/node_modules ] || (cd bench && PUPPETEER_SKIP_DOWNLOAD=1 npm ci --no-audit --no-fund)
[ -x bench/.venv/bin/python ] || { python3 -m venv bench/.venv && bench/.venv/bin/pip install -q -r bench/requirements.txt; }
python3 bench/human_split.py                 # frozen leave-users-out split (identical to training)
python3 bench/replay_traces.py               # 300 real-human trace segments from TEST users only
node bench/plan.mjs 300                      # deterministic task plan
if [ "${BENCH_SKIP_RECORD:-0}" != 1 ]; then bash bench/record.sh "${BENCH_N:-300}"; fi
bash bench/versions.sh > /dev/null
npx tsx bench/featurize.ts
python3 bench/score.py
echo "report: bench/results/RESULTS.md"

#!/usr/bin/env bash
# Rerun the whole weight-space optimisation pass and ship the winner as the default model.
# Safe to run from any shell (including the Metaphor app terminal):  bash tune/run.sh [--quick] [--no-write]
# Steps: featurize all sessions (synthetic + any real ones in data/sessions-real) -> tune.py -> rebuild lib -> print sizes.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/node22/bin:$PATH"
npx tsx train/featurize.ts
python3 tune/tune.py "$@"
npx tsc -p tsconfig.lib.json
npx esbuild src/index.ts --bundle --minify --format=esm --outfile=/tmp/motorprint.min.js --log-level=warning
echo "core bundle: $(wc -c </tmp/motorprint.min.js) B min, $(gzip -9c /tmp/motorprint.min.js | wc -c) B gzip"
echo "report: tune/REPORT.md   all runs: tune/RUNS.md / tune/runs.jsonl"

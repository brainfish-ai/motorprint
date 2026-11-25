#!/usr/bin/env bash
# Rerun the whole weight-space optimisation pass and ship the winner as the default model.
# Safe to run from any shell (including the Metaphor app terminal):
#   bash tune/run.sh [--quick] [--no-write]            # real human datasets (default)
#   HUMANS=both bash tune/run.sh --no-write --tag both  # real + synthetic humans
#   HUMANS=synthetic bash tune/run.sh --no-write --tag synthetic
# Steps: (convert external datasets if missing) -> featurize -> tune.py -> leave-one-dataset-out -> rebuild lib.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/node22/bin:$PATH"
HUMANS="${HUMANS:-real}"
if [ "$HUMANS" != "synthetic" ] && [ ! -s data/external/sessions/adserp.jsonl ]; then
  echo "converting external datasets (see DATA.md for downloads)"; python3 data/external/convert/convert.py
fi
FEAT="data/features-${HUMANS}.json"
npx tsx train/featurize.ts --humans "$HUMANS" --out "$FEAT"
export MOTORPRINT_FEATURES="$PWD/$FEAT"
python3 tune/tune.py "$@"
if [ "$HUMANS" = "real" ] && [[ " $* " != *" --quick "* ]]; then python3 train/lodo.py; fi
npx tsc -p tsconfig.lib.json
npx esbuild src/index.ts --bundle --minify --format=esm --outfile=/tmp/motorprint.min.js --log-level=warning
echo "core bundle: $(wc -c </tmp/motorprint.min.js) B min, $(gzip -9c /tmp/motorprint.min.js | wc -c) B gzip"
echo "report: tune/REPORT*.md   all runs: tune/RUNS*.md   LODO: train/lodo-report.md"

#!/usr/bin/env bash
# Round-3 collection: same tools/plan as record.sh, page now also records the provenance probe (pointer/keyboard/
# wheel/focus attributes, event-vs-handler lag, rAF frames). Separate server/port + raw dir so round-1 data is untouched.
# Usage: bash bench/record2.sh [N per tool, default 80]
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH=$HOME/.local/node22/bin:$PATH
N=${1:-80}
PY=bench/.venv/bin/python
export BENCH_PORT=18791 BENCH_RAW=raw2 BENCH_URL=http://127.0.0.1:18791/
mkdir -p bench/data/logs2
npx esbuild bench/site/bench.ts --bundle --format=iife --outfile=bench/site/bench.js --log-level=warning
curl -s -o /dev/null $BENCH_URL || { nohup node bench/server.mjs > bench/data/logs2/server.log 2>&1 & sleep 1; }
js() { node bench/tools/js-tools.mjs "$1" 0 "$N" >> "bench/data/logs2/$1.log" 2>&1; echo "$(date +%T) done $1" >> bench/data/logs2/record.log; }
py() { xvfb-run -a -s "-screen 0 1280x800x24" $PY bench/tools/py_tools.py "$1" 0 "$N" >> "bench/data/logs2/$1.log" 2>&1; echo "$(date +%T) done $1" >> bench/data/logs2/record.log; }
echo "$(date +%T) start N=$N" >> bench/data/logs2/record.log
( js playwright-mcp ) &
( js ghost-cursor; js puppeteer-stealth; js playwright-stealth ) &
( py replay-xdotool; py pyautogui ) &
( py botasaurus-human; py nodriver ) &
( js replay-cdp; py undetected-chromedriver ) &
wait
echo "$(date +%T) all done" >> bench/data/logs2/record.log

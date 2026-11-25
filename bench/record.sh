#!/usr/bin/env bash
# Record bot sessions with every tool (resumable: finished sessions are skipped). Raw output: bench/data/raw/<tool>/ (gitignored).
# Usage: bash bench/record.sh [N per tool, default 300]
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH=$HOME/.local/node22/bin:$PATH
N=${1:-${BENCH_N:-300}}
PY=bench/.venv/bin/python
XV='xvfb-run -a -s -screen\ 0\ 1280x800x24'
mkdir -p bench/data/logs
node bench/plan.mjs 300 >/dev/null
[ -f bench/data/replay-traces.jsonl ] || python3 bench/replay_traces.py
npx esbuild bench/site/bench.ts --bundle --format=iife --outfile=bench/site/bench.js --log-level=warning
curl -s -o /dev/null http://127.0.0.1:18790/ || { nohup node bench/server.mjs > bench/data/logs/server.log 2>&1 & sleep 1; }
js() { node bench/tools/js-tools.mjs "$1" 0 "$N" >> "bench/data/logs/$1.log" 2>&1; echo "$(date +%T) done $1" >> bench/data/logs/record.log; }
py() { xvfb-run -a -s "-screen 0 1280x800x24" $PY bench/tools/py_tools.py "$1" 0 "$N" >> "bench/data/logs/$1.log" 2>&1; echo "$(date +%T) done $1" >> bench/data/logs/record.log; }
echo "$(date +%T) start N=$N" >> bench/data/logs/record.log
( js playwright-mcp ) &
( js ghost-cursor; js puppeteer-stealth; js playwright-stealth ) &
( py replay-xdotool; py pyautogui ) &
( py botasaurus-human; py nodriver ) &
( js replay-cdp; py undetected-chromedriver ) &
wait
echo "$(date +%T) all done" >> bench/data/logs/record.log

#!/usr/bin/env bash
# Record the exact tool versions used for a bench run -> bench/results/versions.json
cd "$(dirname "$0")"
export PATH=$HOME/.local/node22/bin:$PATH
v() { node -p "require('./node_modules/$1/package.json').version" 2>/dev/null || echo missing; }
pv() { .venv/bin/pip show "$1" 2>/dev/null | awk '/^Version/{print $2}'; }
mkdir -p results
cat > results/versions.json <<J
{"chrome": "$(google-chrome --version | awk '{print $3}')", "node": "$(node -v)", "python": "$(.venv/bin/python -V | awk '{print $2}')",
 "xdotool": "$(xdotool --version | awk '{print $NF}')",
 "ghost-cursor": "$(v ghost-cursor)", "puppeteer-core": "$(v puppeteer-core)", "puppeteer-extra": "$(v puppeteer-extra)",
 "puppeteer-extra-plugin-stealth": "$(v puppeteer-extra-plugin-stealth)", "playwright-extra": "$(v playwright-extra)", "playwright-core": "$(v playwright-core)",
 "@playwright/mcp": "$(v @playwright/mcp)", "undetected-chromedriver": "$(pv undetected-chromedriver)", "selenium": "$(pv selenium)",
 "nodriver": "$(pv nodriver)", "botasaurus-driver": "$(pv botasaurus-driver)", "botasaurus-humancursor": "$(pv botasaurus_humancursor)", "pyautogui": "$(pv pyautogui)"}
J
cat results/versions.json

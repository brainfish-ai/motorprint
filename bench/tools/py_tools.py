"""Off-the-shelf Python bot tools against the bench site, at their published defaults.
Usage (needs an X display; bench/run.sh wraps each worker in xvfb-run):
  python bench/tools/py_tools.py <tool> <from> <to>
  tools: undetected-chromedriver | nodriver | botasaurus-human | pyautogui | replay-xdotool
"""
import json, os, random, subprocess, sys, time, tempfile, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
BASE = os.environ.get('BENCH_URL', 'http://127.0.0.1:18790/')
CHROME = os.environ.get('CHROME', '/usr/bin/google-chrome')
tool, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
PLAN = json.loads((HERE / 'plan.json').read_text())[a:b]
TRACES = [json.loads(l) for l in open(HERE / 'data' / 'replay-traces.jsonl')] if (HERE / 'data' / 'replay-traces.jsonl').exists() else []


def sid_of(p, task=None): return f"{tool}__{p['i']:03d}-{task or p['task']}"
def done(sid):
    f = HERE / 'data' / os.environ.get('BENCH_RAW', 'raw') / tool / f'{sid}.json'; return f.exists() and f.stat().st_size > 400
def url(p, task=None): return f"{BASE}?task={task or p['task']}&sid={sid_of(p, task)}"


# ---------------- Selenium + undetected-chromedriver ----------------
def run_uc():
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import Select
    from selenium.webdriver.common.action_chains import ActionChains
    ver = int(subprocess.check_output([CHROME, '--version']).split()[2].split(b'.')[0])
    opts = uc.ChromeOptions(); opts.add_argument('--window-size=1280,900'); opts.add_argument('--no-sandbox')
    d = uc.Chrome(options=opts, browser_executable_path=CHROME, version_main=ver)   # headed: uc's default
    for p in PLAN:
        sid = sid_of(p)
        if done(sid): continue
        try:
            d.get(url(p)); time.sleep(0.3)
            E = lambda s: d.find_element(By.CSS_SELECTOR, s)
            if p['task'] == 'form':
                for s, t in [('#first', p['first']), ('#last', p['last']), ('#email', p['email'])]: E(s).click(); E(s).send_keys(t)
                Select(E('#country')).select_by_visible_text(p['country']); E('#msg').click(); E('#msg').send_keys(p['msg'])
                E('#agree').click(); E('#submit').click()
            elif p['task'] == 'nav':
                for c in p['nav']: E(f'#card-{c}').click(); time.sleep(0.3)
            elif p['task'] == 'read':
                for _ in range(p['scrolls']): ActionChains(d).scroll_by_amount(0, p['scrollPx']).perform(); time.sleep(0.25)
                E('#read-done').click()
            else:
                E('#q').click(); E('#q').send_keys(p['query'] + Keys.ENTER); time.sleep(0.2); E(f"#res-{p['result']}").click()
            time.sleep(0.3); d.execute_script('window.__benchFlush()'); time.sleep(0.4)
        except Exception as e: print(sid, str(e)[:200], file=sys.stderr)
    d.quit()


# ---------------- nodriver (CDP, its own mouse_move/mouse_click helpers) ----------------
def run_nodriver():
    import nodriver as nd
    async def main():
        br = await nd.start(browser_executable_path=CHROME, browser_args=['--window-size=1280,900'], sandbox=False)   # headed default
        for p in PLAN:
            sid = sid_of(p)
            if done(sid): continue
            try:
                tab = await br.get(url(p)); await tab.sleep(0.5)
                async def click(sel):
                    el = await tab.select(sel); await el.mouse_move(); await el.mouse_click(); return el
                if p['task'] == 'form':
                    for s, t in [('#first', p['first']), ('#last', p['last']), ('#email', p['email']), ('#msg', p['msg'])]:
                        el = await click(s); await el.send_keys(t)
                    el = await tab.select('#country'); await el.mouse_move(); await el.mouse_click()
                    opt = await tab.find(p['country'], best_match=True); await opt.select_option()
                    await click('#agree'); await click('#submit')
                elif p['task'] == 'nav':
                    for c in p['nav']: await click(f'#card-{c}'); await tab.sleep(0.3)
                elif p['task'] == 'read':
                    for _ in range(p['scrolls']): await tab.scroll_down(p['scrollPx'] // 10); await tab.sleep(0.25)
                    await click('#read-done')
                else:
                    el = await click('#q'); await el.send_keys(p['query']); await click('#go'); await tab.sleep(0.2); await click(f"#res-{p['result']}")
                await tab.sleep(0.3); await tab.evaluate('window.__benchFlush()'); await tab.sleep(0.4)
            except Exception as e: print(sid, str(e)[:200], file=sys.stderr)
        br.stop()
    nd.loop().run_until_complete(main())


# ---------------- botasaurus driver with human mode ----------------
def run_botasaurus():
    from botasaurus_driver import Driver
    d = Driver(headless=False, window_size=(1280, 900), arguments=['--no-sandbox'], chrome_executable_path=CHROME) if 'chrome_executable_path' in Driver.__init__.__code__.co_varnames else Driver(headless=False, window_size=(1280, 900), arguments=['--no-sandbox'])
    d.enable_human_mode()   # botasaurus' humanized cursor (human-like curves, delays)
    for p in PLAN:
        sid = sid_of(p)
        if done(sid): continue
        try:
            d.get(url(p)); d.sleep(0.3)
            if p['task'] == 'form':
                for s, t in [('#first', p['first']), ('#last', p['last']), ('#email', p['email']), ('#msg', p['msg'])]: d.click(s); d.type(s, t)
                try: d.select_option('#country', p['country'])
                except Exception: pass   # botasaurus' select_option fails on this <select>; skip the field
                d.click('#agree'); d.click('#submit')
            elif p['task'] == 'nav':
                for c in p['nav']: d.click(f'#card-{c}'); d.sleep(0.3)
            elif p['task'] == 'read':
                for _ in range(p['scrolls']): d.scroll('#article', by=p['scrollPx']); d.sleep(0.25)
                d.click('#read-done')
            else:
                d.click('#q'); d.type('#q', p['query']); d.click('#go'); d.sleep(0.2); d.click(f"#res-{p['result']}")
            d.sleep(0.3); d.run_js('window.__benchFlush()'); d.sleep(0.4)
        except Exception as e: print(sid, str(e)[:200], file=sys.stderr)
    d.close()


# ---------------- OS-level input (pyautogui / xdotool) into a plain kiosk Chrome ----------------
class Kiosk:
    """A normal Chrome (no automation flags, navigator.webdriver = false) in kiosk mode, so page coords = screen coords.
    The remote-debugging port is used ONLY to navigate and read element rectangles; all input comes from the OS (XTest)."""
    def __init__(self):
        import websocket
        self.port = 9300 + (os.getpid() % 500)
        self.prof = tempfile.mkdtemp(prefix='bench-kiosk-')
        self.proc = subprocess.Popen([CHROME, '--kiosk', '--no-first-run', '--no-default-browser-check', '--no-sandbox', f'--remote-debugging-port={self.port}',
                                      f'--user-data-dir={self.prof}', '--window-position=0,0', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json')); break
            except Exception: time.sleep(0.2)
        ws = [t for t in tabs if t['type'] == 'page'][0]['webSocketDebuggerUrl']
        self.ws = websocket.create_connection(ws, suppress_origin=True); self.n = 0
    def cdp(self, method, **params):
        self.n += 1; self.ws.send(json.dumps({'id': self.n, 'method': method, 'params': params}))
        while True:
            r = json.loads(self.ws.recv())
            if r.get('id') == self.n: return r.get('result', {})
    def js(self, expr): return self.cdp('Runtime.evaluate', expression=expr, returnByValue=True).get('result', {}).get('value')
    def go(self, u):
        self.cdp('Page.navigate', url=u); time.sleep(0.8)
        for _ in range(50):
            if self.js('document.readyState') == 'complete': break
            time.sleep(0.1)
    def center(self, sel):
        self.js(f"document.querySelector('{sel}').scrollIntoView({{block:'center'}})"); time.sleep(0.15)
        r = self.js(f"(()=>{{const r=document.querySelector('{sel}').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,window.screenX+(window.outerWidth-window.innerWidth),window.screenY+(window.outerHeight-window.innerHeight)]}})()")
        return r[0] + r[2], r[1] + r[3]
    def close(self): self.proc.terminate()


def run_pyautogui():
    import types
    sys.modules.setdefault('mouseinfo', types.ModuleType('mouseinfo'))   # mouseinfo (a GUI helper) exits without tkinter; not needed
    import pyautogui
    pyautogui.FAILSAFE = False
    k = Kiosk()
    for p in PLAN:
        sid = sid_of(p)
        if done(sid): continue
        rng = random.Random(p['seed'])
        # half the sessions use pyautogui's defaults (instant move), half the common "humanised" recipe from its docs
        human = p['i'] % 2 == 1
        kw = (lambda: dict(duration=rng.uniform(0.25, 0.9), tween=pyautogui.easeInOutQuad)) if human else (lambda: {})
        try:
            k.go(url(p))
            def click(sel):
                x, y = k.center(sel); pyautogui.moveTo(x, y, **kw()); pyautogui.click()
            typ = lambda t: pyautogui.write(t, interval=rng.uniform(0.04, 0.12) if human else 0.0)
            if p['task'] == 'form':
                for s, t in [('#first', p['first']), ('#last', p['last']), ('#email', p['email']), ('#msg', p['msg'])]: click(s); typ(t)
                click('#agree'); click('#submit')
            elif p['task'] == 'nav':
                for c in p['nav']: click(f'#card-{c}'); time.sleep(0.3)
            elif p['task'] == 'read':
                x, y = k.center('#article'); pyautogui.moveTo(640, 400, **kw())
                for _ in range(p['scrolls']): pyautogui.scroll(-max(1, p['scrollPx'] // 100)); time.sleep(0.25)
                click('#read-done')
            else:
                click('#q'); typ(p['query']); pyautogui.press('enter'); time.sleep(0.2); click(f"#res-{p['result']}")
            time.sleep(0.3); k.js('window.__benchFlush()'); time.sleep(0.4)
        except Exception as e: print(sid, str(e)[:200], file=sys.stderr)
    k.close()


KEYSYM = {'Space': 'space', 'Enter': 'Return', 'Backspace': 'BackSpace', 'Period': 'period', 'Comma': 'comma', 'ShiftLeft': 'Shift_L', 'ShiftRight': 'Shift_R', 'Tab': 'Tab'}
def keysym(code):
    if code.startswith('Key') and len(code) == 4: return code[3].lower()
    if code.startswith('Digit'): return code[5:]
    return KEYSYM.get(code)


def run_replay_xdotool():
    k = Kiosk()
    for p in PLAN:
        tr = TRACES[p['i'] % len(TRACES)]
        task = 'form' if tr['kind'] == 'keys' else 'read'
        sid = sid_of(p, task)
        if done(sid): continue
        try:
            k.go(url(p, task) + f"&trace={tr['id']}")
            if tr['kind'] == 'keys': k.js("document.getElementById('msg').focus()")
            off = k.js('[window.screenX+(window.outerWidth-window.innerWidth),window.screenY+(window.outerHeight-window.innerHeight)]')
            lines, last = [], 0.0
            for e in tr['events']:
                dt = (e['t'] - last) / 1000.0; last = e['t']
                if dt > 0.0005: lines.append(f'sleep {dt:.4f}')
                if e['k'] == 'm': lines.append(f"mousemove {int(round(e['x'] + off[0]))} {int(round(e['y'] + off[1]))}")
                elif e['k'] == 'd': lines.append('mousedown 1')
                elif e['k'] == 'u': lines.append('mouseup 1')
                elif e['k'] == 'w': lines.append('click ' + ('5' if (e.get('dy') or 1) > 0 else '4'))
                elif e['k'] in ('kd', 'ku'):
                    ks = keysym(e.get('kc', ''))
                    if ks: lines.append(('keydown ' if e['k'] == 'kd' else 'keyup ') + ks)
            with tempfile.NamedTemporaryFile('w', suffix='.xdo', delete=False) as f: f.write('\n'.join(lines) + '\n'); fn = f.name
            subprocess.run(['xdotool', fn], check=False); os.unlink(fn)
            time.sleep(0.3); k.js('window.__benchFlush()'); time.sleep(0.4)
        except Exception as e: print(sid, str(e)[:200], file=sys.stderr)
    k.close()


{'undetected-chromedriver': run_uc, 'nodriver': run_nodriver, 'botasaurus-human': run_botasaurus, 'pyautogui': run_pyautogui, 'replay-xdotool': run_replay_xdotool}[tool]()

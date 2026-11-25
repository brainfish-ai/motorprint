"""Score the shipped model and cheap baselines on the benchmark. Deterministic given bench/data/windows.jsonl.
Writes bench/results/RESULTS.md and bench/results/results.json.
Usage: python3 bench/score.py [--model path/to/spec.json]   (default: the spec inside src/weights.ts)"""
import json, re, sys, argparse
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'train'))
from mlp import auc, load, split, standardize_fit, standardize, train, predict, export, spec_params

ap = argparse.ArgumentParser(); ap.add_argument('--model'); ap.add_argument('--tag', default='')
ap.add_argument('--half', default='all', choices=['all', 'design', 'eval'], help='bot sessions: all, design = plan blocks of 4 with even (i//4), eval = odd; each half has all 4 tasks')
ap.add_argument('--units', help='JSON list of hand-written units (tune/wsp/units.py) to install into the LODO models too')
args = ap.parse_args()
if args.model: SPEC = json.loads(Path(args.model).read_text())
else: SPEC = json.loads(re.search(r'MODEL: ModelSpec = (\{.*\});', (ROOT / 'src' / 'weights.ts').read_text()).group(1))
THR = SPEC.get('thr', 0.5); ALPHA = 0.35
TOOLS = ['ghost-cursor', 'puppeteer-stealth', 'playwright-stealth', 'undetected-chromedriver', 'nodriver', 'botasaurus-human', 'pyautogui', 'playwright-mcp', 'replay-cdp', 'replay-xdotool']


def spec_prob(spec, X):
    if len(X) == 0: return np.zeros(0)
    Z = np.clip((X - np.array(spec['mean'])) / np.array(spec['std']), -6, 6)
    for i in spec.get('off', []): Z[:, i] = 0
    h = Z
    P = spec_params(spec)
    for li, (W, b) in enumerate(P):
        h = h @ W.T + b
        if li < len(P) - 1: h = np.maximum(h, 0)
    return 1 / (1 + np.exp(-np.clip(h[:, 0], -30, 30)))


def ema(p):
    """Smoothed score per tick exactly as src/detector.ts (EMA on log-odds, alpha 0.35)."""
    l = np.log(np.maximum(1e-6, p) / np.maximum(1e-6, 1 - p)); out = np.empty_like(l); s = None
    for i, v in enumerate(l): s = v if s is None else s + ALPHA * (v - s); out[i] = s
    return 1 / (1 + np.exp(-out))


S = [json.loads(l) for l in open(HERE / 'data' / 'windows.jsonl')]
for s in S: s['X'] = np.array(s['X'], dtype=float).reshape(-1, 38); s['ticks'] = np.array(s['ticks']); s['untr'] = np.array(s['untr'], dtype=int); s['rule'] = np.array(s['rule'], dtype=int)
bots = [s for s in S if s['kind'] == 'bot' and s['group'] in TOOLS]
_idx = lambda s: int(re.search(r'__(\d+)-', s['id']).group(1))
if args.half == 'design': bots = [s for s in bots if (_idx(s) // 4) % 2 == 0]
if args.half == 'eval': bots = [s for s in bots if (_idx(s) // 4) % 2 == 1]
hum = [s for s in S if s['kind'] == 'human']
hum_test = [s for s in hum if s['split'] == 'test']
DATASETS = sorted({s['group'] for s in hum})


def apply(spec, sessions):
    for s in sessions:
        p = spec_prob(spec, s['X']); s['p'] = p; s['sm'] = ema(p) if len(p) else p
        s['smax'] = float(s['sm'].max()) if len(p) else 0.0


apply(SPEC, bots + hum)


# ---------------- detectors: each gives a per-window flag/score and a per-session flag/score ----------------
def det_model(s, thr=THR):
    return (s['p'] >= thr), s['smax'] >= thr
def det_webdriver(s): return np.full(len(s['ticks']), bool(s['webdriver'])), bool(s['webdriver'])
def det_untrusted(s): return s['untr'] > 0, bool(s['untr'].any())
def det_rule(s): return s['rule'] > 0, bool(s['rule'].any())
def det_rule_c(s): w = (s['rule'] & ~1) > 0; return w, bool(w.any())
def det_cheap(s):
    w = det_webdriver(s)[0] | det_untrusted(s)[0] | det_rule_c(s)[0]; return w, bool(s['webdriver']) or bool(w.any())
def det_model_cheap(s):
    a, b = det_model(s); c, d = det_cheap(s); return a | c, b or d
DETS = {'motorprint model @ shipped thr': det_model, 'navigator.webdriver': det_webdriver, 'isTrusted check': det_untrusted,
        'event-rate rules (all 4)': det_rule, 'event-rate rules (conservative: 3, no press-without-move)': det_rule_c, 'cheap checks: webdriver OR isTrusted OR conservative rules': det_cheap, 'model OR cheap checks': det_model_cheap}


def rates(det, sessions):
    if not sessions: return float('nan'), float('nan')
    wf = [det(s)[0] for s in sessions]; w = np.concatenate([x for x in wf if len(x)]) if any(len(x) for x in wf) else np.zeros(0)
    return (float(w.mean()) if len(w) else float('nan')), float(np.mean([det(s)[1] for s in sessions]))


def worst_fpr(det, sessions):
    out = {}
    for d in DATASETS:
        ss = [s for s in sessions if s['group'] == d]; out[d] = rates(det, ss)
    return out


R = dict(model_thr=THR, n_bot_sessions=len(bots), n_human_segments_test=len(hum_test), tools={}, detectors={}, humans={})
by_tool = {t: [s for s in bots if s['group'] == t] for t in TOOLS}

# ALL thresholds are calibrated on VALIDATION users only (never the test users they are then reported on).
# TPR @ 1% / 0.1% FPR = threshold at that pooled FPR on val humans; AUCs use test humans (threshold-free).
hum_val = [s for s in hum if s['split'] == 'val']
hw = np.concatenate([s['p'] for s in hum_test if len(s['p'])]); hs = np.array([s['smax'] for s in hum_test])
hw_v = np.concatenate([s['p'] for s in hum_val if len(s['p'])]); hs_v = np.array([s['smax'] for s in hum_val])
def thr_at(x, fpr): return float(np.quantile(x, 1 - fpr)) + 1e-12
TW = {f: thr_at(hw_v, f) for f in (0.01, 0.001)}; TS = {f: thr_at(hs_v, f) for f in (0.01, 0.001)}
# summary threshold: lowest session threshold where EVERY dataset's VAL-user session FPR <= 0.5% (half the 1% budget,
# because val users are fewer); the bench score then requires the TEST users' worst dataset to stay <= 1%.
VAL_BUDGET = 0.005
def worst_val_thr(budget=VAL_BUDGET):
    per = {d: np.array([s['smax'] for s in hum_val if s['group'] == d]) for d in DATASETS}
    u = np.unique(np.concatenate(list(per.values()))); cands = np.r_[(u[:-1] + u[1:]) / 2, u[-1] + 1e-6]
    for t in cands:
        if max((v >= t).mean() for v in per.values() if len(v)) <= budget: return float(t)
    return 1.0
tau = worst_val_thr()
R['thresholds'] = dict(window_fpr1=TW[0.01], window_fpr01=TW[0.001], session_fpr1=TS[0.01], session_fpr01=TS[0.001], summary_worst_group_1pct=tau)

for t, ss in by_tool.items():
    if not ss: continue
    bw = np.concatenate([s['p'] for s in ss if len(s['p'])]) if any(len(s['p']) for s in ss) else np.zeros(0)
    bs = np.array([s['smax'] for s in ss])
    ttd = []
    for s in ss:
        hit = np.where(s['sm'] >= THR)[0] if len(s['sm']) else []
        if len(hit): ttd.append(s['ticks'][hit[0]] / 1000)
    R['tools'][t] = dict(sessions=len(ss), no_windows=int(sum(len(s['p']) == 0 for s in ss)), windows=int(len(bw)),
        median_dur_s=float(np.median([s['dur'] for s in ss]) / 1000), webdriver_rate=float(np.mean([s['webdriver'] for s in ss])),
        window_det=float((bw >= THR).mean()) if len(bw) else 0.0, session_det=float((bs >= THR).mean()),
        window_tpr_fpr1=float((bw >= TW[0.01]).mean()) if len(bw) else 0.0, window_tpr_fpr01=float((bw >= TW[0.001]).mean()) if len(bw) else 0.0,
        session_tpr_fpr1=float((bs >= TS[0.01]).mean()), session_tpr_fpr01=float((bs >= TS[0.001]).mean()),
        session_tpr_worst1=float((bs >= tau).mean()),
        window_auc=auc(np.r_[np.ones(len(bw)), np.zeros(len(hw))], np.r_[bw, hw]) if len(bw) else float('nan'),
        session_auc=auc(np.r_[np.ones(len(bs)), np.zeros(len(hs))], np.r_[bs, hs]),
        ttd_median_s=float(np.median(ttd)) if ttd else float('nan'), det_within_2s=float(np.mean([x <= 2 for x in ttd] + [False] * (len(ss) - len(ttd)))),
        det_within_5s=float(np.mean([x <= 5 for x in ttd] + [False] * (len(ss) - len(ttd)))))
    # per task
    R['tools'][t]['session_det_by_task'] = {k: float(np.mean([s['smax'] >= THR for s in ss if s.get('task') == k])) for k in ['form', 'nav', 'read', 'search'] if any(s.get('task') == k for s in ss)}

# detectors table (session-level, per tool + human FPR)
for name, det in DETS.items():
    row = dict(tools={t: rates(det, ss)[1] for t, ss in by_tool.items() if ss}, tools_window={t: rates(det, ss)[0] for t, ss in by_tool.items() if ss})
    wf = worst_fpr(det, hum_test)
    row['human_fpr_by_dataset_window'] = {d: v[0] for d, v in wf.items()}; row['human_fpr_by_dataset_session'] = {d: v[1] for d, v in wf.items()}
    row['worst_session_fpr'] = max(row['human_fpr_by_dataset_session'].values()); row['worst_window_fpr'] = max(row['human_fpr_by_dataset_window'].values())
    row['pooled_window_fpr'], row['pooled_session_fpr'] = rates(det, hum_test)
    row['mean_tool_det'] = float(np.mean(list(row['tools'].values())))
    row['bench_score'] = row['mean_tool_det'] if row['worst_session_fpr'] <= 0.01 else 0.0
    R['detectors'][name] = row
# model at the val-calibrated threshold (the summary operating point)
det_tau = lambda s: det_model(s, tau)
row = dict(tools={t: rates(det_tau, ss)[1] for t, ss in by_tool.items() if ss}); wf = worst_fpr(det_tau, hum_test)
row['human_fpr_by_dataset_session'] = {d: v[1] for d, v in wf.items()}; row['human_fpr_by_dataset_window'] = {d: v[0] for d, v in wf.items()}
row['worst_session_fpr'] = max(row['human_fpr_by_dataset_session'].values()); row['worst_window_fpr'] = max(row['human_fpr_by_dataset_window'].values())
row['pooled_window_fpr'], row['pooled_session_fpr'] = rates(det_tau, hum_test)
row['mean_tool_det'] = float(np.mean(list(row['tools'].values()))); row['bench_score'] = row['mean_tool_det'] if row['worst_session_fpr'] <= 0.01 else 0.0
_nr = [t for t in row['tools'] if not t.startswith('replay')]; row['bench_score_no_replays'] = float(np.mean([row['tools'][t] for t in _nr])) if row['worst_session_fpr'] <= 0.01 else 0.0
R['detectors'][f'motorprint model @ val-calibrated thr ({tau:.3f})'] = row

# ---------------- leave-one-dataset-out (recipe retrained without each dataset; no benchmark bots involved) ----------------
lodo_dir = HERE / 'data' / 'lodo-models'; lodo_dir.mkdir(parents=True, exist_ok=True)
cfg = json.loads((ROOT / 'tune' / 'best-config.json').read_text())
need = [d for d in DATASETS if not (lodo_dir / f'{d}.json').exists()]
if need:
    names, X, y, style, sid, M = load(ROOT / 'data' / 'features-real.json', meta=True)
    tr, va, te, held = split(style, sid, group=M['user'])
    for d in need:
        trm, vam = tr & (M['dataset'] != d), va & (M['dataset'] != d)
        mu, sd = standardize_fit(X[trm]); mu[M['off']] = 0; Z = standardize(X, mu, sd); Z[:, M['off']] = 0
        r = train(Z[trm], y[trm], Z[vam], y[vam], hidden=tuple(cfg['hidden']), lr=cfg['lr'], wd=cfg['wd'], noise=cfg['noise'], epochs=cfg.get('epochs', 30), seed=0)
        spec = export(r['last'], mu, sd, names, bits=8, thr=0.5, off=list(M['off']))
        (lodo_dir / f'{d}.json').write_text(json.dumps(spec)); print('lodo model', d)
R['lodo'] = {}
UNITS = json.loads(Path(args.units).read_text()) if args.units else []
if UNITS:
    sys.path.insert(0, str(ROOT / 'tune' / 'wsp')); from units import install
for d in DATASETS:
    spec = json.loads((lodo_dir / f'{d}.json').read_text())
    if UNITS: spec = install(spec, UNITS)
    ss = [s for s in hum if s['group'] == d]
    p = [spec_prob(spec, s['X']) for s in ss]; w = np.concatenate([x for x in p if len(x)])
    sm = [float(ema(x).max()) if len(x) else 0.0 for x in p]
    R['lodo'][d] = dict(users=len({s['user'] for s in ss}), segments=len(ss), window_fpr=float((w >= 0.5).mean()), session_fpr=float(np.mean(np.array(sm) >= 0.5)))
R['lodo_worst_window_fpr'] = max(v['window_fpr'] for v in R['lodo'].values()); R['lodo_worst_session_fpr'] = max(v['session_fpr'] for v in R['lodo'].values())

# ---------------- write ----------------
out = HERE / 'results'; out.mkdir(exist_ok=True)
sfx = f'-{args.tag}' if args.tag else ''
(out / f'results{sfx}.json').write_text(json.dumps(R, indent=1))
pc = lambda v: '–' if v != v else f'{100 * v:.1f}%'
short = {'ghost-cursor': 'ghost-cursor', 'puppeteer-stealth': 'pptr-stealth', 'playwright-stealth': 'pw-stealth', 'undetected-chromedriver': 'uc-selenium', 'nodriver': 'nodriver',
         'botasaurus-human': 'botasaurus', 'pyautogui': 'pyautogui', 'playwright-mcp': 'pw-MCP', 'replay-cdp': 'replay-CDP', 'replay-xdotool': 'replay-xdo'}
present = [t for t in TOOLS if t in R['tools']]
L = [f'# motorprint bench results{(" (" + args.tag + ")") if args.tag else ""}', '',
     f'{len(bots)} bot sessions ({args.half} half) from {len(present)} tools; human test set = {len(hum_test)} ten-second segments from {len({s["user"] for s in hum_test})} held-out users (leave-users-out) across {len(DATASETS)} datasets. Model threshold {THR}.', '',
     '## Headline: session-level detection per tool', '',
     '**Bench score** = mean session detection rate over the tools; 0 if the worst TEST-user dataset exceeds 1% session FPR. For the model, the operating threshold is calibrated on VALIDATION users only (worst val dataset <= 0.5% session FPR) and then applied unchanged to the test users.', '',
     '| detector | ' + ' | '.join(short[t] for t in present) + ' | worst-group session FPR | pooled session FPR | **bench score** |', '|---|' + '---|' * (len(present) + 3)]
for name, row in R['detectors'].items():
    L.append(f'| {name} | ' + ' | '.join(pc(row['tools'].get(t, float("nan"))) for t in present) + f" | {pc(row['worst_session_fpr'])} | {pc(row['pooled_session_fpr'])} | **{100 * row['bench_score']:.1f}** |")
L += ['', '## Model detail per tool', '',
      '| tool | sessions | median length | no scorable window | webdriver=true | window det @thr | session det @thr | window TPR @1% / 0.1% FPR | session TPR @1% / 0.1% FPR | window AUC | session AUC | median time to detect | detected ≤2 s / ≤5 s | by task (form/nav/read/search) |', '|---|' + '---|' * 14]
for t in present:
    r = R['tools'][t]; bt = r['session_det_by_task']
    L.append(f"| {t} | {r['sessions']} | {r['median_dur_s']:.1f} s | {r['no_windows']} | {pc(r['webdriver_rate'])} | {pc(r['window_det'])} | {pc(r['session_det'])} | {pc(r['window_tpr_fpr1'])} / {pc(r['window_tpr_fpr01'])} | {pc(r['session_tpr_fpr1'])} / {pc(r['session_tpr_fpr01'])} | {r['window_auc']:.3f} | {r['session_auc']:.3f} | {r['ttd_median_s']:.1f} s | {pc(r['det_within_2s'])} / {pc(r['det_within_5s'])} | " + ' / '.join(pc(bt.get(k, float('nan'))) for k in ['form', 'nav', 'read', 'search']) + ' |')
m = R['detectors']['motorprint model @ shipped thr']
L += ['', '## Humans: false-positive rate by dataset', '', 'Leave-users-out = the shipped model on its held-out test users. Leave-one-dataset-out = the same recipe (best config, int8, thr 0.5) retrained without that dataset, scored on all of its users.', '',
      '| dataset | LUO window FPR | LUO session FPR (10 s) | LODO window FPR | LODO session FPR | event-rate rule session FPR |', '|---|---|---|---|---|---|']
for d in DATASETS:
    L.append(f"| {d} | {pc(m['human_fpr_by_dataset_window'][d])} | {pc(m['human_fpr_by_dataset_session'][d])} | {pc(R['lodo'][d]['window_fpr'])} | {pc(R['lodo'][d]['session_fpr'])} | {pc(R['detectors']['event-rate rules (all 4)']['human_fpr_by_dataset_session'][d])} |")
L.append(f"| **worst** | **{pc(m['worst_window_fpr'])}** | **{pc(m['worst_session_fpr'])}** | **{pc(R['lodo_worst_window_fpr'])}** | **{pc(R['lodo_worst_session_fpr'])}** | {pc(R['detectors']['event-rate rules (all 4)']['worst_session_fpr'])} |")
L += ['', f"Thresholds calibrated on pooled val humans: window {R['thresholds']['window_fpr1']:.3f} (1% FPR) / {R['thresholds']['window_fpr01']:.3f} (0.1%); session {R['thresholds']['session_fpr1']:.3f} / {R['thresholds']['session_fpr01']:.3f}; val-calibrated session threshold {tau:.3f}. Bench score without replay tools at the val-calibrated threshold: {100 * R['detectors'][f'motorprint model @ val-calibrated thr ({tau:.3f})']['bench_score_no_replays']:.1f}."]
(out / f'RESULTS{sfx}.md').write_text('\n'.join(L) + '\n')
print('\n'.join(L))

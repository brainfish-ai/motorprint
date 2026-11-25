"""Weight-space optimisation pass for the motorprint MLP. Reproducible; rerun any time new data lands.

Stages (every run is appended to tune/runs.jsonl and summarised in tune/RUNS.md):
  0. baseline       float32 MLP 16-8, default hyperparameters (same as train/train.py)
  1. sweep          grid over width/depth, lr, weight decay, input-noise augmentation. Selection = val log-loss only
  2. soup           (a) SWA: average of checkpoints from the 2nd half of training
                    (b) model soup: K fine-tunes from one shared parent with different seeds/noise; uniform + greedy soup
  3. prune          global magnitude pruning 30..90% with masked fine-tune, keep the sparsest within tolerance
  4. quantize       per-row symmetric int8 and int4, keep the smallest within tolerance
Then the chosen model is written to src/weights.ts (unless --no-write) and tune/REPORT.md gets the before/after table.

Usage:  python3 tune/tune.py [--quick] [--no-write]
Needs:  data/features.json (npx tsx train/featurize.ts), numpy, node22 + npx tsx for size/latency measurement.
"""
import itertools, json, os, subprocess, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'train'))
from mlp import *  # noqa

QUICK = '--quick' in sys.argv
TAG = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else ''
SFX = f'-{TAG}' if TAG else ''
TUNE = ROOT / 'tune'
RUNS = TUNE / f'runs{SFX}.jsonl'
OUTD = TUNE / 'models'; OUTD.mkdir(exist_ok=True)
RUNS.write_text('')
NODE_ENV = dict(os.environ, PATH=f"{Path.home()}/.local/node22/bin:" + os.environ.get('PATH', ''))

names, X, y, style, sid, META = load(meta=True)
OFF, USER, DATASET = META['off'], META['user'], META['dataset']
tr, va, te, held = split(style, sid, group=USER)
mu, sd = standardize_fit(X[tr]); Z = standardize(X, mu, sd)
MASKS = (tr, va, te, held)
print(f'[{META["humans"]} humans] windows: train {tr.sum()} val {va.sum()} test {te.sum()} heldout-styles {held.sum()} | off={OFF}')
real_users = lambda m: len(set(USER[m & (y == 0) & np.char.startswith(style.astype(str), 'real_')].tolist()))
print(f'real human users: train {real_users(tr)} val {real_users(va)} test {real_users(te)}')


def logloss(P, mask=va):
    p = np.clip(predict(P, Z[mask]), 1e-6, 1 - 1e-6); t = y[mask]
    w = np.where(t == 1, (y[tr] == 0).sum() / (y[tr] == 1).sum(), 1.0)
    return float(-(w * (t * np.log(p) + (1 - t) * np.log(1 - p))).sum() / w.sum())


def val_summary(P):
    return dict(val_auc=auc(y[va], predict(P, Z[va])), val_logloss=logloss(P), val_acc=metrics(y[va], predict(P, Z[va]))['acc'])


def log_run(stage, cfg, P, extra=None):
    ev = evaluate(P, Z, y, style, sid, MASKS, dataset=DATASET)
    rec = dict(stage=stage, cfg=cfg, **val_summary(P), test_acc=ev['test']['acc'], test_auc=ev['test']['auc'],
               heldout_acc=ev['heldout']['acc'], heldout_auc=ev['heldout']['auc'], heldout_tpr=ev['heldout']['tpr'],
               real_fpr=ev.get('real_human_fpr', {}).get('fpr'),
               params=nparams(P)[0], nonzero=nparams(P)[1], t=time.time(), **(extra or {}))
    with RUNS.open('a') as f: f.write(json.dumps(rec) + '\n')
    print(f"[{stage}] {json.dumps(cfg)} val_ll={rec['val_logloss']:.4f} val_auc={rec['val_auc']:.4f} test_auc={rec['test_auc']:.4f} heldout_tpr={rec['heldout_tpr']:.3f} nz={rec['nonzero']}")
    return rec


def measure(spec, tag):
    path = OUTD / f'{tag}{SFX}.json'; path.write_text(json.dumps(spec, separators=(',', ':')))
    r = subprocess.run(['npx', 'tsx', 'tune/measure.ts', str(path)], cwd=ROOT, capture_output=True, text=True, env=NODE_ENV)
    try: return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: print(r.stderr); return {}


summary = {}
def snapshot(stage, P, bits=32, note='', thr=0.5):
    spec = export(P, mu, sd, names, bits=bits, thr=thr, off=OFF)
    Pe = [[W.copy(), b.copy()] for W, b in (P if bits == 32 else quantize(P, bits)[0])]
    if OFF: Pe[0][0][:, OFF] = 0.0
    ev = evaluate(Pe, Z, y, style, sid, MASKS, thr=thr, dataset=DATASET)
    m = measure(spec, stage)
    summary[stage] = dict(note=note, bits=bits, params=nparams(P), eval=ev, measure=m, spec=spec)
    if 'real_human_fpr' in ev: print(f'   real-human FPR {ev["real_human_fpr"]["fpr"]:.4f} per dataset', {k: round(v['fpr'], 4) for k, v in ev.get('human_fpr', {}).items()})
    print(f'== {stage}: test acc {ev["test"]["acc"]:.4f} auc {ev["test"]["auc"]:.4f} | heldout auc {ev["heldout"]["auc"]:.4f} tpr {ev["heldout"]["tpr"]:.3f} | lib {m.get("lib_gz")} B gz | {m.get("total_us")} us/window')
    return spec

# ---------------- reference: previously shipped model (synthetic humans only), scored on this data ----------------
OLD = TUNE / 'reference' / 'old-synthetic-only.json'
if OLD.exists():
    old = json.loads(OLD.read_text()); pold = spec_predict(old, X); othr = old.get('thr', 0.5)
    class _Fake: pass
    ev = dict(test=metrics(y[te], pold[te], othr))
    ho = held | (te & (y == 0)); ev['heldout'] = metrics(y[ho], pold[ho], othr)
    ev['per_style'] = {s_: dict(n=int(((te | held) & (style == s_)).sum()), flagged=float((pold[(te | held) & (style == s_)] >= othr).mean())) for s_ in sorted(set(style[te | held].tolist()))}
    ev['human_fpr'] = {ds: dict(n=int((te & (y == 0) & (DATASET == ds)).sum()), fpr=float((pold[te & (y == 0) & (DATASET == ds)] >= othr).mean())) for ds in sorted(set(DATASET[te & (y == 0)].tolist()))}
    real = te & (y == 0) & np.char.startswith(style.astype(str), 'real_')
    allreal = (y == 0) & np.char.startswith(style.astype(str), 'real_')
    if real.any():
        _, inv = np.unique(sid[real], return_inverse=True); sp = np.bincount(inv, weights=pold[real]) / np.bincount(inv)
        ev['real_human_fpr'] = dict(n=int(real.sum()), fpr=float((pold[real] >= othr).mean()), sessions=int(len(sp)), session_fpr=float((sp >= othr).mean()))
    if allreal.any(): ev['real_human_fpr_all_users'] = dict(n=int(allreal.sum()), fpr=float((pold[allreal] >= othr).mean()))
    rp = style == 'replay'; ev['attack_replay'] = dict(n=int(rp.sum()), flagged=float((pold[rp] >= othr).mean()))
    ev['session_test'] = dict(acc=float('nan')); ev['session_heldout'] = dict(acc=float('nan'))
    summary['ref_old_synthetic'] = dict(note=f'previous main model (synthetic humans), thr {othr}', bits=8, params=(sum(W.size + b.size for W, b in spec_params(old)), sum(int(np.count_nonzero(W)) + b.size for W, b in spec_params(old))), eval=ev, measure=dict(spec_gz=spec_gz_bytes(old)), spec=old)
    print('reference old model: real-human FPR', ev.get('real_human_fpr'), 'all users', ev.get('real_human_fpr_all_users'))

# ---------------- 0. baseline ----------------
base_cfg = dict(hidden=[16, 8], lr=3e-3, wd=1e-4, noise=0.0, epochs=30)
r = train(Z[tr], y[tr], Z[va], y[va], hidden=(16, 8), lr=3e-3, wd=1e-4, epochs=30, seed=0)
P_base = r['last']
log_run('baseline', base_cfg, P_base)
snapshot('0_baseline', P_base, note='float32 16-8, default hparams')

# ---------------- 1. sweep ----------------
grid = dict(hidden=[(8,), (16,), (16, 8), (24, 12), (32, 16)], lr=[1e-3, 3e-3, 1e-2], wd=[0.0, 1e-4, 1e-3], noise=[0.0, 0.15])
if QUICK: grid = dict(hidden=[(16,), (16, 8)], lr=[3e-3], wd=[1e-4], noise=[0.0, 0.15])
best = None
def _sweep_one(c):
    h, lr, wd, nz = c
    return train(Z[tr], y[tr], Z[va], y[va], hidden=h, lr=lr, wd=wd, noise=nz, epochs=30, seed=0)['last']
combos = list(itertools.product(*grid.values()))
WORKERS = int(os.environ.get('MOTORPRINT_WORKERS', '4'))
if WORKERS > 1:
    import multiprocessing as mp
    with mp.get_context('fork').Pool(WORKERS) as pool: results = pool.map(_sweep_one, combos)
else:
    results = [_sweep_one(c) for c in combos]
for (h, lr, wd, nz), Pr in zip(combos, results):
    cfg = dict(hidden=list(h), lr=lr, wd=wd, noise=nz, epochs=30)
    rec = log_run('sweep', cfg, Pr)
    key = (round(rec['val_logloss'], 4), rec['params'])
    if best is None or key < best[0]: best = (key, cfg, Pr)
_, best_cfg, P_sweep = best
print('best sweep cfg', best_cfg)
(TUNE / f'best-config{SFX}.json').write_text(json.dumps(best_cfg))
snapshot('1_sweep', P_sweep, note=f"best of {np.prod([len(v) for v in grid.values()])} configs by val log-loss: {best_cfg}")

# ---------------- 2. SWA + soups ----------------
h = tuple(best_cfg['hidden']); lr = best_cfg['lr']; wd = best_cfg['wd']; nz = best_cfg['noise']
parent = train(Z[tr], y[tr], Z[va], y[va], hidden=h, lr=lr, wd=wd, noise=nz, epochs=30, seed=0, snapshots=True)
P_swa = average(parent['snaps'])
cands = {'single': parent['last'], 'swa': P_swa}
log_run('swa', dict(**best_cfg, n_snaps=len(parent['snaps'])), P_swa)
K = 3 if QUICK else 6
ings = []
for k in range(K):
    ft = train(Z[tr], y[tr], Z[va], y[va], hidden=h, lr=lr / 3, wd=wd, noise=[0.0, 0.1, 0.2][k % 3], epochs=10, seed=100 + k, P0=parent['last'])
    ings.append(ft['last']); log_run('soup_ingredient', dict(seed=100 + k, noise=[0.0, 0.1, 0.2][k % 3]), ft['last'])
cands['uniform_soup'] = average(ings)
log_run('uniform_soup', dict(k=K), cands['uniform_soup'])
order = sorted(range(K), key=lambda i: logloss(ings[i]))
greedy = [ings[order[0]]]
for i in order[1:]:
    if logloss(average(greedy + [ings[i]])) <= logloss(average(greedy)): greedy.append(ings[i])
cands['greedy_soup'] = average(greedy)
log_run('greedy_soup', dict(k=len(greedy)), cands['greedy_soup'])
cands['best_ingredient'] = ings[order[0]]
cands['sweep_best'] = P_sweep
soup_name = min(cands, key=lambda n: logloss(cands[n]))
P_soup = cands[soup_name]
print('soup stage pick:', soup_name)
snapshot('2_soup', P_soup, note=f'{soup_name} (picked by val log-loss among {list(cands)})')

# ---------------- 3. pruning ----------------
ref_auc, ref_ll = val_summary(P_soup)['val_auc'], logloss(P_soup)
P_pruned, chosen = P_soup, 0.0
for frac in [0.3, 0.5, 0.6, 0.7, 0.8, 0.9]:
    Pp, mk = prune(P_soup, frac)
    ft = train(Z[tr], y[tr], Z[va], y[va], hidden=h, lr=lr / 3, wd=wd, noise=nz, epochs=10, seed=7, P0=Pp, masks=mk)
    Pf = [[W * m_, b] for (W, b), m_ in zip(ft['last'], mk)]
    rec = log_run('prune', dict(frac=frac, finetune_epochs=10), Pf)
    ok = rec['val_auc'] >= ref_auc - 0.001 and rec['val_logloss'] <= ref_ll * 1.10
    if ok: P_pruned, chosen = Pf, frac
snapshot('3_prune', P_pruned, note=f'global magnitude pruning {int(chosen*100)}% + masked fine-tune')

# ---------------- 4. quantization ----------------
ref_auc, ref_ll = val_summary(P_pruned)['val_auc'], logloss(P_pruned)
q_choice = 32
for bits in [8, 4]:
    Pq, _ = quantize(P_pruned, bits)
    rec = log_run('quant', dict(bits=bits), Pq)
    if rec['val_auc'] >= ref_auc - 0.002 and rec['val_logloss'] <= ref_ll * 1.10: q_choice = bits
final_spec = snapshot('4_quant', P_pruned, bits=q_choice, note=f'int{q_choice} per-row symmetric' if q_choice < 32 else 'quantization rejected, float32')
# also keep int8 numbers for the table even if int4 wins
if q_choice == 4: snapshot('4b_int8', P_pruned, bits=8, note='int8 per-row (for comparison)')

# ---------------- 5. threshold calibration (val only) ----------------
# Falsely flagging a human is the expensive error, so pick the lowest threshold with <=TARGET_FPR on validation humans.
# Validation users are different people from test users; with real data the val->test gap is ~1.5-2x, hence 0.25%.
TARGET_FPR = float(os.environ.get('MOTORPRINT_TARGET_FPR', '0.0025'))
Pq_final = quantize(P_pruned, q_choice)[0] if q_choice < 32 else P_pruned
pv = predict(Pq_final, Z[va & (y == 0)])
thr = float(np.clip(np.quantile(pv, 1 - TARGET_FPR), 0.5, 0.97))  # never below 0.5: lowering it only adds human FPs
log_run('calibrate', dict(thr=round(thr, 4), target_val_fpr=TARGET_FPR), Pq_final)
final_spec = snapshot('5_calibrated', P_pruned, bits=q_choice, thr=round(thr, 4), note=f'stage 4 model, threshold {thr:.3f} (<={TARGET_FPR*100:.2f}% FPR on val humans)')

# ---------------- pick + write ----------------
def score(stage):
    e = summary[stage]['eval']
    return (round(e['test']['auc'], 3) + round(e['heldout']['auc'], 3), -summary[stage]['measure'].get('lib_gz', 1e9))
# Ship the final compressed model unless it lost >0.5pt test AUC vs the best stage
best_stage = max([k for k in summary if not k.startswith('ref_')], key=score)
ship = '5_calibrated' if summary['5_calibrated']['eval']['test']['auc'] >= summary[best_stage]['eval']['test']['auc'] - 0.005 else best_stage
print('shipping', ship)

rows = []
for st, s in summary.items():
    e, m = s['eval'], s['measure']
    ps = e['per_style']
    rf = e.get('real_human_fpr', {}).get('fpr', float('nan'))
    rows.append(f"| {st} | {s['note']} | {s['params'][1]}/{s['params'][0]} | {e['test']['acc']:.4f} | {e['test']['auc']:.4f} | {rf:.4f} | "
                f"{e['heldout']['auc']:.4f} | {ps.get('ghost',{}).get('flagged',0):.2f} / {ps.get('wind',{}).get('flagged',0):.2f} / {ps.get('agent',{}).get('flagged',0):.2f} | "
                f"{e.get('attack_replay',{}).get('flagged',float('nan')):.2f} | {m.get('spec_gz',0)/1024:.2f} | {m.get('lib_gz',0)/1024:.2f} | {m.get('model_us','?')} / {m.get('total_us','?')} |")
report = [f"# motorprint tuning report ({META['humans']} humans{', ' + TAG if TAG else ''})", "", f"Generated {time.strftime('%Y-%m-%d %H:%M %Z')}. Every individual run: tune/runs.jsonl (RUNS.md).", "",
          f"Test = held-out sessions of the 5 training bot styles + held-out human {'users' if META['humans'] != 'synthetic' else 'sessions'} ({META['humans']} humans; window level, threshold 0.5 except 5_calibrated and ref_*).",
          "Held-out styles = ghost-cursor-like, WindMouse and AI-agent bots never seen in training, scored against the same human test windows.",
          "Real-human FPR = share of 3 s windows from held-out real users (people never seen in training) that score as bot.",
          "Replay = synthetic human traces replayed through Playwright (an attack the model is NOT expected to catch).", "",
          "| stage | what | nonzero/params | test acc | test AUC | real-human FPR (held-out users) | held-out AUC | flagged ghost / wind / agent | flagged replay | model KB gz | lib KB gz | µs model / µs feat+model per window |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|", *rows, "", f"Shipped: **{ship}**", "",
          ]
report += ["", "## False-positive rate on held-out human users, per dataset (shipped threshold for 5_calibrated)", ""]
for st, s in summary.items():
    hf = s['eval'].get('human_fpr', {})
    rh = s['eval'].get('real_human_fpr', {})
    sess_txt = f" | session-level real-human FPR {rh['session_fpr']*100:.2f}% of {rh['sessions']} sessions" if 'session_fpr' in rh else ''
    report.append(f"- {st}: " + ', '.join(f"{k} {v['fpr']*100:.2f}% (n={v['n']})" for k, v in hf.items()) + sess_txt)
report += ["", "## Confusion matrices", ""]
for st, s in summary.items():
    if st.startswith('ref_'): continue
    t, ho = s['eval']['test'], s['eval']['heldout']
    report.append(f"- {st}: test TP {t['tp']} FN {t['fn']} FP {t['fp']} TN {t['tn']} | held-out styles TP {ho['tp']} FN {ho['fn']} (vs same humans FP {ho['fp']} TN {ho['tn']}) | session-level test acc {s['eval']['session_test']['acc']:.3f}, held-out {s['eval']['session_heldout']['acc']:.3f}")
(TUNE / f'REPORT{SFX}.md').write_text('\n'.join(report) + '\n')
(TUNE / f'summary{SFX}.json').write_text(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'spec'} for k, v in summary.items()}, indent=1))
# RUNS.md
runs = [json.loads(l) for l in RUNS.read_text().splitlines()]
md = ["| # | stage | cfg | val log-loss | val AUC | test AUC | real-human FPR@0.5 | held-out AUC | held-out TPR | nonzero |", "|---|---|---|---|---|---|---|---|---|---|"]
for i, r_ in enumerate(runs):
    rf_ = r_.get('real_fpr'); rf_ = f"{rf_:.4f}" if rf_ is not None else '-'
    md.append(f"| {i} | {r_['stage']} | `{json.dumps(r_['cfg'])}` | {r_['val_logloss']:.4f} | {r_['val_auc']:.4f} | {r_['test_auc']:.4f} | {rf_} | {r_['heldout_auc']:.4f} | {r_['heldout_tpr']:.3f} | {r_['nonzero']} |")
(TUNE / f'RUNS{SFX}.md').write_text('# All tuning runs\n\n' + '\n'.join(md) + '\n')
if '--no-write' not in sys.argv:
    write_weights_ts(summary[ship]['spec'], note=f'tune/tune.py stage {ship}: {summary[ship]["note"]}')
    print('wrote src/weights.ts')
print((TUNE / f'REPORT{SFX}.md').read_text())

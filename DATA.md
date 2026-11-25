# Data and credits

motorprint's human class is trained on **real human input from openly licensed research datasets**, converted to the browser event format in `src/types.ts`. The bot class is recorded from Playwright-driven Chrome (`data/gen-bots.ts`). A motor-control simulator (`data/gen-humans.ts`) is still available as an optional extra (`HUMANS=both`).

Raw downloads live in `data/external/raw/` and converted sessions in `data/external/sessions/`. Both are git-ignored. Only code, derived weights and reports are committed.

## Datasets used

| dataset | what it is | users | sampling | licence | how we use it |
|---|---|---|---|---|---|
| **AdSERP** (mouse movement part) | Mouse logs in the browser on Google results pages (evtrack): `mousemove`, `mousedown/up`, `click`, `wheel` (no delta), `scroll` | 47 users, 2,776 trials of ~21 s | browser events, ~60 Hz, 1 ms timestamps | CC BY 4.0 | Mouse, clicks, wheel timing and scroll. Wheel delta is not logged, so `wheel_dy_cv` is trained off |
| **Freihaut & Göritz MouseTask** | Point-and-click task, `Mo`/`Cl` events, window bounds and zoom | 179 users, 10,783 trials of ~10 s | ~60 Hz events, 1 ms timestamps | CC BY 4.0 | Movement only. `Cl` has no press/release split, so its clicks are dropped |
| **DUX** (`v1.csv`) | Sessions in a browser web app (travel-expense forms): mouse, key press/release, clicks, scroll, emotions | 36 sessions | ~125 Hz browser events | CC BY 4.0 | Real mixed mouse and keyboard sessions. Half are coalesced to 60 Hz frames |
| **Bogazici (BOUN) Mouse Dynamics** | Desktop free use for 1 month (pynput): move, drag, press, release, window category | 24 users (19 sampled), 2,550 h | ~125 Hz OS events | CC BY 4.0 | 45 one-minute chunks per user, coalesced to 60/120/144 Hz browser frames (15% left raw) |
| **KeyRecs** (free text) | Transcription typing, digraph timings (hold, DD, DU, UD, UU) | 100 participants | ms | CC BY 4.0 | Rebuilt as keydown/input/keyup sequences |
| **CMU Keystroke Benchmark** (DSL-StrongPasswordData) | 51 typists, password `.tie5Roanl` typed 400 times, hold, DD and UD times | 51 subjects | ±200 µs reference clock | No formal licence. The authors state the data is "freely available for use" and ask for citation (and a courtesy note when publishing results) | Rebuilt as key sequences. 25 repetitions per session, joined with an *artificial* 1.2 to 3 s gap (the gap was not recorded) |

## Normalisation (`data/external/convert/convert.py`)

- Timestamps are converted to ms relative to the start of the session. Features quantise every timestamp to 1 ms (`src/features.ts`), so 0.1 ms browser clocks, 1 ms browser clocks and dataset clocks all look the same.
- Coordinates are rounded to integer pixels. Duplicate consecutive positions are dropped, because browsers only fire `mousemove` on change.
- **Browser frame coalescing.** Sources that sample faster than a display frame (DUX, BOUN) are coalesced to rAF-aligned frames at a random refresh rate per session. We keep the latest sample per frame with its own timestamp, the way Chrome coalesces `mousemove`. Sources that already run at ~60 Hz browser rate (AdSERP, MouseTask) are kept as recorded.
- Recordings are cut into chunks of at most 60 s. Chunks with fewer than 20 events are dropped.
- Datasets with keystrokes only get an `input` event 1 ms after each printable keydown, which is what a text field emits.
- **Features no dataset can provide are trained off.** No public dataset records click target rectangles, and AdSERP does not record wheel deltas. Target rects are stripped from *every* session, bots included. `click_offset` and `wheel_dy_cv` are listed in `ModelSpec.off` and neutralised at inference.
- Splits are by **user** for real data (70/15/15) and by session for bots. `train/lodo.py` also holds out each human dataset entirely.

## Considered but not used

| dataset | link | licence | why not |
|---|---|---|---|
| Balabit Mouse Dynamics Challenge | https://github.com/balabit/Mouse-Dynamics-Challenge | none stated | No licence, so it is not clearly usable |
| SapiMouse | https://www.ms.sapientia.ro/~manyi/sapimouse/sapimouse.html | none on the data page. The code repo is Apache-2.0 but holds only derived \|dx\|,\|dy\| blocks | The raw data has no licence, and the licensed part has no timestamps |
| DFL (Antal) | https://www.ms.sapientia.ro/~manyi/DFL.html | none stated | No licence |
| Chao Shen static / continuous (also the real-human part of BeCAPTCHA-Mouse) | https://figshare.com/articles/dataset/Mouse_Behavior_Data_for_Static_Authentication/5619313 | CC BY 4.0 (static, checked via the figshare API) | Usable, but figshare's file host returned HTTP 403 to this machine. **Best next addition** |
| BeCAPTCHA-Mouse | https://github.com/BiDAlab/BeCAPTCHA-Mouse | repo publishes synthetic trajectories only | Its real humans are the Shen data |
| Aalto 136M Keystrokes | https://userinterfaces.aalto.fi/136Mkeystrokes/ | research and non-commercial use only | Not compatible with an MIT library that may be used commercially |
| Freihaut & Göritz FreeMouse (same Zenodo record as MouseTask) | https://zenodo.org/records/6559329 | CC BY 4.0 | Downloaded (790 MB) but not used. It is fixed ~43 Hz cursor *polling* that includes unchanged samples and has no clicks, so it does not match browser event semantics |
| Web Bot Detection Dataset (Iliou et al.) | https://m4d.iti.gr/web-bot-detection-dataset/ | none stated on the dataset page | Licence unclear. Very relevant (humans plus advanced bots on Wikipedia pages): ask the authors |
| ReMouse | https://ieee-dataport.org/documents/remouse-mouse-dynamic-dataset | IEEE DataPort terms | Needs an account to download |
| The Attentive Cursor Dataset | https://gitlab.com/iarapakis/the-attentive-cursor-dataset | none on the repo (the paper is CC BY) | No dataset licence |
| dejanai/mouse_movement_tracking (Hugging Face) | https://huggingface.co/datasets/dejanai/mouse_movement_tracking | custom "link attribution" licence | Requires a live do-follow link wherever any derivative is used. Too restrictive for a library |
| TEC (rrweb recordings) | https://github.com/Serendipity0429/TEC | could not verify | Licence not verifiable |
| EyeMouseMap | https://zenodo.org/records/13929730 | CC BY 4.0 | Possible later addition (includes remote online mouse tracking, 30 participants). Visual-search task, 259 MB bundled with gaze data |
| KEasyLogger | https://zenodo.org/records/6535004 | CC BY 4.0 | Aggregated digraph tables, not event sequences |

## Citations

- **AdSERP.** Latifzadeh, K., Gwizdka, J., & Leiva, L. A. (2025). *A Versatile Dataset of Mouse and Eye Movements on Search Engine Results Pages.* SIGIR 2025. https://doi.org/10.1145/3726302.3730325. Data: https://zenodo.org/records/15236546 (CC BY 4.0). We used `mouse-movement-data.zip` and `trial-metadata.zip`.
- **MouseTask.** Freihaut, P., & Göritz, A. S. (2022). *Study-Data: Longitudinal Study about the relationship between computer mouse usage and emotional states* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.6559329 (CC BY 4.0). We used `MouseTask_dataset.json.gz`.
- **DUX.** Bieber, C., Leppich, D., Harms, P., & Schubert, U. (2023). *DUX: A dataset of User Interactions and User Emotions* (v0.1) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.7778612 (CC BY 4.0). We used `v1.csv`.
- **Bogazici.** Kılıç, A. A., Yıldırım, M., & Anarım, E. (2021). Bogazici mouse dynamics dataset. *Data in Brief*, 36, 107094. https://doi.org/10.1016/j.dib.2021.107094. Data: Yıldırım, M., Kılıç, A. A., & Anarım, E. (2021). *Boğaziçi University Mouse Dynamics Dataset*, Mendeley Data, V2. https://doi.org/10.17632/w6cxr8yc7p.2 (CC BY 4.0).
- **KeyRecs.** Dias, T., Vitorino, J., Maia, E., Sousa, O., & Praça, I. (2023). *KeyRecs: Keystroke Dynamics Dataset* (1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.7886743 (CC BY 4.0). Described in *KeyRecs: A keystroke dynamics and typing pattern recognition dataset*, Data in Brief (2023).
- **CMU.** Killourhy, K. S., & Maxion, R. A. (2009). Comparing Anomaly-Detection Algorithms for Keystroke Dynamics. *IEEE/IFIP DSN 2009*, pp. 125–134. Data: https://www.cs.cmu.edu/~keystroke/

Changes made to all of the above: format conversion, resampling or coalescing, chunking, subsampling and the synthetic `input` events described in Normalisation. The datasets' authors do not endorse motorprint.

## Re-downloading

```bash
cd data/external/raw
curl -L -o adserp-mouse-movement-data.zip "https://zenodo.org/records/15236546/files/mouse-movement-data.zip?download=1" && mkdir -p adserp && (cd adserp && unzip -q ../adserp-mouse-movement-data.zip)
curl -L -o MouseTask_dataset.json.gz "https://zenodo.org/records/6559329/files/MouseTask_dataset.json.gz?download=1"
curl -L -o dux-v1.csv "https://zenodo.org/records/7778612/files/v1.csv?download=1"
curl -L -o keyrecs-free-text.csv "https://zenodo.org/records/7886743/files/free-text.csv?download=1"
curl -L -o DSL-StrongPasswordData.csv "https://www.cs.cmu.edu/~keystroke/DSL-StrongPasswordData.csv"
mkdir -p boun && cd boun && curl -s "https://data.mendeley.com/public-api/datasets/w6cxr8yc7p/files?folder_id=root&version=2" \
  | python3 -c "import json,sys; [print(x['content_details']['download_url'], x['filename']) for x in json.load(sys.stdin)]" \
  | while read u f; do curl -sL -o "$f" "$u"; done      # 4.9 GB split zip; read with data/external/convert/splitzip.py
cd ../../../.. && python3 data/external/convert/convert.py
```

# VAJRA: weather research website and React Native app

A SIH26072 research project with a React website, a separate Expo/React Native app, an animated Earth explorer, real radar image experiments, government data collection and a trainable temporal image model. Public and operator views share the same backend.

The working weather demonstrations use synthetic fusion and historical French radar. The downloaded government starter pack is real, but it is not a matched Indian training corpus. No operational Indian lightning model or public warning dispatch is claimed.

**New: a connected research operations workflow.** Open `/#/operations` to queue a source audit, observed radar evaluation or actual ConvLSTM training with calibration. SQLite saves the job; one separate worker runs it; the website and native operator monitor show the same recorded scores. Duplicate requests reuse the existing experiment, retries use fresh attempt folders, and daily checks can queue candidates from newly admitted observed events. No model is automatically promoted. Follow the **[architecture, setup and learning guide](docs/OPERATIONS_GUIDE.md)**.

Start with **[regional decisions, continuous forecasts and resilient communication](REGIONAL_DECISIONS_AND_CONTINUOUS_FORECASTS.md)** for the latest design: weather drivers, sparse-sensor regions, officer thresholds, local geographic matching, Bluetooth/SMS boundaries, daily evaluation and why Jev is optional. Numerical forecasts support decisions; neither an LLM nor Jev is required for the decision policy.

The officer workbench now records probability and evidence checks separately, with configurable source age/count and clear reasons. The native app includes a manually entered, unverified citizen-report preview and an explicit SMS composer action. A standalone bounded forecast queue demonstrates coalescing and rejects superseded results; it is not connected to a live feed. [Implementation design](docs/CONTINUOUS_FORECAST_DESIGN.md).

**STLDM now executes as a separate reference experiment.** The pinned official checkpoint completed one CPU example in 113.39 seconds of model computation. Persistence had lower image error on that example. This is compatibility evidence, not forecast superiority or lightning calibration. Follow the [STLDM setup, commands and actual results](docs/STLDM_GUIDE.md); its five-frame normalized input contract differs from our observed-radar API.

| Component | What you can use |
|---|---|
| Earth explorer | Search 19 supported Indian cities, rotate and zoom to the selected coordinates, pause motion or use reduced motion |
| Radar image lab | Compare raw/despeckled/smoothed inputs, persistence, global translation and dense optical flow against later observed radar |
| Data collection | Provider/API links, access status, manifest-backed downloads and bounded local collection jobs |
| Native app | Public/operator views, optional foreground device location or manual city selection, 12 Indian languages plus English, installed-voice text-to-speech and a user-reviewed SMS report draft |
| Training | Validate episode files, train/evaluate a compact ConvLSTM, optionally calibrate on separate events and report reliability against a climatology baseline |
| Research operations | Durable jobs, bounded immutable dataset registration, actual recipe execution, explicit retries, verified downloads and controlled daily candidate checks |

Cloud animation is decorative. Selecting a city moves the geographic view; it does not create a local weather observation. The native app's operator view is a view preference, not authentication.

See [the implemented system and data-flow diagrams](docs/IMPLEMENTED_SYSTEM.md) for how the website, native app, image techniques, provider APIs and separate training program connect.

For the current algorithm decisions, start with [what makes VAJRA different and how to verify it](ALGORITHM_DIFFERENTIATION_AND_VALIDATION.md). It explains why an LLM is unnecessary, when ConvLSTM/tracking/larger models help, public/operator roles and controlled retraining. The [model and repository review](research/MODEL_AND_REPOSITORY_DECISIONS.md) verifies WeatherNext 3, TimesFM 3.0, Jev, provider APIs and licences. The [Indian evidence register](research/LOCAL_WEATHER_IMPACT_EVIDENCE.md) contains 14 primary-source groups with dates, denominators and limitations.

The [calibration guide](docs/CALIBRATION_AND_VERIFICATION.md) documents the new `train --calibrate` workflow: separate training, model-selection, calibration and test events; frozen evaluation; reliability bins; Brier/log loss/AP; and event-bootstrap intervals. The synthetic smoke's adjusted Brier score is 0.089959, compared with the stronger constant-climatology baseline at 0.089687. This verifies software behavior, not Indian lightning reliability. No trained checkpoint is automatically promoted into the app.

Screenshots: [website Earth explorer](artifacts/earth-patna-desktop.png), [radar image lab](artifacts/image-lab-desktop.png), [native app](artifacts/native-earth-preview.png), [Hindi](artifacts/native-hindi-preview.png) and [Urdu](artifacts/native-urdu-preview.png).

New: [detailed technical architecture](DETAILED_TECHNICAL_ARCHITECTURE.md) and [downloaded government data inventory](data/government/README.md). The starter pack contains real IMD observations, NASA environmental data, NOAA GFS fields covering India, and US satellite/lightning/radar reference files. It includes raw files, CSV views, exact source URLs and reproducible verification; it is not yet a matched Indian training corpus.

Start with [the structured proposal and evidence brief](SIH26072_PROPOSAL_AND_EVIDENCE.md), covering the problem, solution, differentiation, architecture, feasibility, business, risks and sustainability. The [plain-language product and algorithm flow](PRODUCT_FLOW_AND_ALGORITHMS.md) explains the implementation. The [research blueprint](SIH26072_RESEARCH_AND_BLUEPRINT.md) contains the earlier evidence. See [validation results](VALIDATION.md) for what was actually checked.

## Run

Tested with Python 3.14.4 and Node 24.20.0 on Windows. The source uses modern Python and a Vite build. For the exact tested dependencies use the included Python requirements and npm lockfile.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
npm.cmd ci
npm.cmd run build
.\.venv\Scripts\python -m uvicorn nowcast.service:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. The synthetic simulator model and verified radar sample are bundled, so normal startup does not need credentials or downloads. New ConvLSTM candidate checkpoints are generated locally. On macOS/Linux use `.venv/bin/python` and `npm` in the corresponding commands.

For frontend development, start the Python service and run `npm.cmd run dev` in another terminal. Vite proxies `/api` and `/research` to port 8000. The production service mounts `dist` at startup, so build before launching it.

Open `/#/earth` for the globe, `/#/image-lab` for real image experiments and `/#/sources` for the collection catalogue. The existing `/#/workbench` remains available.

To run the new operations page, set `$env:VAJRA_ENABLE_OPERATIONS = "1"` before starting the API. Install the optional `.venv-ml` environment below, then start `.\.venv-ml\Scripts\python.exe scripts/run_operations.py worker` in another terminal. Open `/#/operations`, prepare example episodes and queue an experiment. The [operations guide](docs/OPERATIONS_GUIDE.md) covers real dataset registration, restart recovery and the precise limits of daily learning.

To enable the collection buttons on your own local server, set this before starting Uvicorn:

```powershell
$env:VAJRA_ENABLE_COLLECTIONS = "1"
```

Install the optional collection environment from `requirements-data.txt` as described in [the training and collection guide](docs/TRAINING_GUIDE.md). Browsing and downloading already bundled files does not require new provider access.

Collection accepts only the registered `india`, `noaa` and `gfs` snapshot collectors, a JSON request, a direct loopback connection and a trusted local origin. It cannot fetch an arbitrary URL or run a caller-supplied command. Jobs verify/reuse the pinned historical sample; they are not a live national feed. Job history is limited to the current server process.

## Reproduce the original simulator and tests

```powershell
.\.venv\Scripts\python -m nowcast.training
.\.venv\Scripts\python scripts/fetch_sample.py
.\.venv\Scripts\python -m unittest discover -s tests -v
npm.cmd run build
# Start the service on 127.0.0.1:8000, then:
npx.cmd playwright install chromium
npm.cmd run test:browser
```

The full browser suite now also exercises operations: enable the operations API and run its numerical worker first. `python scripts/verify_operations_workflow.py` checks the three actual recipes, repeated requests, artifact hashes, research links and synthetic exclusion from daily learning against a demo-only local store.

Training writes `data/model.json` and `data/evaluation.json`. It uses 24 training events, six validation events and six test events generated from disjoint seeds. Scores measure performance on the generator, not India. Downloading the sample is optional if bundled checksums already pass. Browser tests use the locally running service and save screenshots in `artifacts`.

## Image techniques and neural training

The radar lab keeps measurement processing separate from screen rendering. Despeckling removes small isolated detected objects; smoothing averages valid neighbours in linear reflectivity, then converts back to dBZ. Missing pixels stay missing. Global translation estimates one motion vector; dense Horn–Schunck flow estimates a spatially varying motion field. Both extrapolate past observations. The later frame is reserved for scoring, not supplied to motion estimation.

These are image baselines, not proof that a sophisticated method is more accurate. Compare their common-support scores in the lab. Radar-echo occurrence is a separate target from lightning occurrence.

The neural training program uses a compact ConvLSTM with masked inputs and a binary spatial output. It is separate from the six logistic simulator heads served by the original workbench. Install the optional training environment:

```powershell
python -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install -r requirements-ml.txt

# Check the machinery on generated examples, not Indian observations:
.\.venv-ml\Scripts\python.exe scripts/train_images.py smoke --output artifacts/image-smoke

# After preparing real, matched episodes using the guide:
.\.venv-ml\Scripts\python.exe scripts/train_images.py validate --data data/training/episodes
.\.venv-ml\Scripts\python.exe scripts/train_images.py train --data data/training/episodes --output data/training_runs/pilot-v1 --epochs 20 --batch-size 4 --device cpu
.\.venv-ml\Scripts\python.exe scripts/train_images.py evaluate --data data/training/episodes --checkpoint data/training_runs/pilot-v1/model.pt
```

Use `--device cuda` only with a compatible CUDA-enabled PyTorch installation and GPU. The smoke command proves that data loading, optimization, checkpointing and evaluation run; its score has no operational meaning.

Read **[the training guide](docs/TRAINING_GUIDE.md)** before preparing files. It specifies the NPZ schema, target definitions, time/coverage checks, episode grouping, normalization, evaluation commands and access requirements. The required arrays include image values and masks, UTC observation and availability times, future binary targets, target-window ends and coverage. Metadata fixes event identity, channels and physical units. Malformed or insufficient event sets must be rejected rather than silently split into misleading training/test samples.

For Indian lightning training, obtain coincident radar, INSAT and event-level lightning coverage over the same region and period. Build causal histories, then attach future labels separately. Split independent episodes before fitting normalization or models. Test held-out seasons/regions and sensor outages, and validate probabilities before any operational use. The current IMD surface, NASA, GFS and US reference files have different dates/domains; putting them in one folder does not make them paired training examples.

The [government inventory](data/government/README.md) contains actual files and source URLs. The collection scripts are `scripts/collect_india_data.py`, `scripts/collect_noaa_data.py` and `scripts/collect_gfs_data.py`. Run `scripts/prepare_government_pack.py` to recreate CSV views and `scripts/verify_government_data.py --scientific` in the isolated data environment to recheck the pack. Native provider/API access links are also exposed at `/api/data/catalog`.

## Demonstration

The homepage explains the problem and links to the officer workbench, public preview and pipeline guide. These are presentation views, not authenticated roles.

1. Inspect a synthetic event and switch lead time or target.
2. Compare learned fusion, motion, persistence and the simulated outcome.
3. Make a source stale or missing. Remove radar, satellite and lightning to see abstention even when NWP remains.
4. Select a demo site, preparation time, probability threshold and minimum recent-source requirements. Save and export a local receipt; inspect the recorded reasons. High probability with insufficient evidence is held for review, and synthetic results never authorize public dispatch.
5. Switch to France for actual observed radar and +5 to +20-minute echo verification.
6. Open the verification lab and research documents.
7. After saving a receipt, use **View public preview** to retain a labelled historical sample on this browser. Reload without a connection to inspect offline behavior. Use **Remove this saved sample** to clear it.

## Website and mobile app

The production build includes a PWA manifest and a versioned service worker. Supported browsers can install the website. Offline caching covers the introduction, guide and other app-shell files; it deliberately excludes `/api/` and `/research/` responses. An explicitly saved simulation receipt is stored separately in localStorage. Historical samples are always labelled and never treated as current warnings.

Desktop localhost is a supported secure-context development exception. A phone installation needs an HTTPS deployment that the phone can reach; `127.0.0.1` on a phone points to the phone itself. The separate React Native source is in `mobile/`. No hosted deployment, signed native binary, push service or public warning feed is included in the PWA build.

Useful links are `/#/overview`, `/#/workbench`, `/#/public` and `/#/flow`. Browser back/forward and deep-link reloads preserve the view. Forecast inputs remain session state rather than URL parameters. A browser with no backend connection can read cached pages but cannot run the Python model.

`node scripts/verify-web-delivery.mjs` checks Chromium manifest/installability errors, research downloads and keyboard skip navigation against the running production build. It does not certify mobile-platform installation or accessibility conformance.

The location names in simulation are study-area markers, not observed Indian storms or verified shelters. Real replay contains radar only; it cannot support lightning decisions. The map is a coordinate grid with city markers, not an official administrative map.

## React Native app, languages and spoken alerts

The native app lives in `mobile/` with its own dependency lockfile. It uses Expo and React Native primitives; it is separate from the browser PWA. See **[the mobile guide](docs/MOBILE_GUIDE.md)** for setup, API configuration, building and the tested scope.

```powershell
cd mobile
npm.cmd ci
npx.cmd expo start
# Browser preview of the React Native client:
npx.cmd expo start --web --port 8081
```

The language selector supports **Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese and Urdu**, with English as a fallback. Preferences are saved locally. The app keeps selected-place details, information status and source context visible. Translation text is a draft and needs native-speaker review before public warning use.

Spoken messages use `expo-speech` and an available matching device voice. Listen/Stop controls do not substitute for a background notification service. Some phones lack particular language voices; the app must report that and retain readable text. Installing a voice may require a device download. Device voice availability alone does not prove offline speech, and iOS silent mode can suppress audio. Test the actual target phones before relying on TTS.

Set `EXPO_PUBLIC_API_URL` using `mobile/.env.example`. On a physical phone, use a reachable server address, not the phone's `localhost`. For local development on a trusted LAN, run the backend with `--host 0.0.0.0` and point the app at the computer's LAN address. The collection write endpoint remains loopback-only. Production needs HTTPS and authenticated operator roles before exposure outside a controlled development setup.

Web exports and Android/iOS JavaScript bundle exports do not prove native installation, physical-device audio or background delivery. The [validation record](VALIDATION.md) distinguishes completed checks from those remaining device checks.

## API

Interactive API schema is available at `/docs`.

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Local service and model availability |
| `POST /api/runs` | Compute and save a replay with target, scores and provenance |
| `GET /api/runs/{id}` | Retrieve exact saved result |
| `GET /api/evaluation` | Held-out synthetic experiment results |
| `GET /api/image-methods` | Supported processing and motion methods |
| `POST /api/image-runs` | Real-radar processing, extrapolation and held-out comparison |
| `GET /api/data/catalog` | Official sources, API links, local files and access status |
| `GET /api/data/files/{file_id}` | Download a manifest-listed file after hash verification |
| `POST /api/data/collections/{collection_id}` | Start/reuse a bounded registered local collection job |
| `GET /api/data/jobs` | Recent jobs in this server process |
| `GET /api/data/jobs/{id}` | Collection status and result |
| `POST /api/receipts` | Save an idempotent local simulation review record |
| `GET /api/receipts` | List latest 100 receipts |
| `GET /api/receipts/{id}` | Retrieve receipt |

Example run body:

```json
{"mode":"simulation","seed":62,"step":8,"horizon":30,"hazard":"lightning","disabled":[],"stale":["radar"]}
```

For observed radar use `{"mode":"observed","horizon":15,"hazard":"storm"}`. It deliberately rejects lightning and unsupported lead times. Run identities include the request, model, code and data provenance. Repeated identical requests return the original stored execution, including its latency measurement.

## Files and scope

The [data atlas](research/DATA_SOURCES.md) covers Indian permissions and open international sources. [Model research](research/MODEL_RESEARCH.md) defines the future spatial model and evaluation. [Problem evidence](research/PROBLEM_EVIDENCE.md) documents impact, survey results and prior art. The [design decision](research/design/SYNTHESIS.md) explains why the first implementation is small.

The two new notes are assessed in [Friend notes review](research/FRIEND_NOTES_REVIEW.md). [Jev assessment](research/JEV_ASSESSMENT.md) explains why the optional online text-classification service is separate from weather prediction. Jev is not integrated.

SQLite records live in `data/receipts.sqlite`, created on first use. No emails, SMS, CAP warnings or public alerts are sent. The API is intended for localhost; authentication, multi-user governance and operational integrations are future work.

Météo-France data are used under [Etalab Open Licence 2.0](data/external/METEONET_LICENCE.md), with [source URLs, checksums and transformations](data/external/meteonet_manifest.json). Outputs use a three-pixel sampling stride and preserve missingness. MétéoNet is not affiliated with or endorsing this project.

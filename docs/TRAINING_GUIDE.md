# Radar image experiments and temporal-model training

This repository now has two independent additions: a working image-processing laboratory using real French radar, and an optional PyTorch training CLI for an explicit episode format. Neither trains or validates Indian lightning prediction from the government starter pack. The existing `/api/runs` simulator and radar replay retain their behavior; experimental training weights are not loaded by that endpoint.

## 1. Run the observed image laboratory

For the separate pretrained generative experiment, use the [STLDM guide](STLDM_GUIDE.md). It pins the official source and checkpoint and records a real CPU inference against the author example. It does not accept these dBZ episodes as pretrained inputs, train a lightning model, or replace this ConvLSTM workflow. [Continuous refresh versus controlled retraining](../REGIONAL_DECISIONS_AND_CONTINUOUS_FORECASTS.md#continuous-correction-daily-learning-and-bounded-memory) explains how new scans, delayed truth, daily evaluation and model promotion differ.

The standard application dependencies in `requirements.txt` are sufficient. Start the API as described in the root README, then use the Image Lab in the website or call:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/image-runs -ContentType application/json -Body '{"method":"global_translation","preprocessing":"smooth","horizon":10}'
```

`GET /api/image-methods` lists the supported methods and parameters. The response contains original, processed, forecast, held-out truth and segmentation arrays; masks; same-cohort comparisons against raw persistence; and pinned provenance. Grid values are dBZ, with `null` for missing data. The source archive uses `-10` as a computational no-echo sentinel. Processing retains linear reflectivity and separate `masks.no_echo` arrays: positive reflectivity can become any finite negative dBZ, including `-10`, so processed/forecast values alone must not be used to infer no echo. `masks.intensity_evaluation` identifies the intensity cohort. Segment labels are per-image components, not tracked storm identities.

| Option | Actual operation | Important limit |
|---|---|---|
| `preprocessing=raw` | Preserve decoded pixels | Does not perform instrument quality control. |
| `despeckle` | Remove connected ≥20 dBZ components with fewer than four pixels | A heuristic that can erase real small echoes. |
| `smooth` | Mask-aware 3 × 3 averaging in linear reflectivity, then return to dBZ | Existing missing centres remain missing; smoothing can blur intense features. |
| `method=persistence` | Keep the current processed image fixed | No motion or growth model. |
| `global_translation` | Cross-correlation motion from two past frames, then linear-reflectivity advection | One velocity for the entire image; fixed search range. |
| `dense_optical_flow` | NumPy Horn–Schunck current-to-previous flow, 60 iterations and fixed regularization; frozen local-velocity extrapolation | Smooth-motion/brightness assumptions can fail during growth, decay or large displacement. No superiority claim. |

The two inputs are archived at 10:10 and 10:15 on 19 December 2018. Only +5, +10, +15 and +20 minutes have held-out future images in this replay. The source timezone remains unverified and is not relabelled UTC. No future image participates in preprocessing, motion or segmentation.

Binary CSI/POD/FAR/FSS use the ≥20 dBZ echo target on the intersection of valid truth, selected forecast and raw persistence. The returned `brier` is a score for deterministic 0/1 echo predictions, not evidence of calibrated probabilities. MAE/RMSE in dBZ additionally require positive linear reflectivity in **both forecasts and truth**, and report a separate `intensity_samples` count. Valid weak echoes below −10 dBZ remain in this cohort. This common cohort makes the comparison explicit but excludes missed/new echoes from the intensity metric; the binary scores retain them. Small-case pixel scores are not independent-storm validation.

## 2. Inspect and collect the government starter pack

`GET /api/data/catalog` exposes provider links, exact file source URLs, available API/documentation URLs, local file counts, time ranges, units and unfulfilled Indian radar/INSAT/lightning access requirements. `GET /api/data/files/{file_id}` serves only manifest-listed files after size and SHA-256 verification. It cannot download arbitrary server paths or arbitrary remote URLs.

The optional collection environment is separate from the app:

```powershell
python -m venv .venv-data
.\.venv-data\Scripts\python.exe -m pip install -r requirements-data.txt
.\.venv-data\Scripts\python.exe scripts\collect_india_data.py
.\.venv-data\Scripts\python.exe scripts\collect_noaa_data.py
.\.venv-data\Scripts\python.exe scripts\collect_gfs_data.py
.\.venv-data\Scripts\python.exe scripts\prepare_government_pack.py
.\.venv-data\Scripts\python.exe scripts\verify_government_data.py
```

These collectors retrieve allowlisted fixed historical samples; they are not continuous weather ingestion. The GFS command above retrieves its raw subset. Its optional `--decode` path has an additional wgrib2 requirement described in that script and the government collection notes. The government preparation utility produces useful decoded examples, **not matched lightning-training episodes**.

The web collection button requires `VAJRA_ENABLE_COLLECTIONS=1` in the API server environment. `POST /api/data/collections/india` (or `noaa`, `gfs`) requires JSON body `{}`, a direct loopback client, a local Host header and a trusted browser Origin. It starts at most one fixed collector job at a time; repeat requests for the same active collection return that job. Poll `/api/data/jobs/{id}`. Job status is kept in the local server process and is not a durable production queue. The API allows no user-provided command, URL or filesystem path. A LAN-connected phone can read the catalog but cannot trigger collection.

Review [the collected-file inventory](../data/government/README.md) and [India collection evidence](../research/GOVERNMENT_INDIA_COLLECTION.md). Sparse SYNOP, a single NASA point, one GFS time and US reference samples have incompatible dates/spatial support and lack Indian lightning labels. Their presence on disk is not a training-readiness signal.

## 3. Optional CPU/GPU training environment

Keep PyTorch out of the web API environment:

```powershell
python -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install numpy==2.5.2
.\.venv-ml\Scripts\python.exe -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
```

The verified smoke environment is Windows/Python 3.14 with NumPy 2.5.2 and **PyTorch 2.14.0+cpu**. For CUDA, use the [official PyTorch installation selector](https://pytorch.org/get-started/locally/) for your operating system and driver, rather than the CPU index above. `--device cuda` fails clearly if CUDA is unavailable. This delivery verified CPU execution; it does not claim a tested GPU throughput.

Run a complete, small software smoke experiment:

```powershell
.\.venv-ml\Scripts\python.exe scripts\train_images.py smoke --output artifacts\my-image-smoke
.\.venv-ml\Scripts\python.exe scripts\train_images.py validate --data artifacts\my-image-smoke\episodes
.\.venv-ml\Scripts\python.exe scripts\train_images.py evaluate --data artifacts\my-image-smoke\episodes --checkpoint artifacts\my-image-smoke\run\model.pt
```

Use a new output directory per smoke run. This creates six **synthetic moving-blob episodes**, uses four for fitting, one for model selection and one for final testing, trains one CPU epoch, and saves `model.pt` plus `report.json`. It establishes that loading, causal masking, optimization, checkpointing and frozen-test evaluation execute. It establishes no meteorological skill. The verified run under `artifacts/image-training-smoke/` produced test Brier about **0.1982** and **CSI 0** at threshold 0.5: it missed the synthetic positive pixels. This poor short-run score is reported rather than described as successful weather prediction.

## 4. Required episode format

One `.npz` file is one bounded episode or tile from an episode. Related tiles must share `event_id`. Loading uses `allow_pickle=False`; timestamp arrays must be strings, not Python datetime objects. Arrays are:

| Key | Shape | Meaning |
|---|---|---|
| `values` | `[T,C,H,W]` | Physical or explicitly defined input channels. |
| `masks` | same | Boolean/0–1 validity; valid values must be finite. |
| `times_utc` | `[T]` | Strictly increasing, equally spaced UTC issue/acquisition-end timestamps. |
| `available_at_utc` | `[T,C]` | Recorded readiness per source channel, or explicitly declared research-latency assumption; never before acquisition end. |
| `targets` | `[T,H,W]` | Binary target corresponding to the issue at each `times_utc[t]`. |
| `coverage` | same | True only where the complete target interval and spatial neighborhood meet the declared detection-coverage rule. |
| `target_end_utc` | `[T]` | Exactly issue plus the declared positive horizon. |
| `metadata_json` | scalar Unicode string | JSON metadata described below. |

Required metadata keys are `event_id`, ordered `channels`, matching `units`, `grid`, `target_definition`, `horizon_minutes`, `availability_mode`, `provenance` and `scope`. `grid` must describe the CRS, shape, orientation, origin/transform and spatial support for real data. `target_definition` must fix the observed event type/provider, spatial neighborhood, interval boundaries, duplicate/quality handling and coverage policy. The validator requires these declarations and compatible episodes; it cannot independently prove that an upstream provider decoder or label builder implemented them correctly.

Use `availability_mode="recorded"` only with actual historical readiness evidence; otherwise use `"assumed_research_latency"` and explain the assumption in provenance. Do not invent readiness timestamps, lightning events or timezone conversions to satisfy the schema. `scope` distinguishes synthetic experiments from named observed datasets. Source SHA-256s, product versions, spatial transforms and label provenance belong in the metadata's provenance record.

For the proposed Indian target, labels would describe at least one qualifying observed event within 8 km during `(issue, issue+30 minutes]`. Preparing those labels requires a suitable event feed and coverage evidence; this release does **not** manufacture them from rainfall, radar reflectivity or official warnings.

## 5. Prepare, validate, train and evaluate your matched episodes

First implement the provider-specific decoding/alignment and coverage-aware target construction using authorized observations. For each independent episode, place these files in `matched-source/<episode-name>/`: `values.npy`, `masks.npy`, `times_utc.npy`, `available_at_utc.npy`, `targets.npy`, `coverage.npy`, `target_end_utc.npy` and `metadata.json`. The preparation CLI packs and validates those existing arrays; it does not invent missing data or perform a sensor-specific geophysical retrieval.

```powershell
.\.venv-ml\Scripts\python.exe scripts\prepare_image_episodes.py --source matched-source --output training-episodes --history 6
.\.venv-ml\Scripts\python.exe scripts\train_images.py validate --data training-episodes --history 6
.\.venv-ml\Scripts\python.exe scripts\train_images.py train --data training-episodes --output artifacts\regional-experiment-01 --history 6 --epochs 20 --batch-size 4 --device cpu
.\.venv-ml\Scripts\python.exe scripts\train_images.py evaluate --data training-episodes --checkpoint artifacts\regional-experiment-01\model.pt
```

The software minimum is **six independent event groups**, not a scientifically sufficient sample-size recommendation. The tiny French replay, raw government files and a directory containing one episode fail the training contract. Do not split one storm into differently named groups to satisfy this check.

The default path orders groups chronologically, with approximately 60–80% train and the remaining groups split between validation/test, subject to at least one group each. A conservative purge rejects overlap of acquisition/future-label intervals across the partition boundaries. Channels, grid, cadence, target and scope must match. Means and standard deviations use only training measurements that enter at least one covered causal input window; each measurement is counted once. Permanently unavailable measurements cannot influence these statistics. Each sample uses a causal history ending at its issue; channel data received later are zero-filled **after normalization** with a separate false mask. They are not treated as zero physical measurements. Covered positives and negatives use the same loss mask.

The model is a compact 12-hidden-channel ConvLSTM with a dense binary output. It receives normalized values and validity masks. Training uses masked binary cross entropy with logits, Adam and gradient clipping. Validation Brier score selects the checkpoint; the test partition is evaluated after selection. Outputs are uncalibrated by default. The checkpoint pins episode-file hashes, group splits, normalization, metadata and model architecture; standalone evaluation rejects a changed corpus. There is no automatic promotion into the API or live public-warning path.

Use `train --calibrate` to reserve separate training, model-selection validation, calibration and test groups. This path requires at least eight independent groups, with at least two each reserved for validation, calibration and test. That minimum is a software requirement, not enough evidence for a deployed weather model. A regularized temperature fit uses only calibration groups after selecting the checkpoint. Saved evaluation does not refit it. Reports include raw and adjusted probabilities' reliability bins, Brier/log loss/AP, threshold scores, training-climatology skill and whole-event bootstrap intervals.

```powershell
.\.venv-ml\Scripts\python.exe scripts\train_images.py smoke --output artifacts\image-training-smoke\my-calibration --calibrate
.\.venv-ml\Scripts\python.exe scripts\train_images.py evaluate --data artifacts\image-training-smoke\my-calibration\episodes --checkpoint artifacts\image-training-smoke\my-calibration\run\model.pt
```

The [calibration guide](CALIBRATION_AND_VERIFICATION.md) gives the exact split, fitting and uncertainty definitions. The verified synthetic smoke improved Brier from 0.211584 to 0.089959, but the climatology baseline remained better at 0.089687. Calibration is not a guarantee of skill or a substitute for independent Indian observations.

## 6. Efficiency, validation and remaining gates

Start with a compact crop, modest channels/history and CPU smoke. Increase batch size only after measuring memory and step time. This first CLI loads bounded episodes and materializes windows in RAM; it is not a streaming national-scale trainer. For larger archives, implement chunked/lazy reading and a reproducible sampler before expanding the corpus. Training on a haloed 192 × 192 tile needs measurement on the intended device. No GPU-memory or latency guarantee follows from the 16 × 16 smoke.

The current CLI has no automatic mixed precision, distributed training, augmentation, hyperparameter search or graphical reliability plot. Calibration, tabular reliability and bounded event-bootstrap intervals are implemented. Fix episode/target correctness first, compare same-cohort persistence/climatology and appropriate domain baselines, then assess probability quality and realistic feed outages on untouched events. The present intervals exclude model-fitting uncertainty; a tiny event count cannot establish a dependable regional interval.

Relevant verification commands:

```powershell
python -m unittest tests.test_image_data -v
python -m unittest discover -s tests -p "test_*.py" -v
```

The focused tests cover linear-reflectivity smoothing, missingness, flow direction, future-frame independence, equal scoring support, API boundaries, collection origin/host/loopback checks, file integrity, split overlap, UTC validation and exclusion of late inputs and holdout values from the corresponding training operations. Independent Indian validation, matched multi-season data, calibrated probabilities and accountable operational deployment remain necessary before claiming an Indian forecasting service.

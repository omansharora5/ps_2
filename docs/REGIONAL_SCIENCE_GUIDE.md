# Lightning, onset and seasonal research methods

The new code can train a small image model with three heads: lightning within the forecast horizon, first-rain timing, and first-lightning timing. It can also fit phase-dependent lightning calibration and a seasonal radar/rain correction. These methods work on test fixtures; we have not established Indian lightning skill, reliable block-scale onset times, or superiority to Damini/IMD.

The original scalar ConvLSTM in `scripts/train_images.py` remains unchanged. `nowcast/regional_heads.py` is a separate experimental architecture. No checkpoint from this workflow becomes an operational warning model automatically. No LLM is involved.

## Run the complete computation

From the repository root in PowerShell:

```powershell
.\.venv-ml\Scripts\python.exe scripts/train_regional_heads.py smoke --output artifacts/regional-research --steps 20
.\.venv-ml\Scripts\python.exe -m unittest tests.test_regional_science tests.test_regional_heads -v
```

The smoke command creates eight clearly named synthetic events, trains on two, selects weights using two separate validation events, fits lightning calibration on two calibration events, and evaluates on two test events. This very small dataset verifies plumbing only. It saves a checkpoint, reloads it and checks that predictions agree. The output directory is derived from the corpus, code, library versions and training settings. An identical retry verifies and reuses the existing output; changed settings create another run. Partial staging directories are not published runs.

Each published run contains `checkpoint.pt`, `report.json`, `test_predictions.npz` and an integrity manifest. The JSON reports losses, lightning reliability bins, fitted phase temperatures, sample counts and synthetic scope. The prediction archive includes each onset-bin probability and the probability of no event during the horizon. Scores from these synthetic samples must never be used in a public weather performance claim.

## What the heads calculate

Recent image frames pass through a shared compact ConvLSTM. Every input channel has a value, a usable-data mask and an observation-age channel. A frame acquired earlier but delivered after issue time is masked. Channel means and standard deviations are fitted from causal training inputs only.

The lightning head uses covered binary cross-entropy: a detected lightning event within the horizon is positive; a covered period with no event is negative. No strike record without network coverage is **unknown**, not negative. Labels must identify lightning type, detection coverage and geographic/time support. The adapter does not assume that a reference to 2019 INCOIS data provides matched training imagery or permission to redistribute it.

The two timing heads learn a conditional hazard for each interval, normally `(0,5], (5,10], …, (25,30]` minutes after issue. A hazard answers: “If the event has not happened yet, how likely is it in this interval?” Multiplying the previous survival probabilities by the next hazard gives the event probability for that interval. The leftover survival probability represents no event within the horizon.

For an event in interval three, training uses “survived intervals one and two, then event in three.” If observation stops after interval two, training uses only the observed survival prefix. It does not teach the remaining intervals to be dry. Covered onset targets require a known event-free starting state. Locations where rain is already occurring need a separate continuation/end model; this implementation does not predict when heavy rain ends.

`onset_summary()` gives a **conditional interval**, such as 10–20 minutes after issue if an event happens within the horizon, plus a separate probability of no event. It does not produce an unsupported exact minute. Hazard outputs are currently uncalibrated research probabilities. The binary lightning and onset heads are fitted separately and can disagree; do not silently substitute one for the other or publish either without held-out assessment.

## Prepare observed training data

Create one bounded NPZ following `make_fixture()` as a format example. Use actual observations and provenance for observed datasets; never relabel synthetic arrays as observations.

| Array | Shape | Meaning |
|---|---|---|
| `values`, `masks` | `[N,T,C,H,W]` | Physical channels and usable-input masks |
| `times_utc` | `[N,T]` | Acquisition end of each history frame |
| `available_at_utc` | `[N,T,C]` | When each input channel became available |
| `issue_utc`, `target_end_utc` | `[N]` | Forecast issue and end of its horizon |
| `event_ids`, `roles` | `[N]` | Storm/event group and `train`, `validation`, `calibration`, or `test` |
| `phases`, `phase_available_at_utc` | `[N]` | `onset`, `active`, `break`, `unknown`; when that phase was knowable |
| `lightning_targets`, `lightning_coverage` | `[N,H,W]` | Horizon event outcome and valid label support |
| `rain_event_bin`, `lightning_event_bin` | `[N,H,W]` | Zero-based first-event bin; `-1` means no event seen before censoring |
| `rain_observed_bins`, `lightning_observed_bins` | `[N,H,W]` | Number of consecutive observed intervals from issue; never bridge missing gaps |
| `rain_coverage`, `lightning_onset_coverage` | `[N,H,W]` | Valid timing examples |
| `rain_at_risk`, `lightning_at_risk` | `[N,H,W]` | Known event-free initial states according to the declared target |
| `metadata_json` | Scalar string | JSON contract described below |

Metadata requires `schema_version: 1`, unique `channels`, corresponding `units`, native `grid`, `bin_edges_minutes`, `scope`, `availability_mode`, `label_provenance` and `target_definition`. Use `scope: "observed_research"` and distinguish recorded availability from assumed research latency. Preserve original native resolution; interpolating coarse satellite rain onto small cells does not create small-cell truth.

The bounded prototype accepts 8–256 samples, 2–12 history frames, 1–16 channels and grids up to 64×64, with at least two independent events in each of four partitions. These are computation limits and minimum plumbing checks, not statistical sufficiency. Every training sample needs at least one covered task. Each event belongs to one partition only; adjacent partitions must not overlap input or target time. Missing targets can remain missing under their masks. Any covered first-lightning detection must imply a positive binary occurrence wherever that label is covered, even if later intervals are censored. Full-horizon lightning event/onset targets must also agree on no-event outcomes.

```powershell
.\.venv-ml\Scripts\python.exe scripts/train_regional_heads.py validate --corpus data/private/ncr-regional.npz
.\.venv-ml\Scripts\python.exe scripts/train_regional_heads.py train --corpus data/private/ncr-regional.npz --output artifacts/ncr-regional-research --steps 100
```

The regional factory currently starts a small model from random weights. It does not load Google WeatherNext, STLDM or scalar-ConvLSTM checkpoints into this incompatible head layout. Transfer learning needs a separate compatible encoder conversion and held-out evaluation; we do not claim it is already implemented.

## Inference without future labels

`scripts.train_regional_heads.predict_history()` accepts a checkpoint and only causal observations. It requires `values`, `masks`, `times_utc`, `available_at_utc`, `issue_time`, and an `input_contract` whose channels, units, grid and availability mode match the checkpoint. It also requires separate boolean `[H,W]` masks `rain_at_risk` and `lightning_at_risk`: true only where observations available by issue establish the event-free starting state under the same target definition used for training. An unknown state, rain already in progress, or an already active lightning episode must be false; missing detections alone cannot establish an event-free state. The caller must obtain this eligibility from adequately covered observations, not from future labels or the model's own prediction.

Optional `phase` and `phase_available_at` support the fitted lightning calibrator. The function returns lightning occurrence probabilities, two onset distributions and missing-input fraction, always marked `operational: false`. Each onset distribution has an explicit `eligible` mask. Event-bin, cumulative and no-event probabilities are `NaN` where eligibility is false, so an ongoing event cannot appear as a newly predicted onset. Stored test-prediction archives apply the same masks. JSON adapters must represent these masked values as `null`, never zero or an invented time. The binary future-lightning occurrence probability is a separate task and remains available regardless of first-onset eligibility. Inference never reads future target arrays.

## Monsoon phase calibration

Use `PhaseEvent` with held-out **calibration** predictions, not training/test predictions. A phase annotation must already have been available at forecast issue. `fit_phase_calibration()` fits a pooled temperature and a phase temperature only when the configured event and class counts are met (defaults: four independent events and twenty covered positives and negatives). Sparse phases and `unknown` use a disclosed pooled fallback. These minima are configurable research choices requiring sensitivity analysis; they are not proof of calibration.

An external, versioned regional definition must establish onset/active/break labels. We have not implemented an authoritative Indian monsoon phase detector. Retrospective labels are valid for stratified retrospective analysis but cannot be presented as features available to a live forecast. `apply_phase_calibration()` enforces phase availability at inference.

## Seasonal radar/rain correction

`fit_seasonal_zr()` fits `log Z = log a + b log R`, where `Z = 10^(dBZ/10)` and `R` is **mm/hour**. Rows require event/season IDs, `role: "train"`, `dbz`, `rain_mm_h`, units, explicit `quality_passed`, matched-support evidence and `time_delta_seconds`. The implementation admits matched pairs within five minutes; adjust preparation and assess sensitivity for a real sampling protocol. Hourly gauge totals cannot be paired directly with one radar scan.

Zero-rain pairs are recorded as excluded from the logarithmic fit; negative rainfall and incompatible units are rejected. Each fitted group needs varying positive rainfall, at least six wet pairs and the configured number of independent events (default three). Sparse seasons fall back to the pooled fit. Coefficients outside declared broad research bounds are rejected rather than published. This is a simple log-regression baseline, with no claim that it fully corrects radar attenuation, beam height, clutter or gauge representativeness.

`evaluate_seasonal_zr()` accepts only test rows with events absent from fitting, and compares MAE/RMSE against configurable baseline coefficients (defaults `a=200`, `b=1.6`). It includes valid zero-rain test rows. Any local improvement must be demonstrated across independent seasons/events and accompanied by uncertainty analysis before claiming a scientific contribution.

## Warm rain, dust and verification limits

`quality_diagnostics()` exposes missing radar, reported rain with above-freezing cloud-top temperature and reported dust requiring precipitation quality control. These are descriptive flags. They are not trained warm-rain/dust detectors, and a temperature threshold is not a universal rain rule. Warm rain, dust, monsoon phase, lead time and source availability should become explicit held-out evaluation strata once suitable labels exist.

The tests check hand-computed censored likelihoods, normalized event/no-event mass, missing-label exclusion, time leakage, independent event splits, phase fallback, known synthetic Z–R recovery, held-out fitting rejection, checkpoint reload and idempotent reuse. They verify implementation behavior. They do not establish how many Indian lives the model could save or whether a thirty-minute warning will be reliable.

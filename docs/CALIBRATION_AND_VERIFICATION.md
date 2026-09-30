# Held-out calibration and probability verification

Implemented and verified on 30 September 2026. Grounding, two-design comparison, implementation and CPU verification are complete. Independent review identified a normalization availability bug, which is corrected and covered by a regression. The ConvLSTM architecture is unchanged.

## Grounding and design decision

`scripts/train_images.py::main` dispatches validation, training, evaluation and generated smoke runs. `load_episode` validates UTC times, regular cadence, channel/geometry compatibility, numeric masks and covered binary targets. `corpus` groups files by event ID and uses chronological splits with a conservative purge between acquisition and future-label windows. `normalizer` sees training events only. `examples` masks measurements that were not available at issue time. Training selects the checkpoint by validation Brier score; test evaluation runs after selection. No checkpoint enters the web application.

Two designs were considered before implementation:

| Candidate | Caller usage and ownership | Tradeoff |
|---|---|---|
| Standalone evaluator | `train`, then export predictions, then a separate `calibrate` command with calibration/test manifests | Supports external models, but callers must keep exports, selected weights and four split manifests aligned. A separate command can accidentally reuse test labels. |
| Integrated optional calibration, selected | `train --calibrate`, then `evaluate --checkpoint model.pt`; the CLI owns chronological split selection and frozen artifacts, while a small NumPy module owns probability scoring and temperature fitting | Keeps fitting after checkpoint selection and exposes one reproducible workflow. Retains the existing six-group default path. |

The integrated candidate hides split and artifact coordination inside the existing CLI. A separate pure probability module is justified by its statistical contract, not by adding a wrapper around each training step. Both candidates were checked for shared mutable state, duplicated label rules and reliance on callers to enforce causality. The integrated candidate keeps the model architecture unchanged.

## Usage and ownership

```powershell
.\.venv-ml\Scripts\python.exe scripts\train_images.py train --data episodes --output data/training_runs/calibrated --calibrate
.\.venv-ml\Scripts\python.exe scripts\train_images.py evaluate --data episodes --checkpoint data/training_runs/calibrated/model.pt
.\.venv-ml\Scripts\python.exe scripts\train_images.py smoke --output artifacts/image-training-smoke/calibration --calibrate
```

The probability module receives `EventPredictions(event_id, logits, targets, coverage)` and exposes `fit_temperature(events)` and `evaluate_events(events, training_rate, calibrator=None)`. Covered labels must be binary; covered logits must be finite. Values outside coverage are excluded. `fit_temperature` accepts only calibration events selected by the CLI. `evaluate_events` never fits parameters. It returns raw/calibrated scores, reliability bins and event-bootstrap intervals.

The calibrated path requires at least eight event groups. With `n` groups it reserves `max(2, floor(n/5))` groups each for model-selection validation, calibration and test, with remaining earliest events used for training. Eight groups is a software smoke minimum and leaves only two training groups. The latest future-label end of each split must precede the earliest acquisition in the next split; overlap is rejected rather than silently dropped. Every episode must use the same cadence. The default path retains the original six-group minimum and three-way split.

Grouping depends on the supplied event IDs. The CLI cannot establish meteorological independence: corpus curators must assign related storm windows and split/merge descendants to the same event group. Inventing a new ID for each overlapping window does not create an independent storm. Overlap within one split is allowed and is not treated as independent evidence.

Normalization counts each training measurement once if it occurs in at least one covered training window and was available by that window's issue time. `causal_input_mask` supplies the same availability rule to normalization and example creation. Permanently unavailable values cannot alter the statistics. A late measurement remains usable if it arrives before an issue whose input history still includes that measurement. A channel with no causally usable training measurements is rejected. These statistics are fitted once over the offline training period, not recalculated from validation, calibration or test inputs.

## Fitting order and artifacts

1. Freeze chronological event splits and the file manifest; derive causal training normalization and the covered training-target occurrence rate.
2. Fit the unchanged network on training windows. Select its checkpoint using raw validation Brier score.
3. Reload that selected checkpoint. If requested, fit the temperature using covered calibration labels only.
4. Freeze the temperature, then evaluate raw and adjusted probabilities on test events. Evaluation performs no optimization or threshold selection.

For selected-model logit `z`, the adjusted probability is `sigmoid(beta*z)`, with `temperature = 1/beta`. Fit the convex objective

```text
mean_calibration[log(1 + exp(beta*z)) - y*beta*z] + (0.001/2)*(beta - 1)^2
subject to 0.05 <= beta <= 20
```

The implementation solves its monotone derivative by bounded bisection. Samples are weighted equally per covered pixel-example, not per event. A single positive scale limits fitting freedom; an intercept-bearing Platt fit is deferred until a larger calibration corpus supports that extra freedom. Constant logits or single-class calibration labels return an identity transform with a specific status instead of claiming a fitted correction. The `calibrated` checkpoint flag means a temperature was fitted, not that reliability was established. Temperature scaling follows the general post-training method of [Guo et al., ICML 2017](https://proceedings.mlr.press/v70/guo17a.html); this bounded, identity-regularized objective is our implementation choice, not a claim of reproducing their experiments.

A positive temperature preserves ranking and the 0.5 boundary in exact arithmetic. It can adjust probability magnitudes, but cannot create missing storm predictors, fix all base-rate changes or guarantee improvement on held-out events. Finite-precision saturation can introduce score ties.

`model.pt` contains selected weights, training normalization and climatology, frozen calibration parameters, evaluation batch size, event lists, per-file SHA-256 values, per-split hashes and a corpus hash. `calibration.json` exposes parameters/manifests and the checkpoint hash for inspection. `report.json` contains raw/adjusted test scores and uncertainty. Frozen `evaluate` checks all episode bytes and the recomputed split manifest, including non-test files, before scoring. Moving an unchanged corpus is allowed; modifying it requires a new run. Checkpoint contents are authoritative for evaluation; the JSON sidecar is an audit record. Exact CPU reproduction is verified in the recorded environment; equality across hardware or library versions is not promised.

## What the reported metrics mean

Only cells with valid target coverage enter these scores. Unknown coverage is not a negative target. Probabilities and binary labels are validated on covered cells; invalid covered logits fail. Predictions outside coverage are excluded.

| Field | Definition and edge cases |
|---|---|
| `brier` | Mean `(p-y)^2` over covered pixel-examples; lower is better. |
| `log_loss` | Mean binary negative log likelihood; probabilities are clipped to `[1e-7, 1-1e-7]` for this score only. |
| `average_precision` | Non-interpolated sum of precision times recall increments at distinct score thresholds; tied scores share a threshold. This is AP, not ROC AUC or trapezoidal PR AUC. Null if no positives. |
| `reliability` | Ten fixed equal-width probability bins. Each reports count, mean forecast probability and observed frequency; empty-bin means are null. Lower edges are inclusive; the final bin also includes probability 1. |
| `pod`, `far`, `csi` | At the fixed threshold 0.5: `H/(H+M)`, `FA/(H+FA)`, `H/(H+M+FA)`. H = hits, M = misses, FA = false alarms. Zero denominators produce null. FAR means false-alarm ratio, not false-positive rate. |
| `training_climatology_brier` | Score the constant covered training-target occurrence rate on the same test cells. The constant is never estimated from test labels. |
| `brier_skill` | `1 - model_brier/climatology_brier`; negative means worse than that baseline. Null if baseline Brier is zero. |

The AP definition matches the [scikit-learn metric documentation](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html); the implementation here uses NumPy and adds no scikit-learn dependency. Reliability bin counts are support counts, not confidence bounds. No adaptive bins, ECE summary or test-selected alert threshold is fitted.

With at least two usable test events, a fixed-seed, 200-replicate cluster bootstrap resamples whole event groups with replacement. Each replicate pools the sampled groups' pixel totals, preserving the pixel-weighted estimand. It reports nominal 95% percentile intervals for Brier, log loss and Brier skill, plus the paired adjusted-minus-raw Brier difference. AP and reliability bins do not receive intervals. Models, normalization and calibrator stay fixed; uncertainty from their fitting is excluded. With fewer than two events the interval status is `unavailable`. Two related synthetic events can yield very narrow intervals while supplying almost no evidence about real deployment uncertainty.

## Executed verification and limitations

The tracked [smoke summary](../artifacts/calibration-smoke-summary.json) contains commands, environment versions, exact metrics, reliability bins, intervals and checkpoint/split hashes. Full generated episodes, weights and reports are under ignored `artifacts/image-training-smoke/calibration-v2/`.

| CPU synthetic smoke result | Raw model | Temperature-adjusted model |
|---|---:|---:|
| Test Brier | 0.2115840712 | 0.0899587523 |
| Test log loss | 0.6160474624 | 0.3272656478 |
| Average precision | 0.2217036478 | 0.2217036478 |
| Brier skill vs training climatology | -1.3591295461 | -0.0030261228 |
| POD / CSI at 0.5 | 0 / 0 | 0 / 0 |

Training-climatology Brier is **0.0896873474**, slightly better than the adjusted model. The temperature is 0.1109087449. Adjustment improves this undertrained model's probabilities toward the base rate, while all 306 positive test cells remain missed at threshold 0.5. Reliability gaps remain visible: the adjusted 0.1–0.2 bin has mean probability 0.1393 but observed frequency 0.0804. This exercise therefore demonstrates working calibration and verification software, not a reliable weather model.

The run used one training epoch, eight generated moving-blob event groups split 2/2/2/2, 12 test windows and 3,072 covered test pixel-examples. Frozen CLI evaluation exactly reproduced raw scores, adjusted scores and bootstrap results. The six-group default smoke also passed, with no calibrator and an explicitly unavailable interval for its single test group.

Thirteen new tests passed in `.venv-ml`, including actual Torch training, and four existing training-contract tests passed in the regular Python environment. Tests cover hand-computed scores/bins, tied AP, zero denominators, invalid coverage, degenerate fits, unequal-size event resampling, causal normalization, disjoint chronology and future-window rejection. A double-training integration test changes only held-out test labels: weights, normalization, validation history and calibration parameters remain identical; test scores change; frozen evaluation rejects the changed corpus. Another test changes a permanently unavailable training frame to `1e6` and verifies identical normalization, input tensors and network predictions while retaining a reachable late frame.

The ML environment intentionally lacks FastAPI, so the existing API-coupled test module was run with regular Python instead. The new probability suite and original training contracts both passed in their supported environments. No weights were promoted to the web or mobile app. Real India lightning labels, documented detection coverage, independently curated storms and held-out seasons/regions remain prerequisites for any forecasting skill claim.

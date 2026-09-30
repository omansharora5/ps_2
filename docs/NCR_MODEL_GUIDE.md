# NCR model preparation, weight reuse and causal inference

The compact ConvLSTM training pipeline can now initialize from a compatible local checkpoint and run a saved model at one episode issue time. These capabilities do not make the current checkpoint an NCR weather model. Existing demonstration weights use synthetic examples; no claim of NCR rain or lightning accuracy follows from successful execution.

## What can be reused

The existing model reads a sequence of measurement arrays and validity masks. Its convolutional recurrent state represents spatial patterns and their recent evolution, and a final head outputs one binary-event logit per cell. It is a small model that can be trained and checked locally. The repository's optical-flow implementation remains a useful movement baseline.

`--initialize-from` reuses **weights and their exact channel normalizer**, then optimizes the weights using the new training split. It starts a new optimizer and discards the previous calibrator. It does not download a pretrained model, make unrelated Google weights compatible, or infer Indian lightning from rain labels.

Compatibility checks require the compact architecture version, input-channel count and order, units, history length, exact grid metadata, event definition and forecast horizon to match. New checkpoints also record and check frame cadence and array shape. Legacy compact checkpoints can be used when the existing metadata matches; their unrecorded cadence is explicitly marked `cadence_verified: false`. Verify that cadence independently before interpreting such a transfer experiment.

Exact grid and target checks intentionally prevent casual reuse across regions or tasks. Transferring weights trained with a different geographic grid, resolution, sensor, event target or channel set requires a separately designed and tested adaptation. Renaming metadata to pass these checks is not adaptation.

## Build suitable NCR episodes first

An episode is an already decoded and aligned sequence. Downloaded station files, display PNGs and unrelated satellite/radar snapshots do not become an episode simply by sharing a folder.

| Field | Required meaning |
|---|---|
| `values` | Float array `[time, channel, height, width]` in declared units |
| `masks` | Same-shape observation validity, with gaps explicit |
| `times_utc` | Regular, increasing UTC acquisition/issue slots |
| `available_at_utc` | `[time, channel]` time at which the observation became usable |
| `targets` | Binary outcome at each issue's declared future interval; never a model's guess |
| `coverage` | Where the outcome is actually known; unknown is false, not dry |
| `target_end_utc` | Each issue plus the target horizon, such as 30 minutes |
| `metadata_json` | Event ID, channels, units, grid, target definition, horizon, availability mode, provenance and scope |

Rain targets must respect the measured accumulation interval. A six-hour amount cannot label individual 30-minute windows, and a station does not establish every surrounding grid cell's outcome. Lightning requires lightning observations and information about sensor coverage. A missing or failed feed is unknown.

Reserve separate event groups for training, validation, optional calibration and testing. The current software requires at least six groups, or eight with calibration; those are software minimums, not evidence of enough meteorological diversity. Keep acquisition and target windows separated across groups. Stable event IDs must follow the same storm across files and future training runs.

The initializer records all events in all its splits as prior exposure. A new validation, calibration or test group cannot use any of those event IDs, including exposure inherited through previous fine-tuning runs. This conservative rule also excludes events previously used only for evaluation. Reusing old training events in the new training split is allowed. IDs are not a substitute for scientific event identity: never rename the same storm to evade the exclusion.

## Commands

Use the optional ML environment from the repository root. The paths below represent prepared, observed episodes and separately reviewed compatible weights; they are not included NCR datasets.

```powershell
.venv-ml/Scripts/python.exe scripts/train_images.py validate --data data/ncr/episodes --history 3 --calibrate

.venv-ml/Scripts/python.exe scripts/train_images.py train --data data/ncr/episodes --output artifacts/ncr/candidate-001 --history 3 --epochs 10 --calibrate --initialize-from artifacts/compatible-source/model.pt

.venv-ml/Scripts/python.exe scripts/train_images.py evaluate --data data/ncr/episodes --checkpoint artifacts/ncr/candidate-001/model.pt
```

The training command refuses an output directory already containing `model.pt`. If no compatible checkpoint exists, omit `--initialize-from` to exercise the existing architecture with new weights, but do not call that fine-tuning. Selecting epoch counts and model capacity requires validation experiments; ten epochs above is only a usage example.

The resulting `model.pt` includes weight initialization provenance, SHA-256 of the source checkpoint, the full exposure ID set, normalizer, metadata and split hashes. `report.json` records held-out performance and the same initialization provenance. Calibration is fitted only if requested, using the new calibration split; there is no automatic model promotion.

## Run a saved model at a specific issue time

```powershell
.venv-ml/Scripts/python.exe scripts/predict_images.py --checkpoint artifacts/ncr/candidate-001/model.pt --episode data/ncr/episodes/observed-event.npz --index 5 --output artifacts/ncr/forecasts/issue-005-revision-0.npz
```

The issue time is `times_utc[5]`. With history three, only indices 3, 4 and 5 enter the model, and only measurements whose `available_at_utc` is no later than that issue time. Future frames, future rain/lightning outcomes and target coverage never enter the network. Inference still accepts the validated episode format: for an outcome not observed yet, use placeholder target values with all corresponding `coverage` false. That is unknown truth, not a dry label.

The horizon comes from the validated model metadata. A model trained for 30 minutes produces a 30-minute result; a synthetic ten-minute checkpoint remains a synthetic ten-minute checkpoint. There is no horizon override that relabels a model's output.

The output NPZ contains `probabilities`, `input_support` and `metadata_json`. Unsupported cells are NaN. Input support means at least one usable observation exists within the history at that cell; it does not prove adequate sensing, calibrated confidence or known outcomes. If every input is unavailable, inference abstains.

Probabilities are explicitly uncalibrated unless the checkpoint contains a supported, fitted temperature calibrator tied to its independent calibration split. A valid fitted calibrator is not proof of operational reliability. Assess held-out Brier score, calibration curves, missed events, false alarms and event-level uncertainty before any deployment decision. The command never sends an alert.

When new observations arrive, prepare a new causal input snapshot and write a new issue/revision artifact. Existing outputs cannot be overwritten. Preserve earlier forecasts for verification against later truth; correcting today's forecast must not rewrite yesterday's record. The CLI performs one inference invocation; it does not implement a live polling service or retrain automatically.

## Verification and remaining boundary

```powershell
.venv-ml/Scripts/python.exe -m unittest tests.test_image_transfer -v
```

Regression checks exercise real weight updates, preserved normalization, incompatible checkpoints, inherited exposure exclusion, causal masking, future-label independence, missing-data abstention, calibration provenance and immutable output names. They use synthetic fixtures to test software behavior, not weather accuracy. Indian satellite, numeric radar and lightning access, matching observed labels and independent NCR evaluation remain prerequisites for a credible NCR model.

# Public scorecards and benchmark manifests

The tools in this guide operate on supplied frozen observations. They do not generate NCR forecasts, claim an IMD comparison exists, or turn the current source catalogue into an aligned sensor corpus. Test fixtures exercise the code and are not published as weather results.

## Monthly scorecard

Run from the repository root:

```powershell
python scripts/publish_scorecard.py C:\private-data\scorecard-config.json --revision 1
```

The default output root is `data/community/publications`. The command writes an immutable, checksummed `YYYY-MM/r0001.json`. Running the same input and revision again is safe. Different content requires a new revision. Prior revisions are retained; the reader verifies and returns the latest revision. A changed or malformed latest file fails instead of quietly falling back to old scores.

Python entry points in `nowcast.public_verification`:

```python
card = build_scorecard(config)
card = publish_scorecard(root, config, revision=1)
card = read_scorecard(root, "2026-09")
```

Without a published file, the reader returns `status: unavailable`, the month and an explanation. It does not manufacture a demonstration score. The community API can expose this same verified reader without importing PyTorch.

### Frozen configuration

The configuration is a JSON object with the following fields. Fill it from real archives; these are schema descriptions, not observational records.

| Field | Meaning |
|---|---|
| `month` | `YYYY-MM`, selected by each case's target start in UTC |
| `publication_cutoff` | Explicit UTC timestamp; outcomes received after this time are excluded |
| `model_id` | Version of the frozen evaluated model |
| `hazard`, `label_definition` | Exact hazard and versioned event/threshold definition |
| `lead_time_seconds` | Integer gap from issuance to target-window start; zero for the immediately following interval |
| `target_duration_seconds` | Positive integer duration; 1800 for a 30-minute window |
| `threshold` | Probability decision threshold fixed before this test |
| `training_climatology` | Event frequency estimated from training data, never fitted from this month's outcomes |
| `train_event_ids`, `validation_event_ids`, `calibration_event_ids` | Complete training, model-selection validation and calibration exposure lists; evaluation events must not appear in any. `validation_event_ids` may be omitted only when no validation events were used. |
| `cases` | Frozen case records described below |
| `comparator` | Optional categorical bulletin archive described below |

All timestamps require a UTC offset (`Z` or `+00:00`). All SHA256 fields require 64 lowercase hexadecimal characters. Provenance hashes must identify real archived records; passing a syntactically valid invented hash does not establish scientific evidence. The publication operation hashes the complete input configuration but does not copy raw case records into the public scorecard.

Each case contains:

```text
case_id, event_id
hazard, label_definition
geometry_id, geometry_sha256
issued_at, target_start, target_end
forecast_archived_at, forecast_record_sha256
probability: finite number in [0,1]
data_mode: "observed"
truth:
  observed: integer 0 or 1
  source_kind: "instrument"
  source_id, record_sha256
  coverage_complete: true
  available_at
  target_start, target_end
  geometry_sha256, label_definition
monsoon_phase: optional {value, source_id, available_at}
season: optional {value, source_id, available_at}
```

`geometry_sha256` identifies the versioned polygon/grid-support definition, including the sampling rule. A station report at one point cannot establish “rain everywhere in the block.” Define an observation-supported task first, then use exactly that task on both predictions and labels. This first implementation accepts only independent instrument truth in the public scorecard; reviewed citizen observations remain available for separate research datasets.

The model forecast must have been archived by its declared issue/decision deadline. Complete truth must have the same geometry, label definition and interval, and become available after the interval ends but by publication cutoff. Missing coverage, late truth, synthetic cases, crowd labels and late forecast archives are explicitly counted as exclusions. Duplicate cases, exposure leakage, nonfinite probabilities, impossible chronology or a changed task horizon fail validation. Renaming a case or geometry does not allow the same event/hazard/label/polygon/window to be counted twice; timestamp spelling is normalized for this check. Training, validation and calibration exposure lists must be mutually disjoint, and a case used to choose the model is not an untouched test case.

Optional phase/season values must include their source and availability. A phase discovered retrospectively after issuance is scored in `unknown`, so a future three-day monsoon classification is not silently used as an operational condition. This does not automatically verify the scientific phase definition; register and audit the stated source.

### Metrics and comparison

The result contains case/event counts, hits, misses, false alarms, correct negatives, POD, FAR, CSI, Brier score and reliability bins. Empty denominators are `null`. FAR means **false-alarm ratio**. The Brier skill baseline uses the supplied frozen training climatology. Whole-event bootstrap intervals for POD/FAR/CSI/Brier use 200 deterministic resamples; at least two events are required, and few events produce unstable intervals. Resampling bounds memory to one replicate at a time. These intervals exclude uncertainty from model/calibrator training.

`strata.monsoon_phase` and `strata.season` expose the same metrics for supplied categories. Splitting a small month into many groups can leave too few events to interpret; this interface makes sample counts visible rather than claiming improvement.

An optional comparator has:

```text
name: e.g. a documented IMD product name
kind: "categorical"
cases:
  case_id, event_id, hazard, label_definition
  geometry_id, geometry_sha256
  issued_at, target_start, target_end
  archived_at, archive_sha256, source_id
  prediction: integer 0 or 1
```

The case/event/hazard/definition/geometry/target-window identity must match an admitted model case exactly. The comparator must have been issued and archived no later than that model's issue deadline; an archive cannot precede its own bulletin issuance. Incompatible/late bulletins are excluded and counted. `comparison.model` and `comparison.comparator` use only their common matched cohort. A district three-hour bulletin cannot be silently relabelled as a block 30-minute forecast.

Categorical IMD bulletins receive contingency metrics only. They do not receive invented probabilities, Brier scores or reliability diagrams. With no compatible archive, comparison status is unavailable. These are local publication files; no automatic scheduler or external publication service is enabled by these commands.

## Benchmark preparation

```powershell
python scripts/prepare_benchmark.py C:\private-data\benchmark-config.json --base-dir C:\private-data\matched-episodes --output data/community/publications/benchmark.json
```

Python entry points:

```python
manifest = prepare_benchmark(config, base_dir, output)
public_status = read_benchmark(output)
```

The tool reads and hashes the actual files, checks chronology and split separation, and writes **metadata and recipes only**. It never copies raw data or uploads anything. The output is immutable; use a new versioned path for a revised release candidate. The optional conventional `benchmark.json` is a single immutable snapshot, not a mutable “latest” pointer.

Configuration:

```text
benchmark_id
frozen_at: UTC cutoff
artifacts:
  path: relative file within base_dir
  sha256, source_id
  event_id
  split: "train" | "validation" | "calibration" | "test"
  data_mode: "observed"
  input_start, input_end, input_available_at, issued_at
  target_start, target_end, truth_available_at
  target_duration_seconds
  label_definition, geometry_sha256
  label_coverage_complete: true
  recipe: reproducible acquisition/preprocessing reference without credentials or personal details
  privacy_review: "approved" or a pending review state
  redistribution: optional
    allowed: true or false
    license: exact applicable licence/agreement identifier
    evidence: permission record/reference
```

An artifact represents an aligned, labelled episode, not an isolated screenshot or a common static terrain file. Source manifests and recipes should preserve all constituent sensor provenance, quality masks, units, native support and processing steps. The generic manifest validator does not decode imagery or independently establish that the scientific alignment is correct.

The required chronology is:

```text
input_start <= input_end <= input_available_at <= issued_at
            <= target_start < target_end <= truth_available_at <= frozen_at
```

Files must exist within `base_dir`; path escapes and mismatched hashes fail. An event or identical episode content cannot cross partitions. Windows are chronologically separated in the order training, optional model-selection validation, calibration, test, including their input histories and targets. Training, calibration and test are required for release readiness; the optional validation partition does not replace any of them. Declared target duration must match the timestamps. Synthetic artifacts and incomplete labels fail admission to this observed benchmark.

Missing per-file redistribution permission or unfinished privacy review leaves `release_ready: false` and lists the blockers. Missing partitions also blocks readiness. Even with permissions supplied, `export_mode` stays `metadata_and_recipes_only`, and `raw_files_exported` stays zero. Permissions are explicit supplied attestations, not legal rights created by this program.

`read_benchmark` verifies the envelope checksum before serving metadata. With no file it reports metadata-only status, `raw_release_allowed: false`, and missing corpus/rights blockers. Existing manifests report whether their recorded checks permit a later raw release; the reader does not re-open private raw files and does not serve them. SHA256 detects accidental changes, not malicious rewrites by an actor with publication-directory write access; restrict that directory to trusted local publication jobs.

MOSDAC restricts redistribution of downloaded products without the relevant agreement. Therefore a successful download, a government URL or a cropped INSAT file is not automatic raw-release permission. Keep acquisition recipes and request redistribution rights where required. [Official MOSDAC guidelines](https://www.mosdac.gov.in/look/DOCS/mosdac-data-guidelines_english.pdf). Scientific context and prior-art corrections are in [the evidence note](../research/REGIONAL_FEATURE_EVIDENCE.md).

## Verification

```powershell
python -m unittest tests.test_public_verification -v
```

Tests cover known metric arithmetic, undefined denominators, excluded observations, duplicate physical cases under renamed IDs, model-selection exposure, future-phase leakage, matched-cohort comparison, late archives, immutable revisions, checksum tampering, permission/privacy gates, path escape, label coverage and chronology across training/validation/calibration/test splits. Fixture data are explicitly identified as tests; these checks establish implementation behaviour, not weather skill.

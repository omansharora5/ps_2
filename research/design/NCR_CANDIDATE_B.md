# Candidate B: durable NCR observation ledger

## Problem

Current `/api/runs` serves synthetic inputs or French historical radar, while the collector downloads fixed snapshots. NCR work needs an auditable timeline of actual observations, explicit access failures, interval-correct rain labels and forecasts that can abstain. Existing `operation_store` and its single-owner worker already provide durable bounded jobs; `observations.select_as_of` enforces issue-time availability and `train_images` enforces causal episode splits. Extend those ownership boundaries without routing network downloads through HTTP requests.

## Usage (caller's view)

```console
python scripts/collect_ncr_data.py --latest --lookback-hours 72
python scripts/collect_ncr_data.py --start 2026-09-01 --end 2026-09-30
python scripts/ncr_model.py prepare --ledger data/ncr/observations.sqlite --horizon-minutes 30
GET /api/ncr/status
GET /api/ncr/observations?source=imd_surface&start=2026-09-29T00:00:00Z
GET /api/ncr/forecast?issued_at=2026-09-30T06:00:00Z
```

```python
# CLI/registered worker recipe: owns writes; date range is bounded at admission.
ledger = NcrLedger.writer(root)
receipt = ledger.collect(CollectionWindow.latest(hours=72), sources=verified_sources)
print(receipt.source_results)  # actual latest observed times, not collection wall time

# API: local reads only; status explicitly separates connected from training-ready.
reader = NcrLedger.reader(root)
return reader.status(as_of=clock.now())

# Model worker: remains an abstention when only coarse observations exist.
result = ledger.forecast(issue_time, model=registered_model, horizon=Minutes30())
# ForecastResult is either an immutable prediction revision or an explained abstention.
```

## Shape

Types below are sketches; constructors validate provider-boundary facts once.

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime  # UTC, strictly increasing; provider accumulation convention retained

@dataclass(frozen=True)
class Accumulation:
    millimetres: float
    interval: Interval
    evidence_sha256: str
    quality: Literal['accepted', 'suspect']
    trace: bool  # provider trace is never silently converted to a measured zero

@dataclass(frozen=True)
class Observation:
    identity: str  # provider + station/grid + variable + interval + revision + raw hash
    source: str
    footprint_id: str
    valid_time: datetime
    available_at: datetime  # first known availability, never inferred from valid time
    raw_sha256: str
    precipitation: Accumulation | None
    fields: tuple['MeasuredField', ...]  # value, unit, quality, spatial support

@dataclass(frozen=True)
class RainLabel:
    interval: Interval
    footprint_id: str
    state: Literal['rain', 'dry', 'unknown']
    evidence: tuple[str, ...]
    reason: str

@dataclass(frozen=True)
class ForecastRevision:
    identity: str  # hash(issue_time, horizon, input identities, model version)
    issued_at: datetime
    valid_interval: Interval
    input_ids: tuple[str, ...]
    model_version: str
    probabilities_path: Path
    supersedes: str | None

@dataclass(frozen=True)
class Abstention:
    issued_at: datetime
    missing_requirements: tuple[str, ...]

ForecastResult = ForecastRevision | Abstention

class NcrLedger:
    @classmethod
    def writer(cls, root: Path) -> 'NcrLedger': raise NotImplementedError
    @classmethod
    def reader(cls, root: Path) -> 'NcrLedger': raise NotImplementedError
    def collect(self, window: 'CollectionWindow', *, sources: tuple['Source', ...]) -> 'CollectionReceipt': raise NotImplementedError
    def status(self, *, as_of: datetime) -> 'Readiness': raise NotImplementedError
    def observations(self, query: 'ObservationQuery') -> tuple[Observation, ...]: raise NotImplementedError
    def episodes(self, spec: 'EpisodeSpec') -> 'EpisodeExport': raise NotImplementedError
    def forecast(self, issue_time: datetime, *, model: 'RegisteredModel', horizon: 'Minutes30') -> ForecastResult: raise NotImplementedError

def rain_label(measurements: tuple[Observation, ...], target: Interval, footprint: str) -> RainLabel:
    raise NotImplementedError  # Pure: exact coverage/quality, no distributing daily totals.
```

**Persistence and access patterns.** SQLite stores `collection_attempt`, `observation`, `source_access`, `forecast_revision` and `model_registration`. Immutable raw payloads and array artifacts live in content-addressed files. Index observations by `(source, footprint_id, valid_time, available_at)` and accumulation intervals by `(footprint_id, start, end)`. Index revisions by `(issued_at, created_at)`. Latest views are derived queries, not separately synchronized status files. Source capability records distinguish open observations, account-required, permission-required and temporarily failed access.

**Concurrency and retries.** The existing worker is the sole ledger writer. Each download uses its own staging directory; verified blobs are atomically published before the database transaction references them. A crash may leave an unreferenced blob, never an accepted partial payload. Unique immutable identities make replay a no-op; differing provider corrections become separate versions. The API uses a read-only connection and never performs collection. SQLite WAL supports readers; existing worker ownership handles execution exclusion. Do not introduce a second scheduler or HTTP-owned collector.

**Label contract.** Dry requires a valid explicit zero covering the exact target interval and footprint. Positive or trace precipitation establishes rain only over its reported interval. A one-hour positive total cannot label either half-hour as rain. Missing, suspect, ambiguous accumulation periods and uncovered intervals remain unknown. Station footprints cannot label all NCR grid cells. Historical retrieval time remains known; operational backtests require separate defensible availability evidence, otherwise exports are marked unsuitable for latency evaluation.

**Model contract.** A registered model declares channels, units, cadence, input spatial support, target type, horizon, weights provenance and code/weights licences separately. Reuse existing persistence/optical-flow and compact ConvLSTM training boundaries. A third-party pretrained model is admitted only after matching its normalization and labels; reference STLDM cannot be relabelled as an Indian lightning model. Google research informs probabilistic ensemble design, but architecture inspiration does not supply weights, sensor decoders or NCR validity. Rain and lightning readiness remain separate.

**Revision contract.** New accepted scans create a new input identity and immutable 30-minute forecast; the old forecast stays available for verification. Models use only observations available at issue time. Retraining is a separate candidate job and never part of each revision. No calibrated confidence, missing sensor data or fine-resolution rainfall is invented. A 30-minute API can honestly return an abstention with missing radar/satellite/labels requirements.

**Module map.** `nowcast/ncr.py` owns domain types, ledger schema, pure labels and three caller operations; `nowcast/ncr_sources.py` hides HTTP, pagination, credentials, provider units and field decoding; `scripts/collect_ncr_data.py` and `scripts/ncr_model.py` are thin CLI boundaries. `service.py` exposes read-only routes; a registered recipe reuses the current worker. Training exports preserve the existing `prepare_image_episodes.py` schema, group splits and calibration separation. Common traces cross at most three modules. Boundary validation and immutable identities follow boundary-discipline and make-operations-idempotent.

## Synthesis decision

Pending comparison. This candidate concentrates observation history, readiness and revision ownership in one durable ledger rather than composing independently mutable collection manifests.

## Tradeoffs accepted

- Accept a small schema migration and one writer in exchange for atomic provenance and consistent temporal queries.
- Accept explicit abstention and fewer eligible examples in exchange for truthful 30-minute labels.
- Accept separate immutable array blobs in exchange for keeping large images outside SQLite transactions.

## Alternatives considered

- Per-run JSON manifests are easier to inspect manually but expose cross-run deduplication, corrected records and latest selection to each caller; the ledger hides those rules.
- A streaming broker and separate ingestion microservices hide transport retries but add deployment and ownership complexity beyond this single-region prototype.

## Open questions and risks

- Which verified NCR providers expose accumulation intervals and availability evidence sufficient for a 30-minute target?
- Which official NCR boundary or documented research bounding box should be versioned as the spatial scope?
- Do provider licences permit model training and redistribution of downloaded samples or only derived artifacts?

## Next implementation step

Add the ledger schema, one verified public NCR surface-data adapter and interval-label tests; expose readiness before enabling model execution on those observations.

# Candidate A: immutable NCR collections and a guarded model path

Phase: grounded and sketched; synthesis and implementation belong to the orchestrator.

## Usage (the caller's view)

These are proposed interfaces, not commands already implemented.

```powershell
python scripts/collect_ncr_data.py --start 2026-09-01 --end 2026-09-30
python scripts/ncr_model.py prepare --collection data/ncr --output data/ncr/episodes
python scripts/train_images.py validate --data data/ncr/episodes
```

The collector attempts documented public sources and writes a dated report even when every provider fails. Dates bound acquisition requests, not an assertion that records exist. The model command exits with explicit blockers when matched inputs and targets cannot be built; it never substitutes synthetic observations.

```python
# Thin CLI: one call owns fetch, source validation, deduplication and publication.
report = collect_ncr(root, window=UtcInterval(start, end))
print(report.collection_id, report.status, report.rain_label_counts)

# Existing FastAPI service: local reads only; no upstream network in HTTP handlers.
@app.get('/api/ncr/status')
def ncr_status():
    return inspect_ncr(root).as_public_dict()

# Existing worker owns inference, not the API process.
proposal = prepare_ncr(root, issued_at=issue, horizon_minutes=30)
if isinstance(proposal, ReadyInputs):
    ticket = proposal.ticket(model_version=accepted_model.version)
    queue.submit(ticket, now=issue)
else:
    record_abstention(proposal)  # unavailable/late imagery or targets stays explicit
```

## Problem and grounding

`data_catalog.py` exposes manifest-backed fixed samples. `collect_india_data.py` currently targets Bihar snapshots, not an NCR refresh. `train_images.load_episode` already checks units, masks, equally spaced UTC slots, source availability, binary target coverage and 30-minute target ends. Its corpus splitter separates event groups and purges overlapping windows. `forecast_updates.LatestForecastQueue` provides bounded scheduling metadata, but not persistence. Preserve these boundaries; do not add network IO to `/api/runs` or call a synthetic run an NCR forecast.

## Shape

Public domain types use immutable values and explicit missingness. Constructors validate UTC, finite units, intervals and bounds once at the provider/storage boundary, per boundary-discipline.

```python
@dataclass(frozen=True)
class UtcInterval:
    start: datetime
    end: datetime             # end > start; both UTC

@dataclass(frozen=True)
class MeasuredRain:
    station_id: str
    point: tuple[float, float]  # longitude, latitude; not a cell-wide claim
    interval: UtcInterval
    amount_mm: float          # valid >= 0 measurement, not a fill value
    trace: bool
    source_sha256: str

@dataclass(frozen=True)
class UnknownRain:
    station_id: str
    observed_at: datetime
    reason: str               # missing interval/unit/value or failed quality
    source_sha256: str

RainEvidence = MeasuredRain | UnknownRain

@dataclass(frozen=True)
class SourceResult:
    source_id: str
    state: Literal['collected', 'empty', 'unavailable', 'access_required']
    record_ids: tuple[str, ...]
    attempted_at: datetime
    latest_observed_at: datetime | None
    message: str              # scrub credentials and bounded provider errors

@dataclass(frozen=True)
class CollectionReport:
    collection_id: str
    status: Literal['complete', 'partial', 'unavailable']
    sources: tuple[SourceResult, ...]
    rain_label_counts: dict[str, int]  # interval-qualified wet/dry/unknown

@dataclass(frozen=True)
class BlockedInputs:
    issued_at: datetime
    blockers: tuple[str, ...]

@dataclass(frozen=True)
class ReadyInputs:
    issued_at: datetime
    input_manifest_sha256: str
    episode_path: Path
    def ticket(self, *, model_version: str) -> ForecastTicket:
        raise NotImplementedError

def collect_ncr(root: Path, *, window: UtcInterval) -> CollectionReport:
    raise NotImplementedError
def inspect_ncr(root: Path) -> CollectionReport:
    raise NotImplementedError
def prepare_ncr(root: Path, *, issued_at: datetime,
                horizon_minutes: Literal[30]) -> ReadyInputs | BlockedInputs:
    raise NotImplementedError
```

The collection surface hides bounded retries, provider schemas, missing-value decoding, interval reconstruction, request provenance and atomic publication. Caller-visible state remains source availability and measurement meaning. An NCR bounding rectangle is a collection filter, not the official administrative boundary or a guaranteed forecast resolution.

## Storage, ownership and data flow

- `data/ncr/raw/<sha256>.<ext>` stores immutable bytes. An atomic temporary-file replacement publishes only a verified complete payload; identical bytes converge on the same name.
- `data/ncr/runs/<run-id>/manifest.json` stores one actor's immutable request/results, timestamps, units, hashes and source restrictions. Each actor writes only its own directory. Do not maintain a shared mutable `latest.json`; readers merge completed manifests by source observation time, then retrieval time.
- `data/ncr/records/<source>/<record-id>/<payload-hash>.json` preserves provider corrections. Logical IDs derive from provider/station/variable/observation interval. Divergent revisions coexist; read-time selection retains the history.
- A run manifest records failed/empty attempts too. A previous valid snapshot can remain readable with explicit age while the newest attempt is unavailable. Stale data cannot silently become current.
- Wet means a quality-valid positive accumulation (or explicit trace); dry means a quality-valid measured zero over a known interval; all other cases remain unknown. Six-hour rainfall cannot be divided into twelve invented 30-minute labels. Surface rain never supplies lightning labels.
- Training alignment uses acquisition time and recorded availability separately. Historical downloads without issue-time readiness remain research-latency assumptions. Forecast-valid time is never substituted for observation time.
- New arrivals produce a new immutable input manifest and forecast issue/revision. Forecasts are never overwritten after observation, preserving honest verification. The existing queue suppresses superseded work; its accepted completion is persisted separately before any latest-read selection.

## Module map

| Module | Responsibility and rationale |
|---|---|
| `nowcast/ncr_data.py` | Own source adapters, domain parsing, immutable persistence and status; one deep interface avoids provider knowledge leaking to CLI/API. |
| `scripts/collect_ncr_data.py` | Parse bounded CLI dates and invoke collection; may later run as an existing durable operation recipe. |
| `scripts/ncr_model.py` | Build a provenance-bearing aligned episode or return blockers; reuse existing episode validator and training CLI instead of a second trainer. |
| `nowcast/service.py` | Add read-only `/api/ncr/status` and bounded local observation listing; expose neither credentials nor arbitrary filesystem paths. |
| Existing training and queue modules | Preserve calibration/event split checks and bounded update scheduling; add compatibility-checked checkpoint initialization only when a usable checkpoint exists. |

## Model reuse and tradeoffs

Reuse the existing compact ConvLSTM and dense optical-flow baseline first. A fine-tune option must check channel ordering, normalization, grid, target definition and horizon against checkpoint metadata; partial undocumented tensor loading is disallowed. No pretrained NCR checkpoint is assumed. Compatible upstream weights can initialize the model only after license and input compatibility are verified. A Google architecture can inspire recurrent forecast updates and probabilistic outputs without implying Google weights or accuracy are available.

We accept filesystem manifest scans in exchange for inspectable, portable samples and no migration burden. Bound response sizes and collection periods now; introduce an index only when measurements justify it. We accept explicit abstention in exchange for avoiding false claims of 30-minute skill from coarse station-only inputs. The eventual matched image corpus remains the bottleneck, not GPU scheduling.

## Alternative and red-flag review

A normalized SQLite ingestion registry would provide faster indexed regional queries, but couples provider parsing, migrations, shared writers and publication before the small pilot proves useful. This candidate keeps durable job ownership in the existing operations store while source artifacts remain separately inspectable. Red-flag review: no public wire schema, no load/validate/save pass-through module chain, no second trainer, no mutable shared manifest, and no dependency on forecast agreement when defining observations.

## Synthesis decision, open risks and next step

Synthesis is pending. Which exact IMD fields provide valid accumulation intervals, and which NCR satellite/radar/lightning products can actually be retrieved under present access? Resolve through the parallel source probes; adapters must fail explicitly until those facts are known. First implement the NCR collector and evidence inventory, then verify duplicate runs, interrupted writes and unknown precipitation handling before enabling a model path.

# Candidate A: regional modular worker

## Problem

A small team needs reproducible causal weather experiments, reliable data ingestion, and a future shared officer/public service. Data access is currently more constraining than serving traffic. The current on-demand simulator and radar replay must remain usable while raw government data are collected separately.

## Usage (proposed caller contract)

```python
artifact = archive.ingest(provider.fetch(request))
issue = regional.issue(region_id, issued_at, bundle_id, mode="shadow")
forecast = forecast_store.get(issue.forecast_id)
decision = review.record(forecast.id, site_id, actor, policy_version)
```

These are design sketches, not imports available in today's repository. A scheduler creates one job per regional issue. A browser fetches its completed immutable forecast instead of repeating GPU inference.

## Shape

One Python package owns four deep domains: observations/archive, forecasting, verification/training, and review. FastAPI is the transport boundary. A background process handles provider acquisition and issue jobs. PostgreSQL stores manifests, job leases, issued records and review history; filesystem or S3-compatible object storage contains immutable source files and scientific arrays. Browser clients cannot read labels, raw restricted files or model credentials.

```python
class ArtifactRef:  # frozen
    sha256: str
    provider_product_version: str
    observed_interval: TimeInterval
    retrieved_at: UTCInstant
    provider_available_at: UTCInstant | None
    geometry: GeometryRef
    units: UnitMap
    terms: TermsRef

class IssueManifest:  # frozen; complete causal input selection
    id: str
    forecast_origin: UTCInstant
    issued_at: UTCInstant
    cutoff: UTCInstant
    inputs: tuple[ArtifactRef, ...]
    snapshot_hash: str
    bundle_id: str
    replay_mode: ReplayMode

class ForecastBundle:
    weights_hash: str
    preprocessing_version: str
    target: TargetContract
    calibration_id: str
    supported_source_patterns: tuple[SourcePattern, ...]

def ingest(payload: ProviderPayload) -> ArtifactRef: ...
def issue(region: RegionId, issued_at: UTCInstant, bundle: BundleId, mode: ReplayMode) -> IssueResult: ...
def verify(forecast: ForecastRef, labels: LabelSetRef) -> VerificationReport: ...
```

The observation domain hides format, units, QC, grids and access terms. The forecasting domain hides causal selection, baseline/model selection, calibration and packaging. The review domain owns authority, expiry, actor identity and official bulletin relationships. Verification owns future labels and grouped splits. Types are pseudocode; immutable records, database constraints and boundary validation enforce invariants in the eventual implementation.

Data structures: a content-addressed raw object keyed by SHA-256 can serve many provider receipts; a receipt preserves URL and time. A unique issue job key includes region, nominal origin, input manifest, target and bundle. A lease prevents duplicate workers committing different outputs for the same key. A unique forecast ID and transactional outbox make crashes after committing but before sending recoverable. Expired leases permit retry; a poison job goes to a failed state with its reason. Keep at-least-once delivery and receiver deduplication explicit.

Only observations whose acquisition ends and actual local readiness precede the cutoff qualify. Future NWP valid times are allowed for forecasts from a run already available at cutoff; reanalysis is a separate retrospective experiment. Unknown historic readiness means idealised replay, not operational replay. An issue is sealed before inference; late inputs create a separately identified revision. Future labels live behind training/evaluation access, never in the inference input query.

Storage indexes: observations by provider/product/time + footprint; forecast by region, origin, status + target; jobs by pending state and lease expiry; decisions by forecast/site/actor/time. Large arrays never go in PostgreSQL JSON. PostGIS is useful for site/area intersection, not as an array engine. Model bundles pin channel normalization, source patterns, target and calibration together.

## Deployment and sizing

Begin with an API process, a worker process, PostgreSQL and object storage on one institution-managed host. A separate training machine writes versioned bundles. Isolate the public read API from officer write roles. Add replica APIs or a dedicated GPU worker when measurements require it. No Kafka or Kubernetes is needed to validate a single regional pilot. Containers on a Linux pilot host avoid Windows scientific-decoder packaging constraints.

Use 128x128 central cells at 2 km and a 32-cell halo each side: 192x192 input. Six 10-minute history slots with masks and actual ages; do not synthesize missing INSAT scans. Begin with one 30-minute/8-km target. A 64-km halo provides context, not a guarantee of capturing every fast-moving storm. Flag insufficient upstream context and profile alternative halos at 60 minutes.

## Rationale and tradeoffs

- Accept a regional worker as a possible bottleneck for a much smaller operational surface and an auditable transaction boundary.
- Accept manual bundle promotion for controlled comparisons and quick rollback.
- Keep provider adapters inside the observations domain; adding a provider must not change browser or review logic.
- Use one PostgreSQL job table rather than multiple coordination services; add independent consumers only after source lag or resource isolation measurements justify them.
- Retain draft/issued/cancelled/expired states separately from hazard probability. Missing data never silently reduces probability toward zero.

## Alternatives considered

An event-stream architecture enables independent feed scaling, but exposes message schema evolution, ordered event-time processing and distributed completion to the operator. A request-triggered pipeline is easiest to write but repeats expensive work per user and gives inconsistent snapshots. Browser-only inference cannot repair absent sensors or deliver current information offline.

## Open risks

Which Indian products can be legally archived and used at near-real-time cadence? Which source patterns have enough test cases for calibrated use? These are partner/data gates, not reasons to delay the requested architecture or public starter-pack collection.

## Next implementation step

Build immutable acquisition manifests and inspect a bounded official data starter pack; then implement one causal provider adapter with executable unit/time/coverage contracts.

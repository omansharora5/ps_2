# Candidate B: immutable research requests with reconciliation

Design candidate, 30 September 2026. This file proposes interfaces; it does not claim that they are implemented.

## Problem

The current service persists forecast runs and decision receipts but loses collection jobs on restart. Its optional image trainer already owns causal masking, event separation, calibration and frozen evaluation. Connecting these capabilities should preserve those scientific contracts and give the website and app one understandable view of work. The proposed owner is a filesystem research store: immutable requests express desired results, one reconciler produces them, and read projections explain the difference. There is no mutable transactional queue or broker.

## Usage (caller's view)

```python
# Service: registered IDs only; no client-provided paths or commands.
operation = research.request(TrainExperiment(dataset_id, recipe_id))
return operation.to_public_record()  # Repeating the request returns the same identity.

# A separate worker process: only one may own this local store.
research.reconcile_once(now=utc_now())  # Checks inputs, runs one bounded task, commits evidence.

# Both clients: refresh freely, preserve the last response when offline.
GET /api/research/operations?limit=20
GET /api/research/operations/{operation_id}
```

The officer selects a registered dataset and a named experiment, sees its scope and readiness, starts it, and receives a durable operation link. The mobile operator screen monitors the same record; its presentation-only role switch confers no ability to start privileged work. Current `/api/runs`, `/api/receipts`, image and collection routes remain compatible. Collection POSTs delegate to the store and project their existing response shape.

An operation record contains `id`, `kind`, `status`, `stage`, `scope`, dataset and recipe identities, attempt count, created/started/finished timestamps, structured blocking reasons, bounded metrics, result links and `public_dispatch_eligible: false`. States are `queued`, `running`, `succeeded`, `failed`, or `blocked`; completed research is not a validated model. A clock stamp is never used as the scientific identity. API parsing and local loopback/Origin/JSON restrictions stay at the service boundary; remote training is disabled until real authentication exists.

## Shape

```python
@dataclass(frozen=True)
class FrozenDataset:
    id: Sha256
    files: tuple[VerifiedObject, ...]  # Hash, size, original filename; registered local objects.
    event_plan: EventSplitPlan        # Train/validation/calibration/test IDs and purge boundary.
    scope: DataScope                  # Synthetic, French radar, or independently admitted observations.
    target: TargetDefinition
    maturity: CoverageEvidence        # Target end, label availability, declared coverage and provenance.

OperationSpec = CollectSnapshot | VerifyStarterData | ReplayRadar | TrainExperiment

class ResearchStore:
    def request(self, spec: OperationSpec) -> OperationView:
        raise NotImplementedError  # Hash normalized spec + input/recipe identities; publish desired manifest.
    def operation(self, id: OperationId) -> OperationView:
        raise NotImplementedError  # Derive state from complete manifests and the worker lease.
    def recent(self, limit: int = 20) -> tuple[OperationView, ...]:
        raise NotImplementedError
    def reconcile_once(self, *, now: UtcInstant) -> ReconcileOutcome:
        raise NotImplementedError  # Own exclusive process lock; repair incomplete attempts; execute one task.
```

`nowcast/research_store.py` owns identities, admission, immutable manifests, attempts, reconciliation and public projections. `nowcast/research_recipes.py` owns the finite set of executable scientific recipes and their artifact validators; it directly calls `train_images.train/evaluate`, `image_processing.image_run`, and registered collectors. These are two deep modules, not one service per pipeline stage. The existing training module retains all split and model rules. Per boundary-discipline, HTTP models do not enter this domain surface.

Store layout is `datasets/<digest>.json`, `requests/<digest>.json`, `attempts/<operation>/<uuid>/`, and `results/<operation>.json`. The operation digest includes recipe/source version, dataset digest, model/configuration and fixed seed. The dataset digest includes filenames, byte hashes, event assignments, scientific metadata and maturity evidence. No changes to published manifests are permitted. Bounded lists can scan a configured maximum of retained manifests initially; an optional disposable index may accelerate reads without becoming a second source of truth. Admission limits prevent unbounded files, decoded arrays, requests and retries.

Requests are written to a unique temporary file, flushed, closed and atomically renamed on the same filesystem. Concurrent identical request writers publish identical bytes under the same hash. The single worker holds an OS file lock for its whole lifetime, not a timestamp lease that can expire while inference continues. Model work runs synchronously in that worker, so an unexpected worker exit cannot leave an independent trainer publishing results. API processes only create immutable request manifests. Collectors requiring subprocesses need explicitly owned child lifetime and termination before recovery; until that is implemented, collection recovery becomes a visible interrupted result requiring retry rather than launching a potentially overlapping collector.

Attempts always have fresh directories because `train_images` rejects an existing checkpoint. A result becomes visible only when all required files exist, their hashes pass, and one complete result manifest is atomically published. An interruption before publication leaves no successful result. Startup adopts a fully verified completed result, marks an incomplete attempt interrupted and may create one bounded replacement attempt. Deterministic input failures remain failed or blocked. An explicit retry uses an immutable request keyed by operation, failed-attempt digest and client retry token; repeating the retry cannot produce another attempt. This follows make-operations-idempotent while acknowledging that computation can run twice even though there is one logical result.

## Scientific execution and recurring learning

Starter-data verification must check actual SHA-256 bytes through registered manifests, not the catalogue's current size-only display. Verification produces provenance evidence; it never marks unmatched Indian/US/archive samples as a training corpus. Radar replay uses the pinned French sample and emits its existing metrics/scope. Both therefore deliver useful real operations before new Indian observations arrive.

A training request verifies the frozen corpus, executes the existing compact ConvLSTM in a new attempt folder, retains checkpoint/calibrator/split hashes, and independently invokes frozen `evaluate`. Calibration and the climatology baseline are retained even when they worsen results. The worker holds one model at a time and enforces recipe-specific episode/file/decoded-memory budgets. It must not promise bounded memory merely because the queue is bounded: `corpus()` currently loads all episodes and `examples()` materializes windows.

Recurring learning is reconciliation of **new eligible dataset versions**, not a daily clock causing another fit. A local registered-corpus policy admits only whole genuinely new events whose future targets and label-availability times have matured, whose provenance and coverage pass, and whose identity has not already been consumed. It writes a deterministic training request and records a blocked reason when requirements are missing. No API accepts arbitrary uploaded paths or shell text.

One necessary trainer extension is explicit frozen event rosters. Its current `corpus()` chronologically repartitions whenever the corpus grows; repeating that default would move former evaluation events into training. Add an optional validated split-plan argument while preserving the existing CLI default. For each learning cycle, keep protected evaluation events outside fitting and use genuinely new, predeclared evaluation cohorts when making a new performance claim. Repeatedly inspecting a final test makes it development evidence; the report must say so. Synthetic smoke execution remains a separate recipe and is never eligible as new observational learning. Candidate models stay in a registry for review; there is no automatic active-model pointer change or public alert promotion.

## Tradeoffs accepted

- We accept one local worker and bounded directory scans in exchange for inspectable immutable evidence, no new infrastructure and straightforward recovery.
- We accept interrupted computation restarting in a fresh directory in exchange for preserving the trainer's existing artifact rules.
- We accept an explicit split-plan extension in exchange for preventing daily learning from quietly contaminating evaluation.
- We accept process-crash recovery, not an untested power-loss durability promise; atomic rename and filesystem flush behavior must be tested on the actual Windows volume.

## Alternatives considered

A SQLite transactional queue hides stronger claims, leases and indexing behind compact operations but introduces mutable lifecycle state separate from artifact publication. It is preferable if concurrent workers, retention queries or distributed scheduling become necessary. A generic ingest/validate/train/evaluate/publish service pipeline was rejected because callers would coordinate scientific invariants and partial failures across too many shallow interfaces.

## Synthesis decision

Pending orchestrator comparison. This candidate's distinctive choice is immutable desired-state manifests with one reconciliation owner, rather than database-owned transitions.

## Open questions and risks

Can collection child lifetime be guaranteed on both Windows and Linux before automatic recovery is enabled? Until proven, surface interrupted collection work. Can the admitted dataset fit the declared decoded-memory budget with the current materialized trainer? Reject before execution when it cannot. Does the eventual observed corpus include trustworthy availability and coverage records? Until it does, recurring observational learning remains visibly blocked.

## Next implementation step

Build request identity, attempt isolation and result publication with injected process interruption tests; then connect registered integrity verification and actual radar replay before connecting bounded ConvLSTM training.

Red-flag screen: no transport types in domain contracts; no stage-by-stage services; no caller coordination of checkpoint paths; one owner per manifest family; status is derived rather than synchronized with another authoritative store.

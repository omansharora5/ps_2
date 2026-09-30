# Candidate A: durable research operations with a separate worker

Candidate design, 30 September 2026. Phase: Ground complete; Sketch complete; synthesis and implementation belong to the orchestrator.

## Problem

The current API already persists immutable forecasts and decisions in SQLite, but collection jobs live in `data_catalog.JOBS` and disappear on restart. `train_images.py` performs real compact ConvLSTM fitting, calibration and frozen evaluation, yet only as a CLI; its fresh-output requirement makes naive retries unsafe. The new boundary should hide job recovery, input identity and publication from both clients while retaining existing endpoints, honest synthetic/observed scope and local-only mutation controls.

## Usage (caller's view)

An operator opens the operations page, sees registered datasets with integrity and readiness reasons, selects a fixed recipe, and receives one durable job. Retrying after a lost response returns that same job. Phone users can inspect the same progress and scientific limitations without gaining training permissions through the presentation-only role switch.

```python
# Service: parse and authorize at the existing HTTP boundary.
job = operations.submit(StarterAudit(collection="india"))
job = operations.submit(ObservedReplay(method="dense_optical_flow", horizon=10))
job = operations.submit(TrainCandidate(dataset_id="frozen-sha256", recipe="convlstm-calibrated-v1"))
# Same command + frozen inputs + recipe/code identity -> same job, even after success.

# Separate local worker: the caller never chooses a command, executable or path.
operations.work_once(worker_id=worker_id, now=utc_now())

# Both clients read a stable projection; internal leases and local paths stay private.
view = operations.get(job.id)
```

Add `GET /api/operations`, `GET /api/operations/{id}`, `GET /api/operations/datasets`, and local-only `POST /api/operations`. A bounded `POST /api/operations/{id}/retry` requeues a failed logical job, never creates a duplicate result. All mutation uses the existing opt-in, loopback, Host, JSON and Origin checks. The mobile build is read-only for this boundary. Existing forecast, decision and collection response contracts remain intact; collection can adopt the ledger behind its current interface after its fixed scripts support isolated output.

The client projection contains `id`, `operation`, `state`, `attempt`, timestamps, named stage, `scope`, `dataset_id`, recipe/code identity, `summary`, typed `error_code`, safe error text, and bounded `artifacts` with server-generated download IDs. Stages are named facts, not invented percentage estimates. A successful execution may have `validation_status="research_only"` and `candidate_recommendation="retain_baseline"`; a green job never implies a scientifically better model. Both clients show stale/unreachable status and retain the last fetched timestamp.

## Shape

```python
Command = StarterAudit | ObservedReplay | TrainCandidate
State = Literal["queued", "running", "succeeded", "failed"]

@dataclass(frozen=True)
class FrozenDataset:
    id: str                    # canonical manifest digest, not a caller path
    file_hashes: tuple[FileDigest, ...]
    event_ids: tuple[str, ...]
    scope: Literal["synthetic_smoke_only", "observed_research"]
    target: str
    readiness: Ready | Blocked # typed reasons; coverage and maturity included

@dataclass(frozen=True)
class Lease:
    job_id: str
    attempt: int
    token: str                 # fencing token changes on every claim
    expires_at: datetime

class Operations:
    def submit(self, command: Command) -> JobView: raise NotImplementedError
    def get(self, job_id: str) -> JobView: raise NotImplementedError
    def list(self, limit: int = 30) -> list[JobView]: raise NotImplementedError
    def retry(self, job_id: str) -> JobView: raise NotImplementedError
    def work_once(self, worker_id: str, now: datetime) -> bool: raise NotImplementedError
    def learning_tick(self, now: datetime) -> LearningView: raise NotImplementedError
```

Keep the runtime trace within three files: `service.py` owns transport and authority; `operations.py` owns command identity, SQLite transitions, dataset registration/readiness and publication; `operation_recipes.py` owns the fixed scientific executions. `scripts/run_operations.py` is only the worker entry point. Avoid separate load/validate/save services and repositories that merely pass the same payload through.

SQLite holds `jobs`, append-only `attempts`, immutable `datasets`, and one learning-policy watermark. Unique `jobs.command_sha256` implements submit convergence. Its hash covers canonical command parameters, frozen input manifest, recipe version and relevant implementation digest; it excludes wall time, UI session and retry count. `BEGIN IMMEDIATE` atomically claims one eligible job and increments its attempt/token. Short transactions cover metadata only; no database lock remains held during hashing, network work or Torch execution. Index state/created time for claiming and updated time for bounded client lists.

Each attempt writes exclusively to `data/operations/attempts/{job_id}/{attempt-token}/`. The existing trainer therefore always sees a fresh output directory. After successful computation, verify expected files, JSON schema, dataset/checkpoint/report hashes and finite metrics, then commit artifact references and success only with `WHERE state='running' AND token=? AND lease_expires_at>now`. A stale worker may leave its own unreferenced directory, but cannot overwrite a newer attempt or publish its result. Artifact downloads use registered IDs, root containment and integrity checks; never expose arbitrary path downloads. This concentrates retry and publication policy behind one deep interface, per boundary-discipline and make-operations-idempotent.

## Dataset and learning contract

Starter auditing checks every registered manifest file's size and SHA-256 and reports individual failures. Historical Indian station/context files, US samples and the French radar sequence remain separate datasets; a passing audit does not make them training episodes. Observed replay calls the existing `image_processing.image_run` and preserves its measured scope and benchmark comparison.

Training registration is a local administrative action over a fixed configured directory, not an API path/upload parameter. Copy validated episodes into an immutable digest directory, verify the completed copy before registration, and recheck it before execution. Reuse `load_episode`, `corpus`, causal masks, split validation and normalization rather than duplicate their rules. Store dataset and split identities alongside the trainer's checkpoint, calibration and evaluation hashes. Invoke the actual calibrated ConvLSTM CLI using a fixed executable/argument array with `shell=False`; perform frozen `evaluate` afterward. Generate a clearly named eight-event synthetic fixture only for the demonstration recipe. Missing Torch yields a visible setup failure, never fabricated training output.

The scheduled learning tick first verifies a registry sidecar that records label availability, target-window completion, source provenance and coverage. Existing `target_end_utc` alone does not prove truth was actually received. Require new independent event identities and covered mature labels beyond the prior successful training watermark, adequate examples and compatible channels/grid/target. No new eligible data means `waiting_for_new_labels`, not another training run. A fingerprint of policy version plus eligible frozen dataset makes repeated daily ticks idempotent. Advance the training watermark only after successful candidate publication; failed attempts do not consume data.

The current CLI re-partitions a corpus chronologically. Its repeat-run test scores must be described as development evaluation; they cannot become an indefinitely reused final benchmark. Reserve an untouched operational qualification corpus outside daily candidate selection, and require an explicit future promotion workflow. This iteration never updates the application's model pointer, never claims self-improvement from synthetic fixtures, and never activates public dispatch.

## Retry and crash analysis

| Failure | Required outcome |
| --- | --- |
| POST response lost / repeated submit | Unique command digest returns the original job |
| Two workers claim together | SQLite transaction gives one a lease; other returns idle |
| Worker dies during training | Lease expires; bounded retry gets a new private attempt directory |
| Old worker finishes after reassignment | Token check rejects publication; its files stay unreferenced |
| Crash after files but before success commit | Retry starts fresh; it does not assume partial files are valid |
| Crash after success commit | GET and repeated submit recover the same result and artifact IDs |
| Input bytes change after registration | Fail integrity validation before computation/publication |
| Daily scheduler runs twice | Dataset/policy fingerprint yields one candidate job |

Lease fencing protects publication, not physical CPU limits: a dead parent can leave a child process alive. The worker therefore owns and heartbeats its subprocess, enforces wall-time/output limits, and uses an OS-managed child-process lifetime (Windows Job Object with kill-on-close, process group on POSIX) before automatic recovery is advertised as bounding compute. Start with one worker and one heavy task at a time; do not launch per-user models. Job history persists; retention can remove only unreferenced expired attempt directories after resolved-root checks.

## Synthesis decision

Awaiting comparison with candidate B. This candidate's distinguishing choice is a separate durable command ledger and worker, with publication fenced by attempt identity and all scientific execution confined to a fixed registry.

## Tradeoffs accepted

- We accept one-host SQLite throughput in exchange for minimal dependencies and inspectable recovery; a broker is unnecessary for this research deployment.
- We accept occasional recomputation after a crash in exchange for no inference that incomplete training output is reusable.
- We accept read-only remote/mobile operation status in exchange for preserving the existing lack of operator authentication.

## Alternatives considered

An in-process executor plus persisted status is shallower: callers still inherit API restart and worker-lifetime behavior, and unsafe retries remain outside the abstraction. A broker/actor platform hides distributed scheduling but exposes deployment, duplicate delivery and artifact-store coordination before those capabilities are needed. Both lose to a bounded local worker for the current workstation deployment.

## Open questions and risks

Which Indian provider will supply recorded event-level truth availability and coverage? Until that external contract exists, readiness remains blocked. Can a future multi-host deployment provide authenticated operators and shared artifact storage? Until then, writes remain local. These are future qualification constraints, not approval checkpoints for implementing the executable research workflow.

## Next implementation step

Implement the SQLite command/attempt transitions and crash-convergence tests first, then connect one real starter audit and one calibrated synthetic ConvLSTM run before exposing the same result projection to web and mobile.

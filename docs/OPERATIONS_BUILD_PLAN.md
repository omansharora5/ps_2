# Connected backend, research API and client delivery

Active iteration, 30 September 2026.

- [x] Ground: trace forecast, collection, training, persistence and both clients.
- [x] Sketch: compare two independent architectures and choose the public contracts.
- [x] Agree: proceed under the requested build authorization, with no approval checkpoint.
- [x] Implement: connect durable operations, evaluation/training evidence, API and clients.
- [x] Verify: exercise retries, restart recovery, actual computation and user flows.
- [x] Scrap review: implementation retained the selected boundaries; no repeated structural workaround required a redesign.

The product remains decision support. This iteration must make the research workflow executable and inspectable while retaining explicit data scope. A scheduled training run cannot establish Indian lightning reliability or authorize public warnings.

## Grounded runtime and ownership

`POST /api/runs` in `nowcast/service.py` validates `RunRequest`, calls the synthetic model or observed radar replay, hashes the request/model/code/provenance and persists one immutable result in `data/receipts.sqlite`. `POST /api/receipts` loads that result, calls the pure evidence policy and persists a separate decision identity. These synchronous research endpoints do not own a provider stream, neural trainer or scheduler.

`GET /api/data/catalog` reads manifests through `nowcast/data_catalog.py`; file downloads verify hashes. The opt-in collection POST checks loopback, Host, JSON and Origin before calling a fixed collector. The current `ThreadPoolExecutor` and `JOBS` dictionary lose job history on restart and only deduplicate active work. This is the concrete persistence gap to address without breaking collection and simulation callers.

`scripts/train_images.py` owns episode loading, causal inputs, group/time split validation, ConvLSTM fitting, optional held-out calibration and frozen evaluation. `train` writes a checkpoint using a temporary file and records report/split hashes. A repeated run into the same directory is rejected. `make_smoke` similarly requires a fresh directory. A workflow must therefore own immutable dataset identities and isolated attempt directories, not retry these commands into partially written folders. Existing generated smoke data can establish that the training workflow runs; it cannot be labelled Indian observations.

The website calls JSON endpoints through `src/service-client.js` and routes through `src/portal.jsx`. The existing workbench separately protects against late receipt responses. `mobile/src/app/operator.tsx` uses `requestApi` and explicit parsers from `mobile/src/lib/api.ts`; it currently reads the catalogue and starts a fixed simulation. Its role switch is presentation state, so a mobile research monitor must not acquire remote privileged training permissions through that switch.

## Historical constraints and evidence coverage

Git commits `d14846b` and `85ffcc1`, README and `docs/CONTINUOUS_FORECAST_DESIGN.md` explicitly separate the optional image trainer from app forecasts and restrict collection to local registered commands. Preserve those scientific and command-execution boundaries. Change the persistence/recovery boundary so a restarted worker can recover unfinished research work. Do not turn the previous in-memory queue into a claim of durable or distributed execution.

The source-history and long-form evidence are local Git and repository documents. Tool discovery found no connected project issue tracker, team chat, observability, exception tracker or analytics warehouse. No production incident or customer history is inferred from those unavailable categories.

## Design comparison process

Arena phases: frame, fan out, cross-judge, pick, graft, verify. Two candidates will consider the same traced system, with separate output files. Score 1–5 for: retry/restart convergence; causal dataset and result identity; one bounded worker without per-user model loads; small API usable by both clients; reuse of the current training/data contracts. The final design will record rejected alternatives and actual validation results.

## Synthesis decision

Both candidates were read in full and screened for shallow modules, leaked storage decisions, stage-only services and pass-through methods. The independent cross-judge recommended A's SQLite ledger and small client API, combined with B's immutable artifacts and one process owning the worker. The parent agrees. Criterion scores A/B were 4/4, 4/5, 3/5, 5/4, 5/4. A's subprocess lease recovery was its weakness; adopt B's OS lifetime lock and execute scientific recipes in the worker process itself. A crash releases that lock without leaving an independent trainer running. Attempt tokens still prevent cancelled/interrupted work from publishing.

Reject a filesystem-only status store because SQLite already supplies atomic metadata and indexed bounded lists. Reject broker infrastructure for this workstation build. Keep the existing in-memory provider collectors explicitly separate: they have shared output directories and subprocess ownership that this change does not magically make durable. The new starter audit verifies their actual files and links back to the collection API.

No new public approval checkpoint is needed. The user has requested implementation. Operational Indian validation, authentication and public dispatch remain separate requirements.

## Selected caller contract

```python
dataset = freeze_dataset(source_directory, store_root, name=name, series=series,
                         labels_available_at=received_at, coverage_evidence=record)
store.register_dataset(dataset)
job = store.enqueue(kind, identity, parameters, scope)
# Same input identity + recipe/code returns the same logical job after restart.
with WorkerLock(store_root):
    store.recover_interrupted()
    job = store.claim()
    result = execute_recipe(job, attempt_directory, store)
    store.finish(job['id'], job['attempt_token'], result)
```

`nowcast/operation_store.py` owns SQLite datasets, jobs, attempts, protected event roles and learning policy. `nowcast/operation_recipes.py` owns immutable input preparation, scientific admission budgets, fixed actual recipes and result artifacts. `nowcast/operations_api.py` owns HTTP parsing and local write checks. `scripts/run_operations.py` owns the OS worker lock, CLI and execution loop. Both clients consume the same public projection. These modules group policy ownership; they do not create one service per temporal stage.

The worker has one OS file lock for its entire lifetime. It runs one recipe synchronously. An interrupted running row becomes retryable only after a new process acquires that lock. No elapsed timestamp starts a second trainer. Each claim gets a new token and fresh attempt directory; results become visible only after integrity checks and a fenced SQLite success transaction. Cancelled work cannot publish, although a currently executing in-process numerical call may finish before the worker returns idle. Retries include the expected terminal attempt number, so a delayed duplicate cannot retry a later failure.

The dataset registry keeps the original bytes, metadata, split rosters, maturity declaration and coverage evidence. Admission bounds compressed bytes, decoded arrays and materialized training windows before fitting. Once an event is assigned to validation/calibration/test in a learning series, later fitting cannot reuse it as training. Reject incompatible new versions rather than silently repartitioning protected events. This does not make repeatedly inspected development scores an untouched final qualification benchmark.

Daily learning reconciles accepted observed dataset versions with prior jobs. It starts at most one candidate for a new eligible dataset/recipe identity, records waiting/blocked reasons, and never retrains the unchanged corpus just because a day elapsed. Synthetic fixtures exercise the workflow explicitly and are excluded from automatic observed-data learning. No model pointer or warning permission changes automatically.

### HTTP contract shared by website and native app

- `GET /api/operations/state`: schema version 1, write availability, worker status, recent jobs, registered datasets, learning state, recipes and linked research.
- `POST /api/operations/jobs`: `{kind: starter_audit | radar_replay | train_candidate, dataset_id?: string}`. Fixed recipes only. Returns the durable job.
- `POST /api/operations/jobs/{id}/retry`: `{expected_attempt: number}`. Bounded, terminal-attempt-conditional retry.
- `POST /api/operations/jobs/{id}/cancel`: `{}`. Idempotent cancellation; no forced kill of another process.
- `POST /api/operations/learning`: `{enabled: boolean}`. Local opt-in for daily reconciliation.
- `GET /api/operations/jobs/{id}` and `/api/operations/jobs/{id}/artifacts/{artifact_id}`: durable detail and verified registered files.

Jobs expose `id`, `kind`, `status`, `stage`, `scope`, `dataset_id`, `attempt`, timestamps, error, summary and artifacts. `succeeded` describes execution. Model quality and baseline comparison remain separate summary fields. GET responses never expose arbitrary local paths. Mutations require explicit server opt-in, direct loopback, local Host, JSON and trusted Origin; the mobile operator view monitors these records without granting remote mutation rights.

## UI intent

An officer or researcher needs to see the next useful action, whether work is waiting for a worker, which data it used and whether the result beat a baseline. Use the existing slate/teal design, a visible data-to-evaluation flow, one clear dataset/recipe form, named job stages, readable limitations and a result comparison. Avoid fabricated progress percentages. Domain terms are observation coverage, event split, forecast issue, calibration, preparation time and source age. Color follows the existing console: slate text, paper background, teal actions, amber missing evidence and red failures.

The interface-design and ui-ux-pro-max guidance is applied within the existing `design-system/vajra/MASTER.md`. The generic portfolio-grid suggestion was rejected as unrelated. The targeted feedback guidance fits: visible pending/success/error states, stable action labels and preserved context when a refresh fails. Visual verification will cover desktop and phone widths, keyboard access, offline/error states and actual backend results.

## Delivered and checked

The selected modules and both clients are implemented. A real local API/worker run verified 18 source files, executed the observed +10-minute radar experiment and trained/calibrated/re-evaluated the compact ConvLSTM. Repeated requests returned the same completed jobs; downloaded artifacts matched their recorded hashes. The synthetic candidate retained the stronger climatology baseline. Generated examples were excluded from daily admission.

Independent implementation review found and corrected cancelled attempt-zero retries, attempt-directory failure handling, an artifact read/reopen race, scheduler backpressure, per-series failure isolation and selected jobs falling outside the recent history list. These fit the selected ownership boundaries. The final regular suite discovered 115 tests: 113 passed and two optional Torch checks skipped; the real training integration ran separately in `.venv-ml`. The website's 12-journey full run passed; the final operations-only three-test run also passed after adding the older-job regression. Native source checks and all-platform exports passed. See [verification scope](../VALIDATION.md) and [the runnable guide](OPERATIONS_GUIDE.md).

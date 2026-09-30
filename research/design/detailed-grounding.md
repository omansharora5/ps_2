# Detailed architecture grounding

The new task is a detailed architecture plus actual government-source data acquisition, not a claim that a production weather service has been trained. Keep immutable raw files with source, retrieval time, observation time, units, licence/access terms, checksums and limitations. A small public starter pack is acceptable only when distinguished from a training corpus and the outstanding Indian access requirements.

## Actual code trace

`POST /api/runs` in `nowcast/service.py::run` validates a Pydantic request, calls `simulated_run` or `observed_run`, computes content-based identity and persists JSON to SQLite. Repeated requests retain the original row, but computation happens again before insertion. There is no scheduled ingestion, public dispatch, authorization or operational calibration.

Simulation: `synthetic_event` generates radar, satellite, lightning and NWP fields; `snapshot` returns three causal input frames with availability masks. `predict` uses global cross-correlation motion and small logistic heads trained only on generated data. Site sampling and threshold-based local receipts are in `service.py`. Current lightning windows are fixed 15-minute windows ending at a selected horizon, not cumulative probabilities. Storm component labels restart each request; these are not tracked lifetime identities.

Observed: `real_data.load_sample` verifies two pinned Météo-France NPZ hashes, loads numeric arrays with `allow_pickle=False`, selects six known frames and samples every third pixel. `replay` uses two frames to estimate global motion and compares translated echoes with later observed radar. Source timezone remains unverified. This path predicts a >=20 dBZ echo, not lightning or a severe storm.

`observations.select_as_of` enforces observation valid time and availability time before issue time, but no live provider adapter currently calls it. The new design must preserve that causality and not substitute an archive download timestamp for historical availability.

The React PWA shares this API, caches only the app shell and an explicitly saved historical simulation record. It does not calculate current weather offline. The receipt API is local simulation only. Newly collected data must not silently enter the simulator-trained model.

## Accepted research direction

Design one regional MVP: initially 30-minute cumulative lightning occurrence within 8 km, a separate versioned target from the current simulator. Proposed 128x128 central tile at 2 km with a chosen halo, six inputs at 10-minute cadence; configuration is contingent on actual source sampling and latency. Keep background dense forecasting, motion/growth baselines, causal storm tracks, missing-source age and mask features, separate calibration and quality reporting. Begin with a compact temporal model; graph/diffusion are experiments after the simpler baseline. One website/PWA, officer review and public official-warning consumption, no automatic authority claim.

## Candidate contract

Produce caller usage first, core types/signatures, module ownership, storage/deployment, retry/idempotency, training/inference separation and rationale. Two structurally different options: a regional modular worker backed by a transactional job table, versus a stream/event architecture with independently scaled consumers. Score: causality, realistic data access, recovery, ownership clarity, and pilot cost/operability (1–5 each). Proposed APIs must be labelled as sketches. Preserve prototype endpoints. Record alternatives rejected and what could be adopted from the other structure. No deployment or forecast-model changes in this phase.

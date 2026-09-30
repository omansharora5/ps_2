# Continuous forecasts and operator decisions: implementation design

30 September 2026. This is the design record for the current iteration, separate from the research conclusions.

Phase checklist:

- [x] Ground existing callers and state.
- [x] Sketch two alternatives and compare against the same criteria.
- [x] Select within the user's authorized implementation scope.
- [x] Implement the selected bounded components.
- [x] Verify behavior and update delivery evidence.
- [x] Reconsider implementation conflicts: no architecture restart was needed; retain the standalone queue and isolated STLDM CLI boundaries.

## Grounding

`POST /api/runs` in `nowcast/service.py` calls `simulated_run` or `observed_run`. `snapshot` in `nowcast/observations.py` records source state, acquisition time and availability time. The simulator and observed replay use separate prediction paths. The service saves a content-identified result to SQLite through `persist`, using `INSERT OR IGNORE`; old results are immutable. It does not run a continuous provider subscription.

`POST /api/receipts` loads a saved simulation, selects one of three research sites, compares its probability to an operator-selected threshold and subtracts preparation time from the target window's start. `ReceiptRequest` validates the caller's controls. The website owns only form state and displays the saved decision. Its public preview caches that same clearly labelled historical receipt. The native operator view separately reads the catalogue and runs a simulation. Neither role selector is authentication, and there is no public dispatch function.

The existing receipt has no configurable observation-support gate. Adding a generic numerical 'trust percentage' would imply a confidence measurement that has not been established. We will instead record explicit requirements for source recency/support and keep model-validation status separate from hazard probability.

The native public screen already keeps optional GPS separate from manual city selection. A citizen SMS report should have its own editable locality and observation note. It must not automatically insert the device fix or forward a practice alert as if it were a warning. The platform composer owns recipient selection and final send.

## Caller usage and two alternatives

All three background slots are occupied by independent primary-source research. Two implementation candidates are therefore sketched inline, as allowed by the architecture workflow when no additional slots are available.

Candidate A adds a small domain policy behind the existing receipt caller:

```python
assessment = assess_research_decision(run, site, policy)
receipt = persist_existing_receipt(assessment)

queue = LatestForecastQueue(regions=["pilot-north", "pilot-south"], max_running=1)
queue.submit(ticket, now=received_at)
job = queue.take(now=clock_time)
# Regional worker computes one result outside the queue.
publish_current = queue.complete(job, now=finished_at)
```

The receipt owns immutable decision evidence; the pure policy owns thresholds and reason codes. The queue owns only bounded metadata, coalescing and publication ordering. It never owns NumPy tensors, user locations, model weights or a persistent archive. The existing API does not start this queue automatically. A future ingest worker must drive it and provide durable input/result storage.

Candidate B introduces a persistent event service for ingestion, forecasts, approvals and delivery. Callers append events, per-region actors consume them, and a read model reconstructs current state. It provides a common revision/audit mechanism but requires a broker, persistent consumers, recovery rules and a real provider stream. Adding those now would expose operational infrastructure decisions before we have the feed contract. It also does not solve model validity or officer authentication by itself.

| Criterion, scored 1–5 | A: existing receipt + bounded queue | B: persistent event service |
|---|---:|---:|
| Preserves current simulation/replay semantics | 5 | 3 |
| Small public interface hiding real policy complexity | 5 | 3 |
| Can verify revision races without live feeds | 5 | 4 |
| Bounded local compute/memory | 5 | 3 |
| Durable multi-process recovery | 2 | 5 |

Select A for this research release. Adopt B's explicit immutable revision identity and stale-result rejection, but defer its broker and distributed state. This comparison concerns the implemented pilot components, not a claim that one process serves all India. Neither candidate requires an LLM.

## Selected types and invariants

`ResearchPolicy` carries a probability threshold, preparation minutes, minimum recent spatial-source count and maximum source age. `assess_research_decision` returns review/hold/unavailable/below-threshold state, the actual qualifying sources, failed checks and deterministic explanatory text. Source timestamps must precede issue time; NWP is context rather than an independent recent spatial observation for this count. This policy cannot authorize public publication of synthetic data.

`ForecastTicket` carries a region, issue time, revision, input fingerprint, model version and expiry. Its identity is immutable. `LatestForecastQueue` accepts only configured regions, bounds concurrent work, keeps at most one waiting ticket per region and refuses contradictory tickets with the same issue/revision. Completion of an older revision cannot publish over a newer requested revision. Expired jobs cannot publish. A current result may still be displayed until its validity ends while the next revision is being computed; a failed update must remain visible.

The queue has one owner, the regional worker loop. It is not a thread-safe database or a distributed lease. Its methods are synchronous metadata transitions; expensive model inference occurs outside it. Process restart requires replaying durable inputs and current revision watermarks from a future ingestion store. This boundary avoids a misleading production scheduler claim.

Successful `complete` returns publication eligibility at that transition, not an atomic database publication. The eventual caller must serialize completion/publication with new submissions or perform a durable compare-and-set against the current revision. It must not treat an earlier `True` return as permission to publish after a newer input has been accepted.

SMS composition uses a platform boundary with explicit user initiation and bounded note/locality lengths. Its result is composer status, never delivery proof. The report remains an unverified observation. Bluetooth relay, signed official alert envelopes, spatial subscriptions and carrier SMS gateways remain separate integrations with hardware/service testing requirements.

## Verification contract

Test high probability with poor evidence, a late observation claiming to be available, threshold boundaries, no-data behavior and synthetic publication blocking. Preserve receipt idempotence and the existing negative preparation deadline example. Queue tests cover duplicate requests, same-revision conflicts, supersession during inference, multiple regions, capacity, expiry and late completion. Test the native report's preview, no automatic recipient/location, unavailable service and honest platform results. Existing forecast calculations must continue to pass their scientific checks.

Final review also found a UI receipt race: a save response can arrive after the officer changes a control. The workbench now displays a receipt only when its run, site, threshold, preparation time and support policy match the current controls. An actual delayed HTTP response test confirms that an old receipt cannot supply a new explanation or public-preview action.

The research documents will determine the STLDM adapter and meteorological/delivery recommendations. They do not silently change these implementation boundaries or convert a checkpoint example into Indian lightning validation.

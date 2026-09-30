# Candidate A Local replay and verification workbench

## Problem and caller usage

A district duty officer needs to know which observations supported a forecast, whether it remains usable after a feed fails, and how much time remains to act. The first artifact must run without restricted Indian data and must expose the distinction between simulation and observed weather.

```python
result = run_forecast(ScenarioRequest(event_id="demo-62", step=8, horizon=30))
degraded = run_forecast(ScenarioRequest(event_id="demo-62", step=8, horizon=30,
                                     disabled_sources=["radar"]))
receipt = save_receipt(result.run_id, site_id="school", preparation_minutes=20)
```

## Shape

- `observations.py` owns synthetic events, independently sampled sensor fields, two-radar mosaics, and causal source selection. A field has valid time, availability time, units, mask, and provenance. Real MétéoNet samples use a separate adapter and explicit coordinates.
- `forecast.py` owns motion estimation, persistence and advection, feature construction, a trained logistic fusion model, and source-abstention policy. Pure array functions hide forecast details from the web API.
- `verification.py` owns masks, counts, probability scores, reliability bins, and neighborhood scores. Undefined statistics are null, never silently perfect.
- `service.py` owns API request validation, bounded caching, SQLite evidence receipts, and the downloadable run record. No outbound alert action exists.
- Browser controls choose event, valid time, hazard, model, missing sources, and action lead time. A geographic raster and tracks are paired with a real computed baseline comparison.

```python
class ForecastRequest:  # validated at the HTTP boundary
    event_id: str
    step: int
    horizon: int
    disabled_sources: list[str]

def source_snapshot(event, issued_at, disabled_sources) -> ObservationSnapshot: ...
def forecast(snapshot, horizon, model_artifact) -> ForecastResult: ...
def verify(prediction, truth, valid_mask, threshold) -> Verification: ...
```

Forecast takes only observations available by issue time. Verification takes future truth after prediction has completed. Model weights, split IDs, calibration choices and version are saved. Model training uses disjoint synthetic events initially; its skill is explicitly simulator skill. A downloaded real radar sample independently exercises ingestion, advection and verification. Neither path claims real Indian lightning skill.

## Tradeoffs and alternatives

Use Python, NumPy and FastAPI, one local process and SQLite. Accept a transparent small model and a limited observed-data replay to get a complete, testable application now. A production spatial neural model remains an upgrade gated on usable Indian labels and evaluation.

A nationwide queue plus GPU workers plus PostGIS plus a Transformer exposes deployment and data contracts before data access is established. It is a later deployment shape. A browser-only mock lacks a credible scientific boundary. A pure research notebook lacks the duty officer's decision workflow. This candidate keeps only the necessary shared service boundary.

## Verification plan

The root implementation owns the evidence for each claim. Test future-data isolation, invalid timestamps, radar overlap, zero-source abstention, unchanged output when withheld truth changes, metric denominator edge cases, no frame wraparound, and idempotent receipt storage. Run real HTTP and browser flows against the trained artifact and both data modes. Save measured results, including cases where the baseline wins.

## Risks

Synthetic calibration cannot transfer to India. Small MétéoNet samples cannot establish regional skill. Thresholded reflectivity is a convective proxy, not observed thunder. Local hazard probabilities cannot be added or maximized and described as the probability of an event anywhere in a district. A decision deadline is a prototype timing calculation, not a validated emergency procedure.

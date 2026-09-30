# Verification plan

The application can establish software behavior and reproducible sample results. It cannot establish operational Indian lightning accuracy without Indian labels and a representative held-out evaluation.

| Claim | Evidence owned by root implementation | Failure that would refute it |
|---|---|---|
| Forecasts use only information available at issue time | Perturb future arrays and late-arriving inputs while keeping the issue snapshot fixed | Forecast changes |
| Missing observations remain unknown | All-missing and individual-source tests, visible data status and abstention | Missing radar/lightning becomes a zero-hazard observation |
| Multi-radar overlap respects reflectivity units | Analytical linear-Z weighted blend test | Arithmetic mean in dBZ |
| Forecast advection does not wrap across map edges | A boundary pulse translated out of the grid | Pulse reappears opposite edge |
| Reported scores are computed from held-out truth | Hand-counted contingency table and probability test, deterministic experiment artifacts | Constants, test-label model fitting, or invented skill |
| Radar sample provenance and sequence are known | SHA256 against manifest; exact timestamps and contiguous-window check | Altered file accepted or a gap treated as one 5-minute interval |
| Receipts preserve the forecast and action calculation | Repeated saves return the same identity; fetch restores identical content | Duplicate records or changed evidence |
| Browser controls drive real results | Browser changes lead time, hazard, sensor state, replay mode and saves/exports a receipt | Decorative controls, stale result, JS exception |
| The local app remains usable without external tile servers | Browser screenshot with a local coordinate raster and map labels | Blank geographic display without a network connection |

Model training, API integration and browser checks cover distinct boundaries. Additional runs are justified by code changes or discovered failures, not by a desired pass count. The final report will distinguish document checks, scientific invariants, measured execution, and unresolved validation.

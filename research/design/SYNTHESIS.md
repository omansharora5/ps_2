# Architecture decision

Candidate A is the implementation base. Candidate B supplies the future spatial model and the stronger source, label and provenance contracts. Both candidates were read and reviewed against the architect red flags. The root performed the comparison after the independent candidate was complete; no second model-family judge was available without changing the inherited model.

| Criterion, 1 weak to 5 strong | A local replay workbench | B spatial model service |
|---|---:|---:|
| Runnable without restricted credentials | 5 | 2 |
| Preserves forecast causality | 4 | 5 |
| Makes evaluation defensible | 4 | 5 |
| Handles absent sources explicitly | 4 | 5 |
| Small implementation and deployment burden | 5 | 2 |
| Total | 22 | 19 |

The scores are design judgments, not experimental measurements. B is scientifically stronger when representative paired observations and lightning labels exist. Those prerequisites are not established for India. A can test the software and show real radar ingestion today.

Adapted from B: immutable issue snapshots; separate direct-lightning and reflectivity-proxy labels; receipt-time filtering; calibration lineage; explicit abstention; immutable forecast receipts. Kept from A: one local service, CPU NumPy model, static browser app, replay as the default mode. Rejected for the first implementation: conditional first-event hazard neural head, national queues, GPU orchestration and public dispatch. These need evidence and integrations the current data do not support.

The implemented logistic model predicts fixed 15-minute lightning windows ending at each lead time. These are **not cumulative probabilities**, so monotonicity across lead times is not required. A future first-event head is a separate experiment and must not be silently substituted.

Verification is tracked in `research/VERIFICATION_PLAN.md` and the completed `VALIDATION.md`. The UI must label simulation probabilities separately from observed French radar echo forecasts.

# Detailed architecture decision

30 September 2026. Parent authored [candidate A](detailed-candidate-a.md); the architecture researcher independently authored [candidate B](detailed-candidate-b.md). Both used the [same grounding](detailed-grounding.md). The parent read both candidates; a separate read-only researcher cross-judged them after completion. There were no dropouts.

## Scores and selection

These 1–5 scores are design judgments, not performance measurements.

| Criterion | Parent A | Parent B | Independent A | Independent B |
|---|---:|---:|---:|---:|
| Causal selection | 4 | 5 | 4 | 5 |
| Realistic Indian access | 4 | 4 | 4 | 4 |
| Recovery/idempotence | 4 | 5 | 4 | 5 |
| Ownership clarity | 5 | 4 | 4 | 5 |
| Single-region cost/operability | 5 | 2 | 5 | 2 |
| Total | 22 | 20 | 21 | 21 |

Both reviewers selected A's modular regional worker. It has fewer operating components and is appropriate while the training archive and provider access are still being established. The independent reviewer valued B's explicit ownership more highly; this did not change the deployment choice. B's scientific contracts do not require its event broker.

## Grafts from B

- Freeze eligible observations, derive causal tracking/context, then seal the complete forecast manifest with those artifacts and runtime versions.
- Preserve raw receipts on parse failure. Separate pending request identity from the final manifest digest.
- Distinguish actual local readiness, provider publication evidence and assumed-latency replay. Late operational updates require a new actual cutoff/origin/target interval.
- Use lease fencing and conditional completion, plus a transactional publication outbox.
- Require complete label coverage for both classes in the first ordinary binary-loss experiment. Preserve partial positives separately without selection bias.
- Keep lightning baselines separate from precipitation baselines, and return site-to-grid offset rather than inventing exact-site calibration.
- Keep original probability interval visible when publication delay reduces remaining lead.

Rejected for the first pilot: durable broker and independent consumers, seven separately deployed domain services, and eventual-consistency projections as the default read path. Reconsider these only when measured source volume, backfills or resource isolation require independent scaling. Also reject request-time per-client GPU execution and a mutable “latest grid” without retained provenance.

## Verification and outcome

The final [detailed architecture](../../DETAILED_TECHNICAL_ARCHITECTURE.md) distinguishes present code, downloaded samples and proposed services. The cross-judge identified late-revision and historical-shadow ambiguities; both were corrected. The parent also incorporated the complete-coverage cohort, lease fencing, grid offset and probability-interval rules.

The concrete implementation in this task is bounded acquisition, decoding, immutable source manifests and verification. There is no production model, broker, authentication or deployment claim. Actual data checks and final counts are recorded in [the data inventory](../../data/government/README.md) and `artifacts/government_data_validation.json`.

# NCR ingestion and model work

Phase checklist: [x] Ground; [x] Sketch two alternatives; [x] Synthesize; [x] Implement; [x] Verify and revise.

Arena checklist: [x] Frame; [x] Fan out; [x] Cross-judge inline; [x] Pick; [x] Graft; [x] Verify.

## Grounding

`nowcast.service` owns FastAPI and includes `operations_api.router`. Existing `/api/runs` chooses a synthetic multi-sensor model or a historical French radar replay; neither supports current NCR observations. `data_catalog` exposes registered source samples. `operation_recipes` registers bounded work through the durable operations store; the worker owns subprocesses. Collection should stay out of HTTP request latency.

`scripts/collect_india_data.py` downloads fixed Bihar IMD SYNOP and NASA snapshots with bounded HTTP, raw files, hashes and atomic replacement. It does not refresh an NCR feed. `scripts/train_images.py` validates causal time arrays and episode schemas, uses storm/time group splits, and trains a compact ConvLSTM. `prepare_image_episodes.py` requires already aligned labelled arrays; it does not decode provider formats. `run_stldm.py` verifies pinned upstream code and weights, but deliberately only accepts the supplied normalized reference example. `forecast_updates.LatestForecastQueue` bounds pending/running regional tickets in memory; it is not a live collection service.

## Scope and caller usage

Collect actual NCR observations through documented public access; preserve request, retrieval time, observed time, raw bytes and units. Repeated runs must safely reuse identical records, and provider downtime must never become dry labels. Expose local read-only source status and data. Prepare valid rain/no-rain records using actual measured accumulation intervals. Build on existing model code and upstream models with compatible licensing, rather than promising unavailable pretrained Indian weights. Define a 30-minute model path that abstains when matched imagery/labels are unavailable.

Candidate CLI shape: `python scripts/collect_ncr_data.py --start YYYY-MM-DD --end YYYY-MM-DD`; `python scripts/ncr_model.py train --data <collection> --output <version>`; `GET /api/ncr/status`. The actual runnable commands will replace these sketches after synthesis.

## Design rubric

1. Fresh NCR records can be inspected, dated and reproduced; partial collection is explicit.
2. Rain/dry/unknown labels preserve observation interval and coverage, with no invented minute-level labels.
3. Retried or interrupted collection converges without corrupting accepted raw records.
4. Reuses existing training/evaluation boundaries, exposes no credentials, and separates unavailable feeds from fallback observations.
5. A small backend interface reports readiness and uncertainty without presenting a synthetic or coarse model as current NCR skill.

The source research and access tests determine what can be collected now. Credentials must come from the provider. No provider account creation, payment or external correspondence is part of this implementation.

## Synthesis

Read both candidates in full and judged inline against the five criteria above. Scores out of five: A 5/5/4/5/5; B 5/5/5/4/4. Choose A for the bounded single-region collection: raw files and committed manifests fit the existing sample conventions, avoiding another observation database before volume requires one. Graft B's explicit immutable forecast/input identities and exact interval eligibility. Preserve the existing durable operations store for job execution; this first collector is a bounded CLI and read-only API, not another scheduler. Reject broad microservice and broker infrastructure at this stage. No design dropout.

The initial source probe returned 11,479 numeric/coded variable records for the Delhi metro pilot rectangle during September 2026. This is not the whole statutory NCR boundary. The source supplies one-hour and other accumulation intervals, so derived wet/dry labels cannot silently become 30-minute labels. Download all pages, verify counts, preserve unknowns, and report actual observation time independently of retrieval time.

Model implementation reuses the existing ConvLSTM with compatibility-checked checkpoint initialization and a causal inference CLI. WeatherNext 3 is closed-source; its observation-driven refresh and probabilistic design are inspiration rather than available fine-tuning weights. Existing upstream STLDM remains a separately verified reference until its input/label transfer is established. Real NCR training remains gated on matching spatial inputs and independently observed targets.

## Verification and deviations

Implementation retains content-addressed surface snapshots, adds separate bounded public satellite-wind and MOSDAC metadata collectors, and integrates read-only NCR routes into FastAPI. Independent boundary review found and fixed provider rows outside the requested date window. Present-weather descriptions required a separate categorical adapter because numeric rainfall fields alone contained only reported zeros; observed rain/drizzle evidence is retained without inventing interval totals. A provider total-count disagreement keeps the month collection partial.

Fine-tuning reuses compatible weights and normalizers, excludes inherited event exposure from new held-out partitions and resets calibration. Inference publishes a complete NPZ atomically without overwriting an earlier forecast. Existing local models remain research examples; raw NCR image/label integration still requires access and alignment.

Verification: the regular-Python suite ran 155 tests with 10 optional-environment skips; the ML environment separately passed 21 transfer/probability tests. Actual IMD and MOSDAC requests succeeded, stored source hashes verified, and the running FastAPI process returned expected data and explicit forecast unavailability over HTTP. The packaged 31-file data snapshot was checked byte-for-byte after ZIP extraction. See `artifacts/ncr-implementation-check.json`.

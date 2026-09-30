# Regional prediction and public evidence extension

## Work phases

- [x] Ground: trace existing forecasting, training, reporting and client flows.
- [x] Sketch: compare two independent designs.
- [x] Agree: synthesize without a user checkpoint.
- [x] Implement: deliver usable feature paths and numerical research components.
- [x] Scrap/revise: close feedback windows before approval, withhold public vote counts, enforce onset eligibility and reject contradictory targets.
- [x] Verify: numerical, API, browser, native build and export checks; record remaining data gates in `VALIDATION.md`.

Arena phases: frame, independent fan-out, cross-judge, pick and graft complete. Verification evidence is recorded below and in `VALIDATION.md`.

## Synthesis and implementation contract

Both sketches are saved in `artifacts/feature-design-a.md` and `feature-design-b.md`. A read-only judge scored both 16/18 and preferred A's single store. Root selects B after considering that disagreement: public observation claims need separate access and retention from the immutable admitted training corpus. The separate ledger owns no jobs, trained models or approved dataset registry, so it does not duplicate operations authority. This iteration exports reviewed weak evidence; it cannot directly register unmatched votes as image episodes. No multi-store automatic admission transaction is introduced.

Graft A's exact idempotency conflict rule, revision-checked review, explicit consent and causal `phase_available_at`. Keep B's separate coverage-aware task losses and publication cutoffs. Reject a generic event bus, invented forecasts, raw benchmark publication without rights, and adding arbitrary report tables to an already large operations store. Both candidates leave accessibility underspecified; the concrete client contract below resolves that gap.

Root owns `community_store.py`, `community_api.py`, HTTP wiring and integration. Numerical implementation owns new `regional_science.py`, `regional_heads.py`, numerical scripts/tests. Web/native implementation owns the reporting/scorecard clients and shared report copy. Monthly scorecard/benchmark functions can live in a separate pure `public_verification.py` because they protect cohort and release policy, not sensor fitting.

The prototype uses four explicitly named NCR pilot cells with registered bounding boxes, not official administrative blocks. Users manually select where they actually are. Exact GPS coordinates and personal identity are not collected. Client installation IDs reduce duplicates but cannot prove independent people. Majority agreement is a weak candidate; local operator review with corroboration is required for export. The report target is observed rain presence within a 15-minute reporting window, not a 30-minute accumulation or lightning label.

### Shared client API

`GET /api/community/state?cell_id=delhi-central&month=2026-09` returns:

```json
{"enabled":false,"cells":[{"id":"delhi-central","name":"Central Delhi pilot cell","bbox":[77.1875,28.5875,77.2125,28.6125]}],"selected_cell":"delhi-central","prompt":{"question":"Is it raining where you are now?","forecast_status":"unavailable","window_start_utc":"...","window_end_utc":"..."},"aggregate":{"public_status":"collecting","counts_withheld":true,"independent_people_verified":false,"automatic_training":false},"evidence_card":{"status":"unavailable","rain_probability":null,"lightning_probability":null,"onset_interval":null,"heavy_rain_end":null,"confidence":"unvalidated","sensors":[],"tracks":[],"reasons":["No validated NCR forecast is registered."]},"scorecard":{"status":"unavailable","month":"2026-09","metrics":null,"reason":"No eligible observed test cases published."},"benchmark":{"status":"metadata_only","raw_release_allowed":false,"blockers":[]}}
```

`POST /api/community/reports` JSON: `{request_id: UUID, installation_id: UUID, cell_id: fixed ID, answer: yes|no|unsure, observed_at_utc: explicit UTC, consent_training: boolean}`. Response `{report_id, status:"recorded_unverified", duplicate:boolean, aggregate}`. Same request/payload reuses; conflicting request or second answer from one installation in a window rejects. Observed time must be recent and nonfuture. Current window is computed by server; returns its aggregate. No model answer is shown before voting. Report writes require `VAJRA_ENABLE_FEEDBACK=1`; foreign browser origins are rejected. Public internet deployment still requires stronger identity/abuse controls.

`POST /api/community/review` is enabled local-operator only. JSON `{cell_id,window_start_utc,expected_revision,decision:approve|reject,reason,evidence_url}`. Approval requires enough consented matching reports, a closed late-reporting window and independently checked corroboration stated by the reviewer. It records the exact revision; changed evidence invalidates a prior review. `GET /api/community/review-queue` returns `{windows:[...]}` with exact counts, revisions and `reviewable_after_utc` to the local operator only. `GET /api/community/export` is local-only and exports reviewed weak-label metadata, never people/installation IDs. Public counts and revisions are withheld.

`GET /api/community/scorecard?month=YYYY-MM` and `/api/community/benchmark` expose immutable publication artifacts when supplied, otherwise reasons for unavailability. Public scorecards never invent an IMD comparator. The first client implementation adds a report form, evidence and monthly scorecards on a new website page plus public reporting in the native app. No unsolicited SMS or push messages are sent.

### Client interaction contract

The website's `#/community` page and native public screen begin with no chosen reporting cell or answer. Users explicitly confirm presence in a named pilot cell; no existing search result or GPS fix becomes a report location. Training consent is optional and unchecked. A saved installation UUID and frozen request are durably written before sending; failed or interrupted requests retry with identical identity, timestamp, answer and consent until the user explicitly resets. Storage failure blocks sending. The server still rejects duplicate installation/window votes after a reset. Saved confirmation survives reload; stale requests must be reset rather than silently retimed.

The web page exposes source age/coverage, onset availability, immutable monthly scores, comparable-cohort results and benchmark gates without fabricated values. It hides forecast probabilities before a report is submitted. Local review remains a server-authorized action and sends the displayed aggregate revision. Native reporting shares protocol parsing and 13 draft dictionaries with the web, alongside the unchanged manual SMS composer. Native-speaker review remains necessary before public deployment.

## Current runtime and boundaries

`nowcast/service.py` owns FastAPI setup and includes `operations_api` and `ncr_api`. `/api/runs` runs synthetic Bihar fusion or historical French radar replay. Synthetic tracks come from connected radar components and one estimated translation. They are not observed NCR storm tracks. The web public/operator views read these explicitly scoped records.

`nowcast/ncr_api.py` reads checksum-verified IMD and supplemental source snapshots. NCR forecasts remain unavailable. Open-Meteo/GFS are model context; airport weather codes are separately qualified evidence; IMERG is file discovery until authentication and decoding. No raw Indian radar/lightning/INSAT matched corpus is admitted.

`scripts/train_images.py` owns the optional compact ConvLSTM's scalar event target and causal episode schema. It has separate event partitions and optional calibration. `nowcast/probability_evaluation.py` fits temperature scaling on calibration events and computes probability scores with event bootstrap. New event-time/lightning tasks need actual labels and explicit coverage; synthetic success cannot establish NCR skill.

`nowcast/operation_store.py` owns durable research jobs and dataset registrations. `operations_api.py` restricts mutations to enabled local research access. Its worker trains candidates and does not automatically promote models. The extension should preserve that admission boundary.

The existing website has hash navigation and shared `service-client.js`. The native app is a separate Expo Router project; its manually entered citizen report is currently an unverified preview. Reports must become durable backend records without turning arbitrary clients into trusted identity providers or bypassing model admission.

## Requested outcome and invariants

Add lightning/onset task definitions and executable learning/evaluation methods; monsoon phase calibration and seasonal Z-R fitting; explicit warm-rain/dust/coverage caveats; traceable evidence cards; monthly comparable scorecards; benchmark manifest/export gates; and a citizen reporting/review flow shared by clients.

Numerical outputs must distinguish fitted research models from unavailable operational predictions. No invented IMD comparator scores, onset minutes, matched Indian corpus or validated block-level lightning probabilities. Majority feedback is supporting evidence: self-selected correlated users, location uncertainty and duplicate identities prevent treating votes as guaranteed truth. Unknown outcome remains unknown.

## Candidate contract and rubric

Each candidate must write caller usage first, then a module/type/signature sketch with unimplemented bodies, data ownership and a rationale. Produce structurally distinct designs, not cosmetic alternatives. Keep the operational API free of PyTorch and optional collector dependencies. Read the architecture skill runner prompt and red flags.

Evaluate 0-3 on: honest scientific availability; durable/idempotent feedback with review admission; short calls and reuse of existing operations/calibration; executable methods for all requested numerical features; client clarity/accessibility; and verification/export provenance. Prefer the smallest interface that protects these invariants.

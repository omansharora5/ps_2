# Work plan

## Regional science and citizen evidence, 30 September 2026

- [x] Ground existing source, training, operations and client boundaries; verify requested novelty claims against primary sources.
- [x] Compare two architecture candidates, obtain an independent judgement, select the separate citizen ledger and pure numerical/publication modules.
- [x] Implement covered lightning and censored onset heads, phase calibration, seasonal Z–R methods and descriptive warm-rain/dust flags.
- [x] Implement shared website/native reporting, consent, frozen retries, private local review and weak-evidence export.
- [x] Implement immutable monthly scorecards, fair matched-cohort comparison and metadata-only benchmark release gates.
- [x] Review and repair privacy, admission timing, split leakage and onset eligibility/label consistency defects.
- [x] Verify numerical training/reload, full Python suite, HTTP workflow and documentation links.
- [x] Verify website journeys, mobile type/lint/tests and all-platform app exports; inspect live and fixture screenshots.

The final feature/flow guide is `docs/REGIONAL_FEATURES.md`. The model and dataset still require real matched Indian observations before operational claims. Public agreement does not automatically retrain or promote a model. Research corrections remove unsupported claims that Damini is observation-only, IMD does no verification, or that a first Indian benchmark/local Z–R contribution has already been established.

## Supplemental NCR sources, 30 September 2026

Reviewed the supplied training explanation as reference material and verified provider claims against official documentation. Added source-specific public collectors, raw/normalized snapshots, checksum receipts and bounded backend routes. Collected actual Delhi environmental/airport samples and numeric NCR GFS fields. Added Earthdata-gated IMERG file access and an ERA5 request template, with no claim of authenticated downloads.

Scientific safeguards preserve unknown precipitation, mixed model/observation provenance, native spatial support and separate initialization/valid/retrieval times. An independent review found metadata-integrity, raw-evidence, coordinate/time and boolean-quality gaps; fixed them and added regression checks. The source catalogue now links all eight additions. Documentation describes the ablation experiments still needed before integrating new inputs into a compatible model.

Verification: full Python suite ran 181 tests with 10 optional skips; all six saved supplemental snapshots and the NCR GFS snapshot passed offline verification; nine real HTTP checks passed. No visual browser was available. Details are in `VALIDATION.md` and `docs/SUPPLEMENTAL_DATA_GUIDE.md`.

## NCR collection and model reuse, 30 September 2026

- Collected September IMD station observations for a Delhi metro pilot: 11,479 variable records, 631 reports and four stations. Extracted 25 rain, 11 drizzle and five mixed thunderstorm precipitation descriptions separately from 195 explicit one-hour zero accumulations. Provider count disagreement keeps archive completeness partial.
- Connected public IMD satellite-derived BUFR collection and public MOSDAC INSAT catalogue search. The BUFR sample has no verified NCR coordinate crop; MOSDAC image downloads, Delhi radar and lightning events still require provider access.
- Added read-only NCR status/data API, compatibility-checked compact ConvLSTM fine-tuning and causal inference. Neither Google weights nor an operational NCR model is claimed. Wrote source/access, architecture and training guides and packaged verified observations.
- Passed the full backend suite, 155 tests with 10 optional-environment skips, and all 21 ML transfer/probability tests separately. Verified actual local HTTP responses and downloaded hashes. Detailed evidence: `artifacts/ncr-implementation-check.json`.

## Connected operations build, 30 September 2026

- Applied the requested architect and idempotent-operations skills. Traced the existing API, collector, trainer and clients; compared two independent designs; selected a SQLite ledger with immutable datasets/attempt artifacts and one OS-owned synchronous worker.
- Built bounded dataset admission, protected event roles and bytes, actual source/radar/training recipes, local-write API guards, retries, cancellation fencing and controlled daily checks. Held candidate series no longer prevent another series from being considered.
- Added a website operations page with actual stages/results, research links and failure recovery, plus a read-only native monitor with 13 draft locales. Selected details remain available beyond the recent-history list.
- Executed all three recipes through the real API/worker. Verified source hashes, duplicate reuse, six artifact downloads, exact frozen evaluation and synthetic exclusion from daily learning. The climatology baseline beat the generated-data candidate, and both interfaces report that result.
- Verified 113 regular-Python passes plus two optional skips, separate actual ML integration, the full 12-journey website run and final three targeted operations journeys. Native 37 tests, typecheck/lint, all-platform exports and 20 exported-web checks passed.
- Added the [runnable architecture and recovery guide](docs/OPERATIONS_GUIDE.md), updated README/training/mobile/system documents and recorded [verification limits](VALIDATION.md). Runtime databases, copied datasets and checkpoint files stay local under ignored `data/operations/`.

## Regional decision support, reference diffusion and resilient delivery, 30 September 2026

- Re-read the supplied proposals as research material and adopted useful published methods with explicit input/target and licence boundaries.
- Added three primary-source research notes: weather drivers and sparse sensors; STLDM, rapid updates and learning; geographic targeting, Bluetooth and SMS delivery.
- Added officer source-count/age policy controls, immutable assessments and clear reasons without inventing a trust percentage or authorizing synthetic public warnings.
- Implemented and independently reviewed a bounded single-owner regional revision queue. It keeps metadata only and refuses old, contradictory, expired or superseded work; no live provider stream is connected.
- Integrated the pinned official STLDM checkpoint through an isolated reference CLI. One CPU example ran successfully; persistence had lower image error. Independently verified hashes, past/future isolation and scores without repeating the expensive inference.
- Added the native citizen-report preview and explicit OS SMS composer, manual locality, blank recipients, thirteen draft translations and bounded pending-request lifecycle. No actual message was sent.
- Verified 63 regular-Python tests plus one optional skip, all thirteen probability tests in the ML environment, twenty-eight native tests, source checks, Doctor 21/21, all-platform exports and three native exported-web verification scripts. The initial nine website journeys passed; after fixing a delayed-receipt UI race, nine of ten passed together and the timed-out unchanged globe test passed separately. Its intermittent timeout remains recorded.
- Updated README, architecture, training/mobile guides and validation with actual evidence and remaining operational/physical-device limits. The reviewed design uses ordinary code for decisions; Jev remains an optional measured note-routing hypothesis.

Current deliverable: `REGIONAL_DECISIONS_AND_CONTINUOUS_FORECASTS.md`. Supporting evidence: `artifacts/stldm-reference-summary.json`, `artifacts/sms-preview-check.json`, `artifacts/mobile-build-check.json` and `VALIDATION.md`. The following earlier work entries retain their historical scope.

- [x] Read both supplied documents and workspace instructions.
- [x] Ground the problem. This is an empty workspace, with no existing implementation to trace.
- [x] Research the official requirement, impact, existing products, datasets, and forecasting methods.
- [x] Frame and compare two architecture candidates, then record the synthesis.
- [x] Write the complete research and implementation specification with a claim ledger.
- [x] Implement a runnable prototype with explicit data provenance and baseline verification.
- [x] Test scientific invariants, failure cases, API behavior, and the browser workflow.
- [x] Review the final claims against evidence and record remaining operational gaps.

## Architecture comparison rubric

Score each candidate from 1 to 5 for a runnable no-credential demonstration, preservation of forecast causality, defensible evaluation, missing-source behavior, and implementation simplicity. Research agents write separate files. No public notifications or operational forecasts are authorized by this prototype.

## Source documents

The supplied Markdown is a technical interpretation. The DOCX explicitly calls its analysis an interpretation. The 22/500 submission count, rank, and deadline are unverified contextual claims, not implementation requirements. Text extracted from the DOCX is retained in `research/input/problem-analysis-docx.txt` for traceability.

## Completion evidence

`SIH26072_RESEARCH_AND_BLUEPRINT.md` is the main deliverable. Research notes contain primary links and explicit access limitations. `VALIDATION.md` records 17 scientific/API tests, two browser tests, observed radar scores, synthetic model scores and measured execution. A local service is left running at `http://127.0.0.1:8000`. Indian operational training, feed access and field validation remain explicit future gates, not completed claims.

## Friend-note review and website/app iteration, 30 September 2026

- [x] Read both new attachments and compare their claims with the actual implementation.
- [x] Research TypeSafe Jev's hosted API, offline limitations and possible bounded role.
- [x] Check newer weather architectures and correct unsupported novelty/calibration claims.
- [x] Write `PRODUCT_FLOW_AND_ALGORITHMS.md`, `research/FRIEND_NOTES_REVIEW.md` and `research/JEV_ASSESSMENT.md`.
- [x] Apply ui-ux-pro-max, record design choices and build overview, officer, public-preview and guide flows.
- [x] Add URL navigation, mobile controls, accessible focus, expandable evidence and recorded-state loading/retry handling.
- [x] Implement a versioned offline app shell and explicitly saved historical simulation preview.
- [x] Verify science/API behavior, website journeys, offline recovery, mobile layouts, keyboard skip navigation and manifest installability.

The final validation addendum records the expanded checks. No new trained weather architecture, Indian feed, live public warning, authentication or Jev integration is claimed.

## Structured proposal and evidence library, 30 September 2026

- [x] Define the accepted problem, solution, differentiation, architecture and data flow.
- [x] Document stack, feasibility, adoption model, risks, impact and sustainability.
- [x] Collect three primary surveys and three newspaper reports with samples, dates and limits.
- [x] Curate twelve primary research papers, including verified 2025 and 2026 publications.
- [x] Check official public-service alternatives, data access and business assumptions.
- [x] Distinguish historical statistics, working code, proposed experiments and unmeasured outcomes.
- [x] Review document references and consistency against the current implementation.

Main deliverable: `SIH26072_PROPOSAL_AND_EVIDENCE.md`. Supporting notes: `research/SURVEYS_AND_NEWS_2026.md`, `research/PAPER_REFERENCE_LIBRARY.md` and `research/VIABILITY_AND_SUSTAINABILITY_EVIDENCE.md`. No new field survey, customer validation or operational forecast result is claimed. A fresh MoSPI 2025 PDF download timed out; the proposal retains the earlier directly verified 2022 statistic from MoSPI 2024 and labels its reporting year.

## Detailed architecture and government data collection, 30 September 2026

- [x] Ground: trace the existing forecast and observed-data paths.
- [x] Sketch: framed two independent designs, read both, cross-judged, selected the regional worker and incorporated stronger causal/recovery contracts.
- [x] Agree: proceeded within the requested architecture and data-collection scope; no approval checkpoint requested.
- [x] Implement: wrote the detailed architecture and collected the government data starter pack with source manifests and CSV views.
- [x] Verify: checked scientific contents, timestamps, units, 22 file hashes, parser behavior, idempotent reruns and document references.
- [x] Scrap: corrected late-update timing, partial-coverage labels and delayed-probability interpretation; used official wgrib2 when the ecCodes native library was unavailable. No wholesale design restart needed.

Architecture comparison: causal data contracts, Indian access realism, recoverable/idempotent processing, understandable ownership, and single-region cost/operability; score each 1–5. Parent and architecture researcher produce separate candidates; the other researchers collect independent provider subsets. This bounded delegation is requested by the research and architect/arena skills.

Deliverables: `DETAILED_TECHNICAL_ARCHITECTURE.md`, `data/government/README.md`, consolidated `inventory.json`, three provider manifests and collection notes, five collection/preparation/verification scripts, and `artifacts/VAJRA_GOVERNMENT_DATA_STARTER_PACK.zip`. New source content totals 18 files / 11,232,879 bytes, comprising eight weather-data payloads and ten metadata/documentation records. Four derived files add 507,683 bytes. The pack contains actual IMD, NASA and NOAA data with explicitly identified cloud mirrors. It is not a matched Indian training dataset and was not passed to the synthetic model.

Validation evidence: `artifacts/government_data_validation.json` and `artifacts/architecture_document_check.json`. Full scientific parsing, raw/derived checksum verification and malformed/truncated GRIB rejection passed. All local links in the six new main evidence documents resolve and Markdown fences balance. No app behavior changed, so the earlier application tests were not rerun for these standalone acquisition scripts and documents.

## Image methods, collection API and native delivery, 30 September 2026

- Implemented the real-radar processing lab: raw/despeckled/smoothed images, persistence, global translation, Horn–Schunck dense flow, connected objects and held-out comparisons.
- Connected the manifest catalogue, provider/API links, hash-checked downloads and bounded local collection jobs.
- Added the optional compact ConvLSTM preparation/validation/training/evaluation path and documented the matched-observation requirements. CPU smoke and checkpoint evaluation ran on explicitly synthetic examples.
- Built the Three.js Earth explorer with search/focus/zoom, static NASA texture, illustrative clouds, reduced motion, pause and WebGL fallback.
- Built the separate Expo React Native client with public/operator views, shared geography, twelve Indian languages plus English, persisted preference, Urdu text alignment and bounded device-voice speech.
- Cross-reviewed scientific and UI contracts. Fixed weak-reflectivity masking, separate intensity-score denominators, selected-city rotation, voice-discovery timeout, forecast context and tab-label spacing.
- Verified 34 Python tests, the eight website browser journeys plus four affected final regressions, ten native tests, TypeScript/lint, Expo Doctor 21/21, all-platform exports and the exported-native browser flows.
- Preserved exact dataset bytes through Git attributes; checked 38 staged data files against their local bytes and rechecked all 18 source-manifest hashes.

Implementation, guides, sample data and verification evidence were published to the private [omansharora5/ps_2 repository](https://github.com/omansharora5/ps_2) on `main`, after release review. The initial delivery push used a normal branch update and its remote SHA matched local HEAD. Actual Indian training, signed native installation, physical-device speech, background notifications and operational warnings remain outside the evidence established here. The native audit retains thirteen moderate findings, with no forced major-version downgrade.

## Algorithm decisions, calibration and optional location, 30 September 2026

- Verified WeatherNext 3's actual model/access/delivery contract, TimesFM 3.0's separate weight restriction and Jev's hosted text interface. Recorded eleven useful primary implementation repositories and provider/API access boundaries.
- Added fourteen primary-source evidence groups and a matching CSV. Preserved reporting periods, samples and denominators; flagged the official crop-table total discrepancy. Kept lives-saved and project ROI unknown.
- Wrote `ALGORITHM_DIFFERENTIATION_AND_VALIDATION.md`, connecting sensor methods, model choices, public/operator geography, meaningful differentiation, data access, verification and controlled retraining.
- Added optional four-partition calibration to the compact ConvLSTM CLI with reproducible split/checkpoint evidence. Independent review found a normalization leak from permanently unavailable training observations; corrected it and verified invariance.
- Added explicit foreground device-location selection with cancellation, bounded failures, uncertainty/time display, manual fallback and no invented regional coverage. Coordinates are not sent to the research API.
- Verified 46 regular-Python tests plus one environment-specific skip, all thirteen probability tests in the ML environment including that skipped integration, twenty native tests, two exported-native browser scripts, source checks and all-platform bundle export.
- Recorded the synthetic negative result: calibrated Brier improves over raw output but remains worse than training climatology. No weights are promoted to the app and real Indian lightning reliability remains unestablished.

Current evidence is in `VALIDATION.md`, `artifacts/calibration-smoke-summary.json`, `artifacts/location-preview-check.json` and `artifacts/mobile-build-check.json`. The default six-group training path remains available. Device tests, live authorized feeds and matched Indian training data are still required for an operational service.

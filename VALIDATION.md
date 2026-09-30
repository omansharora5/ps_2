# Validation record

This record distinguishes software checks from real-weather and physical-device validation. The current delivery extends the original research prototype; the older benchmark results below retain their original scope.

## 30 September extension: durable research operations

The website, FastAPI service, SQLite ledger, separate numerical worker and native read-only monitor now share an executable research workflow. This adds real controlled candidate generation from registered datasets; it does not connect a national observation stream, promote models or dispatch warnings. [Architecture and commands](docs/OPERATIONS_GUIDE.md).

| Check | Actual result and scope |
|---|---|
| Final regular-Python suite | **115 discovered: 113 passed, 2 skipped**, 52.381 seconds. Both skips require optional Torch |
| New store/runtime boundaries | 21 store and 13 runtime tests included above: concurrent duplicate reuse, capacity, protected event roles/bytes, stale publication, conditional retry, API guards, artifact tampering and actual child-process lock contention/crash release |
| Process restart persistence | Two separate owned Python processes created and reopened an isolated store. Queued/completed records, attempts, timestamps and full-record hashes remained identical. [Evidence](artifacts/operations-restart-check.json). This did not stop or restart the existing live services |
| Optional scientific integration | Actual calibrated ConvLSTM and exact frozen checkpoint evaluation passed separately in `.venv-ml`; not just mocked recipe calls |
| Real API and worker workflow | All three recipes completed in **22.64 seconds total** on this machine. Duplicate submissions reused their completed identities/attempts; six artifact downloads matched recorded SHA-256 and sizes. Four research links returned documents. [Evidence](artifacts/operations-workflow-check.json) |
| Source audit | **18/18** downloaded source files matched manifests. These remain historical, unmatched samples |
| Observed radar recipe | +10-minute dense-flow CSI **0.633886** versus persistence **0.549864**, one French radar case on common valid support; not a lightning or general superiority result |
| Synthetic training candidate | Raw Brier **0.211584**, calibrated **0.089959**, climatology **0.089687**, **two** held-out event groups. The baseline wins; `promoted=false` |
| Controlled learning | Demo-only live store recorded `waiting_for_labels`, then restored its previous paused setting. Unit tests cover mature observed admission, deduplication, unchanged events, failed/cancelled candidates, queue pressure and independent series |
| Website build and journeys | Production build passed. **12/12** full-suite journeys passed in 1.8 minutes. After final selected-job/padding changes, **3/3** targeted operations journeys passed in 18.3 seconds, including a real old-job detail outside a controlled recent-history projection |
| Native source/export | **37/37 tests**, typecheck, lint and Android/iOS/web exports passed. No packages changed. Doctor and dependency audit were carried forward, explicitly dated in [build evidence](artifacts/mobile-build-check.json) |
| Native exported-web journeys | Catalog/simulation 5, location 5, SMS 3 and operations 7 checks passed with zero page errors. [Operations evidence](artifacts/operations-mobile-preview-check.json) separates the actual completed candidate from controlled failure/empty/quality fixtures |

The final UI review checked [desktop operations](artifacts/operations-desktop.png), [phone width](artifacts/operations-mobile.png), stale snapshots and the native monitor. A selected experiment remains stable when it falls outside the latest 30 records. Keyboard refresh and phone overflow checks passed. A browser fixture initially left a response handler running during teardown; the fixture was corrected, then all three targeted checks passed.

This release still has the existing Earth bundle-size advisory and 13 moderate native dependency audit findings; no new dependency was introduced. All-platform export is not a signed native installation. Physical phone speech/SMS, Bluetooth relay, live Indian lightning validation, remote operator authentication, automated provider-to-label ingestion and deployment-scale capacity remain unverified or unimplemented. The research store has explicit workload limits and no automatic disk-retention process. Historical sections below describe earlier releases rather than overriding these current results.

## 30 September extension: decision evidence, STLDM and reporting

The website now saves explicit probability/support policy assessments. Source ages are recomputed from causal timestamps; an insufficient recent-source count holds the result for evidence review even when its score is high. The returned reasons distinguish a research support check from calibrated confidence. Synthetic results always have public dispatch blocked. A standalone single-owner queue coalesces regional updates and refuses superseded/expired completion; a live provider stream, durable recovery and atomic publication remain outside that queue.

| Check | Actual result and scope |
|---|---|
| Complete regular-Python suite | **64 discovered: 63 passed, 1 skipped**, 15.811 seconds. The skip is the optional Torch integration |
| Probability suite in `.venv-ml` | **13/13 passed**, 20.562 seconds, including the skipped Torch integration; these overlap the complete suite and are not 13 additional unique tests |
| Decision/update tests | Ten tests cover causal recency, threshold/evidence separation, receipt identity, preparation timing, bounded queue state, concurrent-region scheduling, supersession, duplicates/conflicts and expiry |
| Independent policy review | All ten tests passed; additional causal-time cases and twelve simultaneous identical receipt requests passed. This does not establish a distributed scheduler or production authorization |
| Official STLDM integration | One author-example inference completed on CPU with pinned source and checkpoint, strict safetensors loading and five past frames only. Model call **113.386315 s**; measured in-function pipeline **150.564177 s**, during other verification activity |
| STLDM scientific result | On one normalized reference example, MSE **0.0081866016**, compared with persistence **0.0079289055**. Persistence wins this case. No physical-unit, calibrated probability, Indian or lightning-skill claim |
| STLDM independent review | Seven boundary tests passed; separately recomputed sample preparation, input/truth separation, metrics and artifact/source hashes matched. CUDA and peak CPU memory were not tested |
| Production web build | Passed; lazy Earth chunk retains its size advisory |
| Website browser journeys | Initial nine-test suite passed. After adding the delayed-receipt fix, **9/10 passed** in the full run; the unchanged Earth-focus test timed out and then passed alone (**1/1**, 18.5 seconds). Both decision-policy tests passed, including the delayed-response race. The intermittent globe timeout's cause is unestablished |
| Native source and exports | **28/28 tests passed**, typecheck/lint passed, Expo Doctor **21/21** and Android/iOS/web exports passed. [Build evidence](artifacts/mobile-build-check.json) records bundle hashes |
| Native exported-web journeys | Existing language/TTS fallback, API failure/retry and explicit location journeys passed with no page errors |
| SMS exported-web journey | Actual unavailable-on-web path retains the editable unverified draft; city selection does not fill its locality; report text was absent from network requests and localStorage. [Evidence](artifacts/sms-preview-check.json) |

Visual review covered [operator evidence controls](artifacts/operator-evidence-mobile.png), the [SMS form](artifacts/native-sms-preview.png) and its [unavailable-service result](artifacts/native-sms-result.png). The first SMS browser attempt incorrectly tried to click the deliberately disabled empty-draft button; the verification was corrected to assert disabled state. No application change was needed for that failure. A separate real UI race was corrected: a late receipt response cannot describe changed controls or expose their public-preview action.

The native report action uses an empty recipient list and lets the user send through the OS composer. No SMS was sent, and no physical composer, carrier delivery, Bluetooth radio, signed native installation or audible phone speech was tested. The existing dependency audit retains **13 moderate, zero high/critical** findings. Translation completeness is not native-speaker approval.

The [current design and recommendations](REGIONAL_DECISIONS_AND_CONTINUOUS_FORECASTS.md) link three new primary-source research notes. Daily outcome evaluation and reviewed retraining are specified, not deployed as unattended learning. No Jev service is required or connected. These additions do not change the simulator into a validated Indian weather service.

## 30 September extension: probability calibration, location and research

The training CLI now supports four-way event separation with `--calibrate`, while preserving the default three-way path. It saves a bounded regularized temperature fit, training climatology and split hashes, then evaluates frozen predictions. Reports include Brier/log loss, average precision with tied-score handling, reliability bins, POD/FAR/CSI and whole-event bootstrap intervals. [Method and result details](docs/CALIBRATION_AND_VERIFICATION.md), [reproducible evidence](artifacts/calibration-smoke-summary.json).

The independent review found and corrected a causal normalization bug: values unavailable to every training forecast could still affect training statistics. Normalization now uses the union of usable training-window measurements. A regression changes an unavailable frame to `1e6` and verifies unchanged normalization, input tensors and model outputs; a late but reachable measurement remains usable.

| Extension check | Result and scope |
|---|---|
| Complete regular-Python suite | 47 discovered: **46 passed, 1 skipped**, 9.260 seconds. The skip is the opt-in Torch integration test |
| Probability suite in `.venv-ml` | **13/13 passed**, 7.928 seconds, including the actual Torch integration skipped above |
| Training/evaluation | Eight-group calibrated CPU smoke, six-group compatibility smoke and exact frozen evaluation passed; changing test labels leaves fitting/calibration unchanged and changed-corpus evaluation is rejected |
| Synthetic calibration result | Brier **0.211584 → 0.089959**; training-climatology baseline **0.089687** remains better. All 306 positive test cells remain missed at threshold 0.5 |
| Native source | **20/20 tests passed**; TypeScript/lint passed, Doctor **21/21** and all-platform export passed, recorded in [build evidence](artifacts/mobile-build-check.json) |
| Existing native browser journeys | City/pause, absent-voice fallback, Hindi persistence, Urdu alignment, real research API and failure/retry passed again with no page errors |
| New location browser journeys | Explicit-only request, overridden London coordinates, uncertainty, watcher cleanup, no coordinate-bearing request/localStorage, clearing, manual selection and denied-permission fallback passed with no page errors; [location evidence](artifacts/location-preview-check.json) |
| Research | 14 primary-source evidence groups and 11 implementation repositories reviewed; model weight licences, operational data timing, source denominators and one official-table arithmetic discrepancy recorded |

The browser checks use an exported React Native web client, a browser geolocation override and mocked denied permission. They do not verify native permission dialogs, GPS quality, device audio or warning delivery. Visual inspection covered the new location control and globe; the screen scrolls to coordinates, uncertainty and the explicit no-live-coverage message.

The neural smoke contains generated moving blobs, not Indian observations. Its two test groups do not support dependable scientific confidence intervals. Calibration has not made it an operational forecast, and no model has been promoted into the app. The website prediction engine and government starter corpus remain unchanged in this extension.

The [algorithm and differentiation decisions](ALGORITHM_DIFFERENTIATION_AND_VALIDATION.md), [model/API review](research/MODEL_AND_REPOSITORY_DECISIONS.md) and [Indian evidence register](research/LOCAL_WEATHER_IMPACT_EVIDENCE.md) separate implemented software, proposed experiments and unmeasured benefits. No new field survey, paired Indian corpus, mortality reduction, forecast superiority or procurement interest is claimed.

## 30 September delivery: image lab, data APIs and native app

The website now includes the animated Earth explorer, observed-radar processing laboratory and manifest-backed collection interface. The separate Expo React Native client provides public/operator views, twelve Indian languages plus English, place search and installed-voice speech. The optional ConvLSTM training CLI is independent of the models served by the existing workbench.

| Delivery check | Result and evidence |
|---|---|
| Final scientific/API suite | `python -m unittest discover -s tests -v`: **34 passed**, 26.352 seconds |
| Production website | `npm run build`: passed; Earth is a lazy-loaded chunk. Vite reports its chunk-size advisory |
| Website browser journeys | Complete suite **8/8 passed**; after final image/rotation changes, all **4 affected exploration tests passed again**, including actual download and collection-job completion |
| PWA and documents | `node scripts/verify-web-delivery.mjs`: no manifest/installability errors, keyboard skip navigation passed; training, mobile and detailed-architecture downloads returned HTTP 200 |
| React Native source | TypeScript and Expo lint passed; Expo Doctor **21/21**; focused tests **10/10**, including unresolved voice lookup timeout |
| Native/web exports | Android and iOS Hermes bundles plus web export completed; [exact bundle hashes and commands](artifacts/mobile-build-check.json). These are not signed native applications |
| React Native browser integration | [Preview check](artifacts/mobile-preview-check.json) passed: city/pause, speech-discovery failure, persisted Hindi, Urdu alignment, real catalogue/simulation and API failure/retry; no page JavaScript errors |
| Visual inspection | Desktop/mobile Earth and radar views, plus native public/Hindi/Urdu previews inspected; screenshots in `artifacts/` |

The completed CPU smoke is in [training-smoke-report.json](artifacts/training-smoke-report.json): six synthetic event groups, one epoch, 24/6/6 train/validation/test examples, saved checkpoint and reproducible standalone evaluation. Test Brier was 0.198232308 and CSI was 0 at threshold 0.5. This establishes a working training path, not useful weather forecast skill.

The real collection API check in [collection_api_check.json](artifacts/collection_api_check.json) fetched the catalogue, downloaded a manifest-listed file with a matching SHA-256 and completed a registered local GFS collection job. The corpus remains unmatched historical reference data, with Indian radar, INSAT and lightning archive access still pending.

Independent source reviews are recorded in [web/backend review](docs/reviews/web-backend-review.md), [backend/web review](docs/reviews/backend-web-review.md) and [native integration review](docs/reviews/native-integration-review.md). They identified and tracked scientific/UI edge cases before release; review is not a substitute for operational validation.

The [final release review](docs/reviews/release-review.md) found no material publication blocker. The [tracked-file scan](artifacts/release_scan.json) checked known credential patterns and local-state exclusions. [Git data verification](artifacts/staged-data-check.json) confirmed that all 38 data files retain their local bytes in Git and all 18 downloaded source hashes match their manifests. `.gitattributes` preserves dataset line endings so a clone does not silently invalidate these hashes.

The project was pushed normally to the private [ps_2 repository](https://github.com/omansharora5/ps_2), branch `main`. The initial delivery's remote commit matched local HEAD; environments, credentials, local databases and generated native builds were excluded.

The mobile dependency audit reports **13 moderate, zero high and zero critical findings**, recorded in the build evidence. They remain unresolved: npm's suggested forced fix would downgrade the Expo/Router stack across major versions. No such downgrade was applied. Reassess compatible dependency updates before deployment.

Physical Android/iOS installation, actual device audio in all twelve languages, offline voices, signed native binaries, notification delivery and live Indian forecast skill are not established in this workspace. There is no Android SDK/emulator/adb or iOS build environment. Native JavaScript exports and browser-preview results must not be described as installed-device tests.

## Original 29 September baseline

The following measurements describe the earlier supplied Windows build, before the image/native additions.

## Outcome

The production frontend builds, the local API runs, all **17 scientific/API tests pass**, and both **browser tests pass**. The browser checks exercise the running service at desktop and mobile widths, real computations, sensor failures, stored decisions and export. No browser JavaScript errors were recorded.

The app is a working research prototype. It is not a validated Indian operational warning service. The full neural architecture and Indian live integrations in the research blueprint are proposed next-stage work.

## Evidence and commands

| Check | Command or artifact | Result |
|---|---|---|
| Model fitting and held-out evaluation | `python -m nowcast.training` | Completed; model and evaluation JSON saved. Latest measured fitting/calibration time 38.184 s; fitting plus evaluation about 45.2 s |
| Scientific and API suite | `python -m unittest discover -s tests -v` | 17 passed, final run 4.231 s |
| Production frontend | `npm.cmd run build` | Passed; JavaScript bundle about 282.8 kB, about 88.7 kB gzip |
| Browser journeys | `npm.cmd run test:browser` | 2 passed; final run 20.9 s, including setup |
| Scientific sample integrity | Runtime SHA256 checks against pinned expected hashes | Passed for reflectivity and coordinate archives |
| Browser visual review | Screenshots in `artifacts/` | Desktop synthetic, real radar and mobile reviewed; map, controls and tables readable |
| Direct replay benchmark | [benchmark.json](artifacts/benchmark.json) | All four observed and three simulated horizons computed |

Python 3.14.4, NumPy 2.5.2, Node 24.20.0, React 19.3.0 and Vite 8.3.1 were used. Exact JS dependencies are locked. The Python HTTP test client emitted a deprecation warning about its current `httpx` integration; it did not affect the checks. There is no claim of cross-platform or production load testing.

## What the tests establish

- Radar composites average linear reflectivity, and all-missing input stays unknown.
- Motion recovers an imposed translation, and cells leaving one edge do not wrap to the opposite edge.
- Changing future radar, satellite, lightning and NWP arrays does not change the issue-time forecast.
- Source selection rejects future-valid, late-received and over-age observations, and compares timezone-aware datetimes.
- A stale radar is withheld as missing. Without radar, satellite and lightning, the learned forecast abstains even if NWP remains.
- The lightning target excludes the issue-time flash and respects the specified spatial radius.
- Event seed splits do not overlap.
- Contingency metrics match a hand-counted example. Empty data and undefined denominators remain null.
- The actual radar sample passes integrity, shape and five-minute continuity checks. Unsupported 60-minute replay is rejected.
- Invalid API values and lightning requests against the radar-only sample are rejected.
- Repeated run and receipt requests are idempotent. Saved receipt retrieval preserves the exact record.
- A +30-minute lightning window and 20-minute preparation time produce a review deadline of −5 minutes when the demo threshold is exceeded. No-data receipts remain unavailable rather than all-clear.
- The browser changes lead, issue time and target; removes/stales/restores sources; switches observed/synthetic data; saves and exports evidence; opens evaluation and receipts; and recovers after a deliberately failed API request.
- At 390 px mobile width there was no document-level horizontal overflow. Wide score tables can scroll within their own container.

During verification, explicit accessible labels were added to controls, the outcome-layer summary was corrected so it no longer displayed a blank score count, and global-motion correlation was changed to elementwise reductions to reduce small-vector BLAS overhead. The final checks above ran against the corrected implementation. Cold historical replay is slower than a synthetic forecast, so its browser assertion allows a documented longer wait while displaying a loading state.

## Actual observed radar scores

These numbers were computed from the bundled Météo-France sample at issue time **19 December 2018 10:15**, using its 10:10 and 10:15 observations. The source's naive timestamps are preserved; UTC was not independently established. The target is radar reflectivity at least **20 dBZ**, sampled every third original pixel. No lightning target exists in this sample.

Each pair uses the same finite prediction/truth intersection. Deterministic forecast Brier score is the mean squared error of its 0/1 predictions, not evidence of probabilistic calibration.

| Lead | Common valid pixels | Motion CSI | Persistence CSI | Motion Brier | Persistence Brier |
|---|---:|---:|---:|---:|---:|
| +5 min | 43,981 | 0.710716 | 0.637651 | 0.035538 | 0.048271 |
| +10 min | 44,032 | 0.584645 | 0.550681 | 0.058117 | 0.064430 |
| +15 min | 43,529 | 0.555373 | 0.506571 | 0.062257 | 0.074180 |
| +20 min | 43,590 | 0.508291 | 0.488428 | 0.074145 | 0.078596 |

This is one short observed case with highly correlated pixels. It supports the claim that the real replay, baseline and verification code execute correctly on this sample. It does not establish general radar forecast skill, superiority to pysteps, thunderstorm occurrence, lightning accuracy or India transfer.

## Actual held-out synthetic lightning scores

These are aggregated over six held-out generator seeds at issue step 8. The target is any simulated flash within 8 km in the 15-minute window ending at the lead. Models use the same common valid pixels at each lead. Temperature was selected on distinct validation events. Complete-source results are shown; the JSON also contains missing-source experiments and explicit unavailable outputs.

| Lead | Method | CSI | POD | FAR | Brier |
|---|---|---:|---:|---:|---:|
| +15 min | Learned fusion | 0.737921 | 0.781395 | 0.070111 | 0.009090 |
| +15 min | Motion | 0.694567 | 0.733333 | 0.070727 | 0.016152 |
| +15 min | Persistence | 0.544286 | 0.590698 | 0.126147 | 0.024247 |
| +30 min | Learned fusion | 0.582278 | 0.603431 | 0.056782 | 0.023685 |
| +30 min | Motion | 0.425574 | 0.429869 | 0.022936 | 0.044834 |
| +30 min | Persistence | 0.317636 | 0.347124 | 0.211009 | 0.057622 |
| +60 min | Learned fusion | 0.244997 | 0.274343 | 0.303922 | 0.071187 |
| +60 min | Motion | 0.220028 | 0.241113 | 0.284404 | 0.093381 |
| +60 min | Persistence | 0.124837 | 0.148377 | 0.559633 | 0.113644 |

The deterioration at +60 minutes is visible. The learned model does not dominate every metric: motion has a lower false-alarm ratio at +30 and +60 minutes. Its other target exposes a stronger failure: at +60 minutes the complete-source convective-proxy fusion CSI is **0.000**, versus **0.097826** for motion. With lightning removed, the +15-minute convective-proxy fusion CSI is **0.196347**, versus **0.490909** for motion. These failures prevent a blanket claim of improvement and justify further modeling and outage calibration.

These figures are properties of a simplified generator, not meteorological skill claims. There are no confidence intervals or first-flash lead-time results. Full scores, coverage counts and scope are in [data/evaluation.json](data/evaluation.json), with a [model card](data/MODEL_CARD.md). Per-replay FSS uses a two-pixel-radius disk; it is not a common physical scale across the two geographic grids.

## Latency and feasibility limits

The saved benchmark measured direct computation plus JSON-grid construction, excluding HTTP transfer and SQLite persistence. In that run, observed horizons took **2.897–6.232 seconds**, and synthetic horizons **0.139–0.280 seconds**. Browser testing was active during part of this benchmark, so resource contention is part of those observations. Two separate direct +15-minute observed runs after the numerical change took 1.736 s cold and 1.396 s warm. These are individual local measurements, not p95 estimates or service guarantees.

Only the small bundled dataset was tested. A full radar-volume network, satellite preprocessing, a larger neural network and concurrent operators would require separate measurements.

## Evidence beyond code

The research notes distinguish primary source retrieval, indexed evidence, direct endpoint checks and unresolved access. The official SIH entry was checked against the two supplied documents. Prior art was checked against ministry/agency descriptions and original model papers. The data atlas includes successful anonymous sample access and failed or restricted Indian endpoints. No stakeholder interviews, credentialed Indian observations, field drills, delivery tests or mortality-impact study were completed.

The next scientific gate is matched Indian observations with direct lightning coverage labels, followed by frozen baselines, calibration and independent event/region tests. The next operational gate is an authorized shadow pilot and verified action protocols. Neither gate can be replaced by passing this software test suite.

## Website, public preview and offline verification, 30 September 2026

The forecasting mathematics and trained weights were not changed in this iteration. The backend change exposes three additional reviewed Markdown documents through the existing explicit whitelist. The frontend adds an overview, plain-language pipeline guide, public sample preview, linkable navigation, responsive controls and a production PWA shell.

Verified results:

- `python -m unittest discover -s tests -v`: **17 tests passed**, 14.941 seconds on this run.
- `npm run test:browser`: **4 tests passed**, 37.5 seconds. This includes the existing forecast/source-failure/real-radar workflow and two new website/offline journeys.
- The two portal journeys passed again after the final copy, research links, sidebar and connection-error changes, 11.7 seconds.
- `npm run build` passed. Final JavaScript bundle: 304.46 kB, 94.91 kB gzip. CSS: 60.96 kB, 8.96 kB gzip. These are bundle sizes, not measured page-load times.
- Chromium `Page.getAppManifest` returned no manifest errors, and `Page.getInstallabilityErrors` returned an empty list. This is a browser check, not an app-store release or real Android/iOS installation test.
- Keyboard Tab reached the skip link and Enter moved focus to main content. Results and document endpoint checks are saved in `artifacts/web-delivery-check.json`.
- The three new document endpoints returned HTTP 200. Root and named views loaded through URL hashes; back navigation and deep-link reload worked.
- Opening the overview, guide and unsaved public preview did not request a forecast. Selecting a sample place updated the preview.
- A saved simulation receipt appeared in the public view with its historical issue time. It survived a forced offline reload; the app showed an offline message. The guide remained available offline.
- Opening the officer workbench while offline showed a service error rather than an old forecast. Reconnecting and retrying recovered. The service-worker cache contained no `/api/` resources.
- Removing the saved sample persisted across reload. The view returned to its explicitly unavailable live-information state.
- There was no document-level horizontal overflow at 375, 768 or 1024 px or the 812×375 landscape check. The 375 px workbench also passed at a 24 px root font size. A tested select control was at least 44 px high. Reduced-motion mode was exercised.

Visual inspection covered the overview, revised officer workbench, public phone layout and pipeline guide. Screenshots are in `artifacts/overview-desktop.png`, `artifacts/workbench-desktop.png`, `artifacts/public-mobile.png`, `artifacts/officer-mobile-updated.png` and `artifacts/flow-desktop.png`. These checks are not a complete WCAG audit or screen-reader certification.

The first expanded browser run exposed an immediate row-count assertion racing the asynchronous receipt load. The assertion now waits for a visible row, and the application separately shows a record-loading state with a working endpoint retry. Subsequent runs passed.

The offline implementation is deliberately limited. Static application files are precached by build version. `/api/` and `/research/` remain network requests. The explicitly saved public sample uses browser localStorage and retains its historical identity. Live warnings, expiry/cancellation propagation, push notifications, authentication and Jev integration are not implemented. Private browsing, storage eviction and unsupported browsers can remove or prevent cached availability; the first successful cache installation is required.

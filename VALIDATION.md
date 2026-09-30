# Validation record

This record distinguishes software checks from real-weather and physical-device validation. The current delivery extends the original research prototype; the older benchmark results below retain their original scope.

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

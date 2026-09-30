# Regional prediction features: evidence and implementation limits

Verified 30 September 2026. Scope: lightning, monsoon conditioning, onset timing, public verification, benchmark release and citizen observations for the NCR research prototype. Official publications, original research papers and provider repositories are the sources below. Recommendations are our design inferences, not reported results from this project.

The useful distinction is a locally evaluated prediction model with visible evidence, honest gaps and a controlled feedback loop. The individual ideas have prior art. They become a credible contribution when their combined benefit is measured on Indian observations.

## Claims we can defend

| Proposal | Evidence check | Defensible project wording |
|---|---|---|
| Predict lightning before it happens | Damini already provides advance location warnings, and LightningCast is established research. | Evaluate an NCR model for calibrated lightning probability over a defined area and next 30 minutes, including a separate first-lightning task. |
| Monsoon-aware calibration | Monsoon phase and seasonal radar calibration have established scientific foundations. Local skill improvement is untested here. | Compare one pooled calibrator with phase-conditioned calibration on independent storm events. |
| Tell people when rain starts | Start/end-time products already exist. A single exact minute can exaggerate available precision. | Show onset intervals, horizon and probability, with data age and coverage. |
| Publish public scorecards | IMD publishes district nowcast verification and has block forecast verification research. | Publish reproducible monthly results for our own declared task; compare only compatible, archived forecasts. |
| Release an Indian benchmark | IndiaWeatherBench already exists for regional forecasting. No search can establish that every possible Indian matched corpus is absent. | Release a documented NCR nowcasting benchmark when data coverage and redistribution rights are established. |
| Learn from citizen confirmation | Crowdsourced weather observations already support research; majority agreement alone does not make a measurement true. | Admit reviewed citizen reports as separately identified supporting labels and measure their added value. |

## Lightning: a separate prediction target

The official Ministry of Earth Sciences description says Damini monitors nearby lightning and gives location warnings valid for the next 40 minutes, alongside 20 km and 40 km proximity notifications. Therefore, “Damini only tells where lightning is” is inaccurate. This description does not establish Damini's model architecture, calibrated block probabilities or a numerical benchmark against our model. [PIB, 6 April 2022](https://www.pib.gov.in/PressReleasePage.aspx?PRID=1813993&lang=2&reg=48).

LightningCast is a published satellite CNN for next-hour lightning guidance. Its evaluation includes POD, FAR, CSI and probability reliability, and distinguishes developing from mature convection in training. It establishes useful prior art; its results are not transferable to INSAT/NCR without new evaluation. [Cintineo et al., 2022, original paper](https://journals.ametsoc.org/view/journals/wefo/37/7/WAF-D-22-0019.1.xml). NOAA's demonstration plan describes GOES ABI inputs and future GLM detections, so its labels are not interchangeable with an Indian ground network's stroke detections. [NOAA demonstration plan](https://goes-r.noaa.gov/users/docs/pg-activities/HWT-PG-2024-Demonstration-Plan.pdf).

The INCOIS-hosted MoES catalogue is a discovery record for an **IITM/Earth Networks** dataset. Its abstract specifies January–December 2019, India, stroke type, amplitude, height and coordinates. The same page also says ongoing/till date; that does not prove a complete current archive. It links an IITM LAS service, names the distributor and leaves the distribution format unknown. Raw NCR event files, usable event timestamps, outages, detection efficiency and redistribution rights have not been obtained by this project. [Official metadata](https://incois.gov.in/essdp/ViewMetadata?fileid=05f2bab9-054f-45cf-b77d-1eaf089252ff).

Historical fatality figures support the importance of the problem without implying lives already saved: NCRB figures reported by the Ministry of Home Affairs are **2,357 in 2018, 2,876 in 2019 and 2,862 in 2020**. [Parliamentary answer, 27 July 2022, page 2](https://www.mha.gov.in/MHA1/Par2017/pdfs/par2022-pdfs/RS27072022/1197.pdf). The Sixteenth Finance Commission also cites **2,887 lightning deaths in 2022**, out of 8,060 deaths attributed to natural hazards. These are historical administrative figures, not a claim about the latest annual count or deaths preventable by this model. [Finance Commission report, paragraph 11.69](https://www.indiabudget.gov.in/doc/16fcvol1.pdf).

Implementation requirements:

- Define the target as a detected event in a versioned polygon or radius during `(issue_time, issue_time + 30 minutes]`. State whether the target is any lightning, cloud-to-ground strokes or flashes. Deduplicate/group strokes before calling them flashes.
- Treat **first detected lightning after a specified observed quiet period** as a different target from lightning occurring in an already active storm. Publish results separately.
- A zero-event label is valid only where the relevant network was observing throughout the target interval. Network gaps are unknown outcomes, never negatives.
- Keep radar growth, echo tops, satellite cooling, CAPE, moisture and previous lightning as predictors, with their issue-time availability and masks. CAPE alone is not a lightning threshold.
- Do not call the maximum pixel probability the probability of an event anywhere in an administrative block without training or validating that aggregation.
- An IITM collaboration pitch can request historical events, network quality metadata and joint validation. It must not claim an existing partnership or that we outperform Damini.

## Monsoon phase and seasonal Z–R corrections

Rajeevan, Gadgil and Bhate define active/break spells for July–August using normalized rainfall anomalies over the monsoon core zone: above +1 or below −1 for at least three consecutive days. This is a regional, multi-day definition, not “it rained in Delhi today.” IITM documents the same procedure. [Original paper](https://repository.ias.ac.in/15911/), [IITM definition](https://tropmet.res.in/erpas/files/active_break_selection.php).

Our implementation should retain the phase's source, definition, valid period and availability time. A retrospective three-day classification can use days that were still in the future at forecast issuance. Use only a phase already known at issue time, or explicitly label the analysis retrospective. Keep unknown/transition cases; do not guess active/break from calendar month. Onset and withdrawal are separate seasonal diagnostics. “Global models are phase-blind” is an unsupported generalization: a model can represent circulation without receiving a named phase variable.

Fit a pooled probability calibrator on calibration events first. Fit phase-specific corrections only when each phase has enough positive and negative independent events; otherwise fall back to the pooled fit. Compare held-out Brier score, reliability and event discrimination with uncertainty by storm/day. Separate evaluation from both training and calibration. More groups can reduce sample sizes and worsen calibration; improvement is a hypothesis.

The Delhi study compares Marshall–Palmer, WSR-88D and Rosenfeld relationships using 2019 radar/gauge events across four seasons. Marshall–Palmer gave the best correlation in monsoon/post-monsoon; Rosenfeld gave the best correlation in winter/pre-monsoon. Crucially, Marshall–Palmer still had the lowest RMSE across seasons/intensities. Selecting solely by correlation would misread the paper. The publisher's indexed abstract and introduction were accessible; direct page retrieval returned HTTP 403, and the full methods were not examined here. [Sharma et al., 2025, DOI 10.1016/j.pce.2025.104182](https://www.sciencedirect.com/science/article/abs/pii/S1474706525003328).

For local fitting, convert `dBZ` to linear reflectivity `Z = 10^(dBZ / 10)` before using `Z = a R^b`; `R` is mm/hour. Match radar accumulation windows to gauge windows, exclude invalid/clutter-contaminated scans and fit positive rain pairs with event-separated validation. Zero rain remains useful for detection evaluation but cannot be inserted into a logarithmic fit. Do not fit physical Z–R parameters from RainViewer colour tiles or airport present-weather codes. [wradlib conversion workflow](https://docs.wradlib.org/en/2.0.0/notebooks/basics/wradlib_workflow.html).

A reproducible local fit and multi-year out-of-sample comparison could contribute useful evidence. It is not yet a new scientific discovery, and the cited Delhi paper already establishes regional prior work.

## Warm rain and andhi need distinct checks

An original Indian study reports difficulties in satellite rainfall estimation over the Western Ghats, including warm rain and terrain-related errors. Its geography is not NCR, so it supports a failure-mode check rather than a numerical claim about Delhi. [2019 study](https://pmc.ncbi.nlm.nih.gov/articles/PMC6821882/).

Design implication: do not discard all warm cloud tops as dry or all non-lightning clouds as non-raining. Retain radar/gauge evidence, moisture and missing-channel masks. Evaluate shallow/warm-top cases separately when reliable labels exist. Satellite-only status should describe the evidence limitation, not attach an arbitrary confidence percentage.

Delhi's May–June 2018 events have already been studied with dual-polarization radar and GNSS water vapour. Polarimetric information helped distinguish hydrometeor properties and non-meteorological returns. [Singh et al., MAUSAM 2021](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/3543). A separate Delhi andhi case study used satellite, radar, ground observations and WRF together. [Original 2021 study](https://www.sciencedirect.com/science/article/pii/S2212095521000559).

Design implication: a dust/gust-front warning is not a rain warning. Useful additional fields include surface wind/gust, visibility and present-weather codes, radar velocity and polarimetric quality, plus satellite aerosol/dust signatures when available. Radar reflectivity alone cannot safely classify every echo as rain. Add a distinct dust/strong-wind task only with corresponding labelled observations; meanwhile expose the unassessed hazard explicitly.

## Onset-time prediction and evidence cards

AccuWeather's own API documents precipitation start/stop times and minute forecasts. Timing UX therefore has prior art; the opportunity is to make local predictions testable and their limits understandable. Its existence does not prove the accuracy of any provider in NCR. [AccuWeather API documentation](https://developer.accuweather.com/documentation/overview).

Discrete-time survival modelling supplies a compact method for event timing. With conditional hazards `h[k]`, survival through bin `k` is `S[k] = product(1 - h[j])`; event probability in a bin is `S[k-1] * h[k]`. The published method handles censored observations; adapting it to weather is our proposed engineering application, not a weather result reported by that paper. [Gensheimer and Narasimhan, 2019](https://peerj.com/articles/6257.pdf).

Implementation requirements:

- Define onset using a measurable rain threshold and a prior dry interval; separate ongoing rain from new onset. Use a time bin supported by label cadence.
- Preserve probability of **no onset within the horizon**. Do not report a median arrival time when cumulative onset probability never reaches 50%.
- If follow-up stops before the horizon, censor it at the last observed interval. Missing data cannot become “no rain.”
- A rain-onset head does not predict cessation, heavy-rain duration or an end time. Those require subsequent intensity trajectories or another defined task. Do not manufacture “heavy till 16:10.”
- Evidence cards should show issue time, forecast validity, observed-data age, coverage, model version, probability calibration status and the genuine observed/forecast track distinction. A model explanation describes supporting measurements; it is not proof of physical causation.
- Evaluate event probability and timing together. Report misses and no-event cases alongside onset MAE for observed events; otherwise timing can look good merely by excluding failures.

## Monthly public verification

IMD's 2023 annual report publishes district POD, FAR, CSI and ETS for three-hour nowcasts during FDP STORM. It describes verification using lightning observations and a two-detection occurrence criterion within the district/validity interval. IMD's forecasting SOP calls for monthly internal verification. Neither source proves a continuously available public block-level 30-minute scorecard, but both contradict “IMD does not verify nowcasts.” [Annual report 2023, printed page 92](https://mausam.imd.gov.in/imd_latest/contents/ar2023.pdf), [Forecasting SOP, section 9.3.9](https://mausam.imd.gov.in/imd_latest/contents/pdf/forecasting_sop.pdf).

Published IMD work also evaluates block forecasts for monsoon 2014. This is a different horizon/product from our proposed 30-minute nowcast and must not be used as a direct scoreboard opponent. [MAUSAM, 2017](https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/406).

Our scorecard should include raw contingency counts, POD, false-alarm **ratio**, CSI, Brier score, reliability-bin sample counts, observation coverage, excluded cases and event-bootstrap intervals. Undefined denominators should be `null`, with an explanation. FAR is not the same metric as false-positive rate. Scores depend on threshold and event frequency, making unmatched comparisons misleading. [Meteorological verification guidance](https://www.cawcr.gov.au/projects/verification/Mason/IntegratedVerificationProcedures.pdf).

An IMD comparison requires actual archived issued bulletins, their geometry, issue/valid times and documented mapping to the same event definition. A district three-hour bulletin cannot be silently treated as a block 30-minute prediction. Where matching is impossible, mark the comparator unavailable. Start with persistence, advection and the pooled model on the identical evaluation set. Publish low-sample months as low-sample months rather than hiding them.

## Benchmark release and data rights

IndiaWeatherBench already provides regional Indian forecasting code and describes IMDAA data covering 2000–2019 at six-hour intervals. Its repository declares CC BY-NC-SA 4.0 for the data. It is not a matched radar/INSAT/lightning/gauge NCR nowcasting corpus, but it defeats the broad claim “India has no open weather benchmark.” [Authors' repository](https://github.com/tung-nd/IndiaWeatherBench), [original paper](https://arxiv.org/abs/2509.00653).

SEVIR is established prior art for a matched satellite/radar/lightning corpus outside India. Its maintainer's dataset metadata states no restrictions on data use. It can help test architecture and loaders, but cannot establish Indian skill. [SEVIR maintainer metadata](https://github.com/MIT-AI-Accelerator/eie-sevir/blob/master/sevir.yaml).

MOSDAC's data guidelines explicitly restrict redistribution of downloaded products unless covered by agreement, while allowing value-added products. Download permission must not be equated with permission to republish raw INSAT files. The guidelines also distinguish general-user and approved near-real-time access. Verify the applicable product agreement and newer terms before release; labelling a raw crop “derived” is not sufficient evidence of permission. [MOSDAC guidelines, sections 3 and 4](https://www.mosdac.gov.in/look/DOCS/mosdac-data-guidelines_english.pdf), [current provider FAQ](https://www.mosdac.gov.in/faq-page).

Release manifest/schema/preprocessing recipes first. Each artifact needs source identifier, version, checksum, licence/permission evidence, acquisition/availability time, spatial support, measurement units and missing-data rules. Keep entire storms and overlapping windows in one split; separate training, calibration and untouched testing. Maintain independent gauges/labels for final evaluation. Export raw files only when that artifact's rights permit redistribution; publish reconstruction instructions otherwise. A manifest is not evidence that a matched corpus has already been acquired.

## Citizen reports and controlled retraining

NOAA's mPING demonstrates that public observations can support radar/forecast research. Its FAQ treats reports as less trusted than trained observers and says rainfall intensity cannot reliably be estimated by eye. Its researchers also document sampling biases that do not disappear simply by adding users. [mPING FAQ](https://mping.nssl.noaa.gov/faq.php), [NSSL research review](https://www.nssl.noaa.gov/about/events/review2015/science/files/Elmore_NSSLReview2015_mPING.pdf). An original evaluation found citizen reports useful for evaluating rain/snow classification, which supports collecting them without claiming perfect truth. [Research paper](https://repository.library.noaa.gov/view/noaa/32175/noaa_32175_DS1.pdf).

Recommended flow:

1. Ask a neutral question: **“What is happening at your location now?”** Offer rain / no rain / not sure and optional hail, dust or strong wind. Avoid telling users the expected answer first. Also sample predicted-dry and uncertain areas so missed events can be discovered.
2. Store observation time separately from receipt time, coarse location and accuracy, consent, prompt/forecast ID if applicable and an idempotency key. A device identifier is not proof of an independent person.
3. Deduplicate retries, limit repeated reports and aggregate only compatible locations/times. Repeated reports from one place are correlated, not many independent gauges.
4. Show agreement and sample counts as citizen evidence. Majority “yes” is a **candidate supporting label**, not automatic truth for an entire block, a rain amount, or a lightning event.
5. Review consistency with available observations, retain disagreements and mark unresolved evidence unknown. Preserve the report source and any quality weight; do not silently merge it with instrument truth.
6. Build a versioned candidate dataset after review. Retrain offline, evaluate against independent held-out observations and require model admission before deployment. Keep the prior model available for rollback.

Do not send people outdoors to confirm severe weather. The app can accept safely observed reports without requiring photos, exact home locations or lightning verification. A missed response says nothing about the weather. Automatic daily training or more votes cannot guarantee daily accuracy gains.

## What remains to demonstrate

The present source snapshots and executable methods do not establish a reliable NCR lightning model, a calibrated onset interval, improved seasonal accuracy or an open matched Indian corpus. These need time-aligned raw sensor data, coverage metadata, sufficient storms and independent tests. The feature design should expose those states directly while enabling collection, analysis, review and reproducible evaluation now.

# Model research and a defensible training plan for SIH26072

Research date: 29 September 2026. This is a design and evidence review, not a claim that an India operational forecast model has been trained. Numerical architecture choices below are proposed pilot settings unless explicitly attributed to a publication. The supplied analysis documents are project context; their suggested model scores, thresholds and data availability are not independent evidence.

## The target must be defined before choosing the network

The practical question is: **Will lightning occur close enough to this location, soon enough that someone must act?** A second question is whether a convective system is forming, moving, intensifying or weakening. These require related but different labels.

| Product | What a valid label measures | What cannot substitute for it |
|---|---|---|
| Total-lightning occurrence | An observed intracloud or cloud-to-ground flash, with a declared sensor, radius and future time window | Cold cloud tops, high CAPE, rain intensity or a generated risk score |
| Cloud-to-ground lightning | A ground network's verified CG event classification and coverage | GLM total lightning alone |
| Radar convective proxy | A documented radar-derived criterion, such as an echo threshold/height and object area | A universal definition of thunderstorm or lightning |
| Precipitation nowcast | Future radar-derived precipitation rate, or a clearly named VIL/reflectivity target | An electrical hazard probability |
| Convective initiation | The first new object/electrification event under a declared previous-absence rule | A mature storm advecting into the area |

GOES GLM labels measure observed total lightning, not only strikes reaching the ground. The original LightningCast learns next-hour GLM occurrence from ABI imagery. This is directly relevant prior art for the lightning objective, while rain nowcasters are relevant to transport and storm evolution. [LightningCast paper, NOAA repository](https://repository.library.noaa.gov/view/noaa/52868), [NSSL lightning research](https://www.nssl.noaa.gov/research/lightning/)

## Prior art that changes the proposal

| Work | Verified contribution and target | Practical use here | Limitation for this problem |
|---|---|---|---|
| Pysteps, 2019 | Open source probabilistic **precipitation** nowcasting; optical flow, semi-Lagrangian advection, multiscale stochastic evolution | Establish persistence, deterministic advection and an ensemble benchmark before a new model | Straight extrapolation cannot explain initiation; growth, decay and changes of motion violate its assumptions. [Paper](https://gmd.copernicus.org/articles/12/4185/2019/), [official code](https://github.com/pySTEPS/pysteps) |
| ConvLSTM, 2015 | Convolutions inside recurrent input/state transitions model spatial sequences | A tractable spatial sequence baseline on aligned image histories | The original task is radar precipitation. Architecture availability does not establish lightning skill or India transfer. [Original NeurIPS paper](https://papers.nips.cc/paper/2015/hash/07563a3fe3bbe7e3ba84431ad9d055af-Abstract.html) |
| DGMR, 2021 | Generative radar precipitation ensembles; evaluates spatial structure and probabilistic forecast quality | Learn why sharp images alone are insufficient, and evaluate ensembles over spatial aggregates | Heavy training/data burden; UK/US rain results are not lightning validation. Its paper also uses missing-value masks and held-out years. [Nature paper](https://www.nature.com/articles/s41586-021-03854-z) |
| NowcastNet, 2023 | Combines an advection-based deterministic evolution network and a conditional stochastic generator for extreme precipitation, reporting lead times up to three hours | A strong future rain baseline; evidence that physics plus neural correction is established prior art | Do not present its precipitation performance as a three-hour lightning guarantee. The original article points to Code Ocean inference assets/weights and notes restrictions on China data. [Nature paper and asset links](https://www.nature.com/articles/s41586-023-06184-4), [author-linked Code Ocean capsule](https://doi.org/10.24433/CO.0832447.v1) |
| Earthformer, 2022 | Cuboid attention for spatiotemporal forecasting | Candidate when longer histories and a larger dataset justify attention | Its official SEVIR precipitation setup predicts 12 future VIL frames from 13 context frames, on 384 × 384 grids. VIL is not a lightning label. [Paper](https://arxiv.org/abs/2207.05833), [official implementation](https://github.com/amazon-science/earth-forecasting-transformer) |
| LightningCast, 2022 | Satellite-based probability of lightning in a 0–60 minute window | Closest lightning baseline concept: direct event target, satellite-only operation and probability maps | GOES-trained weights and ABI channels cannot be relabeled as an INSAT-trained India model. [NOAA paper record](https://repository.library.noaa.gov/view/noaa/52868), [official software](https://cimss.ssec.wisc.edu/csppgeo/lightningcast.html) |
| LightningCast radar extension, 2026 journal issue | Adds radar reflectivity to a satellite lightning model | A mandatory comparator for claims about radar + satellite lightning fusion | Already published prior art, not an undiscovered feature. The official product page lists the work under 2025, while the NOAA journal record identifies the 2026 issue. [NOAA bibliographic record](https://repository.library.noaa.gov/view/noaa/75509), [product page](https://cimss.ssec.wisc.edu/probsevere/lc/) |
| NOAA MRMS / ProbSevere | Operational multi-radar/multi-sensor integration; ProbSevere uses satellite, radar, lightning, environmental data and storm objects | Product/architecture comparator for sensor fusion and forecaster workflows | Combining four modalities, tracking cells or drawing probability polygons is not sufficient novelty. [MRMS official description](https://www.nssl.noaa.gov/projects/mrms/), [NOAA HWT 2022 plan](https://hwt.nssl.noaa.gov/docs/HWT%202022%20Spring.pdf) |

The 2025 NOAA testbed plan explicitly describes LightningCast using ABI and optionally MRMS. A 2025 developer case study reports better performance under thick ice/anvils and in some nocturnal convection with the radar extension. Treat that case study as evidence of failure modes and development direction, not a universal improvement percentage. [NOAA 2025 demonstration plan](https://www.goes-r.gov/users/docs/pg-activities/HWT-PG-2025-Demonstration-Plan.pdf), [CIMSS case study, 14 March 2025](https://cimss.ssec.wisc.edu/satellite-blog/archives/63521)

## What can credibly stand out

These are **testable differentiation hypotheses**, not claims of a world first.

| Hypothesis | Why it matters in the use case | Evidence needed before claiming success |
|---|---|---|
| The forecast remains useful during local radar outages | A district cannot wait for every observation stream to recover | Compare full inputs, radar removal, lightning removal and realistic time delays on the same held-out storms; report skill and coverage |
| Every forecast can be reconstructed from the data actually received by issue time | A good retrospective model can fail when data arrive late | Immutable input manifest, observation and receipt timestamps, model checksum; replay the identical issue twice and obtain identical results |
| First-flash performance is measured separately | Recent lightning is an easy cue; first-flash warning is harder and operationally useful | Evaluate an initiation subset with no previous local flashes, report misses and lead-time distribution |
| Uncertainty changes the recommendation and is explained | A probability without source quality or calibration context encourages overconfidence | Show reliability plots, historical support and explicit unavailable/degraded states; measure false-alert time and useful lead time |
| The model learns storm growth beyond motion | Moving yesterday's echo pattern does not predict new electrification | Beat calibrated recent-lightning and advection baselines on initiation/growth cases without losing overall skill |
| District users can inspect a missed or false alert | Deployment improvement needs accountable failures | Provide a case replay with observed future events, forecast, data delays and model version; keep those observations out of inference |

Missingness masks and elapsed-time inputs are established ideas: GRU-D explicitly represents both, although its evidence is from clinical/synthetic time series rather than meteorological fields. Applying them to this project is an engineering hypothesis requiring weather-specific validation. [GRU-D original paper](https://arxiv.org/abs/1606.01865)

## Recommended forecast contract

Use **one pilot region and one clearly specified product** first. Suggested initial output: probability that the selected lightning network observes at least one flash within 5 km of a grid centre during the next 15, 30 or 60 minutes. These radii and horizons are experimental settings, not IMD-approved warning rules. Include the exact label definition in the API and map legend.

For issue time `t`, horizon `h`, location `x`, radius `r`, define:

```text
Y(t, x, h, r) = 1 if any qualifying observed flash exists with
                 t < flash_time <= t + h and distance(flash, x) <= r
             = 0 if the entire label interval/region has valid coverage
                 and no qualifying flash exists
             = unknown otherwise
```

Do not turn missing lightning coverage into zero flashes. Preserve event/flash terminology: a provider's pulses, strokes, flashes, flash centres and flash-extent-density products differ. Convert or aggregate only using the provider's documented definition. A distance computed in longitude degrees is not a kilometre radius; use a suitable projected grid or geodesic distance. Match the spatial label dilation in all models and baselines.

Use a separately reported **initiation cohort**: examples with valid prior coverage and no flash within a proposed 20 km neighbourhood over the previous 30 minutes. The exact rule should be frozen before testing and revised with meteorologists. This is a test subset, not an assertion that all such first local flashes are newly born storms: a storm can advect from outside the neighbourhood.

For richer time-to-event output, predict conditional hazards `q_k` of the first future flash in each five-minute bin, conditioned on no earlier future flash and the issue-time inputs. Then `P(first flash by bin K) = 1 - product(1 - q_k)` is monotone by construction. These are conditional hazards, so this identity does **not** assume independent lightning events. Censor training at the first missing coverage interval. Keep a simple direct 30-minute logistic baseline to detect errors in this more complex formulation.

## Spatial architecture for the next research stage

The recommended research model is a small multimodal spatial encoder with a ConvLSTM temporal core, an advection branch and a direct lightning head. This is a proposed architecture, not an experimentally selected winner.

1. **Observation contract.** For each source retain observation start/end, received time, unit, grid/projection, valid-pixel mask, quality flags, provenance and source identifier. NWP needs model initialization, release/availability time and forecast valid time.
2. **Issue-time snapshot.** Select only observations received no later than `t`. Build a causal history using prior samples; never interpolate with a future observation. Keep values, validity and age as separate channels. If historic receipt times are absent, declare the evaluation idealized and simulate a documented delay distribution.
3. **Radar mosaic.** Quality/range/beam-height-aware compositing retains contributing radar identifiers and coverage. Do not average radial velocities from different viewing directions as if they were Cartesian wind. Avoid simply taking a maximum reflectivity without clutter/attenuation checks.
4. **Modality encoders.** Small convolutional encoders for radar, IR/WV satellite, lightning history and coarse atmospheric context. Pass mask/age channels through each; exclude a missing encoder from fusion instead of encoding missing data as physically meaningful zero.
5. **Temporal core.** Fuse at reduced spatial resolution into a ConvLSTM. A basic concatenation + convolution is the first experiment; attention/gating earns its complexity only if ablations show benefit. Train source dropout, contiguous spatial outages and latency shifts using plausible patterns.
6. **Two forecast paths.** Radar optical flow provides a transport baseline and motion features. A learned residual predicts growth/decay for the radar proxy. A distinct lightning head uses the fused temporal state; it can activate when there was no previous lightning. There is no assumed physical conservation law for flash counts.
7. **Calibration and quality.** Calibrate on a separate validation set; expose model spread separately from data completeness and calibration status. An ensemble of three independently trained small models is a proposed uncertainty experiment, not a calibrated confidence interval by itself.
8. **Decision layer.** Produce probabilities and an advisory proposal with evidence, timestamp and expiry. Thresholds belong to an explicit, versioned policy. Keep probability of a hazard separate from societal impact, which additionally depends on exposure and vulnerability.

Start with six frames over the preceding 50 minutes on a 2 km projected grid. A 128 × 128 tile covers 256 km per side; a 16-pixel halo leaves a 192 km central forecast region. These are compute-conscious pilot choices. A 1 km output grid does not establish 1 km effective forecast accuracy. At 24 float32 channels, six 128 × 128 input frames occupy 9 MiB before masks, targets, model activations and optimizer state. Benchmark actual training memory and latency; do not promise GPU-hours before a trial.

## Training ladder and data fit

**Stage 0 — system verification.** Synthetic moving/growing storms exercise timestamps, regridding, outages, alert deduplication and replay. Train/test synthetic scenarios can prove code behavior. They cannot establish real-weather skill, India transfer or lives saved.

**Stage 1 — real public benchmark.** SEVIR aligns satellite channels, radar VIL and GLM lightning. Its paper describes more than 10,000 four-hour weather events spanning 384 × 384 km; the original benchmark repository documents roughly 1 TB for the complete download and a chronological June 2019 cutoff. Select a small catalogue subset and all required modalities instead of downloading the archive blindly. Use the official lightning loader/format documentation before constructing labels. [SEVIR original paper](https://proceedings.neurips.cc/paper/2020/hash/fa78a16157fed00d7a80515818432169-Abstract.html), [benchmark repository](https://github.com/MIT-AI-Accelerator/neurips-2020-sevir), [data utilities](https://github.com/MIT-AI-Accelerator/eie-sevir)

SEVIR is suitable for learning a US-domain multimodal pipeline, not for claiming Indian validation. Its five data types do not contain a complete NWP feature cube. Either align a separate forecast archive causally or mark NWP absent. Also, SEVIR's VIL must not be relabeled dBZ, and its satellite channel set is not identical to LightningCast's input set. Its curated storm-event distribution is unsuitable for calibrating a general always-on alarm product without background/no-event sampling and prevalence checks.

**Stage 2 — India adaptation.** Acquire matched IMD radar volumes/products, INSAT observations, a licensed lightning archive with sensor health/coverage, and issue-time NWP forecast archives. Train/validate across seasons and test an unseen region or year. If only satellite data are available, develop and explicitly label a satellite-only model. Reanalysis can support exploratory atmospheric relationships; it cannot be treated as an operational forecast that was available at the historical issue time.

**Stage 3 — prospective shadow operation.** Run without autonomous public warning issuance. Measure source latency, missing coverage, time-to-decision, calibration drift and case-based meteorologist feedback. Promote only a model that beats the agreed baseline and satisfies operational requirements on relevant Indian events.

## Evaluation that can survive questions from judges

Train, model-selection validation, calibration validation and final test periods must be separate. Group windows from the same storm/day; overlapping spatial crops and nearby issue times cannot cross splits. Apply a boundary exclusion gap covering the input lookback plus the longest target horizon so shared observations cannot leak across adjacent splits. Fit scalers, climatology, sampling weights and thresholds using the appropriate training/validation split only. Keep the final test set untouched until the comparison is frozen. Leakage is a documented cause of inflated scientific ML claims. [Kapoor and Narayanan, 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10499856/)

Compare at least: seasonal/regional climatology, calibrated recent-lightning occurrence, persistence of the radar proxy, optical-flow transport, a transparent logistic/tabular model, the spatial single-modality model and the fused model. An advection model for rain is not by itself a calibrated lightning baseline; fit an explicit mapping or score it only for its own radar target.

For binary lightning, report by horizon and radius:

- Brier score and Brier skill against held-out climatology; score only observed labels and disclose the valid count.
- Reliability diagram with bin counts and uncertainty, plus precision-recall AUC for rare events.
- POD `TP/(TP+FN)`, FAR `FP/(TP+FP)` and CSI `TP/(TP+FP+FN)` at validation-selected thresholds. FAR here is **false alarm ratio**, not false positive rate `FP/(FP+TN)`.
- First-flash warning lead-time distribution, fraction of events warned before onset, false-alert hours and alert toggles. Show misses, not only median lead time among successful warnings.
- Spatial neighbourhood skill at declared scales; Fractions Skill Score can complement point verification but must not hide errors by enlarging the neighbourhood after seeing results.
- Paired storm/day bootstrap intervals for differences. Millions of adjacent pixels do not constitute millions of independent storms.

Probability calibration and discrimination are separate properties. Temperature scaling is a useful low-parameter candidate, not a guarantee that a weather model remains calibrated under shift. Fit calibration using data separate from model fitting and preserve cumulative-horizon monotonicity. Reliability means that, for example, events assigned 30% probability occur about 30% of the time in a comparable cohort; it does not mean the model is 30% confident in itself. [Guo et al., original calibration paper](https://proceedings.mlr.press/v70/guo17a.html), [Met Office reliability explanation](https://www.metoffice.gov.uk/research/climate/seasonal-to-decadal/gpc-outlooks/user-guide/interpret-reliability)

## Known failures and required stress tests

| Failure | Consequence | Required treatment/test |
|---|---|---|
| Thick anvils hide developing convection in satellite imagery | First flashes missed despite apparently stable cold cloud | Radar-supported and satellite-only cohorts; retain the failure cases |
| Tall cold non-electrifying clouds | Excess lightning alarms | Label-based calibration; never equate low IR temperature with lightning |
| Night/day and seasonal changes | A model trained on daytime warm-season imagery degrades | Day/night and season-stratified scorecards; visible-channel missing/illumination state |
| Satellite parallax and radar beam geometry | Hazard polygon displaced from true ground location | Apply documented correction when possible and retain spatial uncertainty; no invented precise strike point |
| Radar clutter, attenuation or outages | False core or missing storm | QC and coverage masks; sensor-specific fault injection |
| Lightning network sensitivity changes | False negative labels and distribution shift | Network metadata and coverage masks; report target as observed-network occurrence |
| NWP downloaded after its nominal initialization time | Retrospective leakage | Availability timestamp and backtest cutoffs |
| Severe weather causes network/data loss | Missingness differs from random training dropout | Contiguous outage/latency scenarios and real missing-data analysis |
| Storm splitting, merging or motion change | Misleading single-track ETA | Maintain parent/child lineage or mark track uncertain; use probabilistic arrival windows |
| Domain transfer from US sensors to India | Overconfident out-of-domain output | Local calibration and held-out India evaluation; unknown/OOD state where support is absent |

The first three satellite failures above are explicitly documented in the official LightningCast quick guide; the remaining mitigations are engineering requirements derived from the observation/forecast contract and must be validated. [CIMSS LightningCast quick guide](https://cimss.ssec.wisc.edu/probsevere/wp-content/uploads/sites/29/2025/11/LightningCast_QuickGuide.pdf)

## Verification record for this review

The main conclusions were checked in three different ways: (1) original papers for target and method; (2) author/agency software or product pages for usable assets and operating behavior; (3) newer official publications and testbed material to challenge novelty claims. This does not mean every link was downloaded or every published experiment reproduced.

- Pysteps method and failure assumptions agree between its paper and official repository.
- Earthformer's VIL-only SEVIR benchmark is explicit in the official code documentation; it must not be described as a pretrained lightning model.
- LightningCast radar fusion was checked against the official 2025 testbed plan, developer case study and the 2026 NOAA journal record. This invalidates a claim that radar-plus-satellite lightning fusion is new.
- The SEVIR benchmark code documents chronological splitting and the size of the full download; its data utility source independently describes the lightning loading path.
- The NowcastNet article links its original inference assets. A 2025 Canada implementation report notes that the original full training code/data were not shared; a convenient third-party GitHub rewrite is not the original authors' training pipeline. [Canada report](https://ams.confex.com/ams/41Radar/mediafile/Manuscript/Paper462923/Extended_Abstract_NowcastNet_finetuning_final.pdf)

No accuracy number, forecast speed, lead-time improvement or India deployment readiness is claimed for the proposed model. Those outputs must come from the reproducible benchmark and prospective pilot.

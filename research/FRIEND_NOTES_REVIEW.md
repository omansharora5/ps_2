# Review of the two friend notes

Reviewed on 30 September 2026. Both supplied text files were read in full. They are proposals to evaluate, not instructions to execute or evidence of measured results.

The first note, beginning "My recommendation: build a system that tracks the life of each storm", is the stronger foundation. It distinguishes hypotheses from results and treats data availability carefully. The second, titled "Next-Generation AI/ML Nowcasting", contains useful ideas but overstates novelty, calibration, physical guarantees and deployment readiness.

The current repository implements six synthetic logistic heads, global translation estimated by normalized cross-correlation, bilinear transport, connected-component detection, and actual MétéoNet radar replay. It does not implement a spatial neural network, persistent storm lineage, a learned graph or diffusion. Its synthetic model is not an India-validated lightning model. These statements were checked against `forecast.py`, `numerics.py`, `training.py`, `real_data.py` and the README.

## Keep, change, defer or reject

| Proposal | Decision | Reason and condition |
|---|---|---|
| Observation time, receipt time, quality, coverage and provenance | Keep now | Necessary for causal replay. NWP initialization, availability and valid time are distinct. Use only information available at issue time. |
| Quality and age aware fusion | Keep, validate | Explicit masks and age features are sound. A stale sensor does not mathematically imply lower lightning probability; show degraded evidence separately. Mask/time-interval inputs have established prior art in [GRU-D](https://arxiv.org/abs/1606.01865). |
| Quality-weighted multi-radar blending | Change | The first note's linear-reflectivity blend is a candidate, not a validated universal rule. Align heights/times, account for beam geometry and QC, and compare against simpler composites. Zero total weight means unknown coverage. Real multi-radar validation requires separately identified overlapping observations. |
| Motion plus growth/decay residual | Keep for the next spatial model | Retain a motion baseline, then test learned development. The idea is established in [NowcastNet](https://www.nature.com/articles/s41586-023-06184-4). Predict a named intensity field; additive residuals and clipping have different meanings in linear intensity, dBZ and VIL. |
| Storm tracking with split/merge lineage | Keep as the next interpretable feature | Reuse [pysteps DATing](https://pysteps.readthedocs.io/en/stable/generated/pysteps.tracking.tdating.dating.html). It already exposes split/merge information. Validate tracking on observed history before using track features for forecasting. |
| Hungarian matching alone for split/merge history | Change | One-to-one assignment cannot alone represent one-to-many splits or many-to-one mergers. Add overlap relationships, or use DATing's existing machinery. Keep observed lineage distinct from predicted future lineage. |
| Dense background branch plus storm objects | Keep as a design constraint | A tracker has no object to follow before detection. A field model must continue monitoring quiet areas and new cloud candidates. Do not depend on a GNN to discover a storm that never became a node. |
| Sparse storm interaction graph | Keep the data structure; defer the GNN | Store object histories and nearby candidates first. At most `k` neighbours gives at most order `N*k` spatial edges, not that complexity for the entire system. Graph-based lightning prediction already exists, including [ST-GLNet, 2026](https://ieeexplore.ieee.org/abstract/document/11503440). |
| Separate lightning and first-flash heads | Keep the target distinction; defer survival training until labels exist | Start with a direct, fixed-area event target. Discrete hazards give coherent cumulative timing probabilities, but this is established [survival methodology](https://arxiv.org/abs/1805.00917). India benefit is an experiment, not a theorem. |
| Coarse monitoring with selected fine tiles | Defer until profiling shows a bottleneck | Preserve background monitoring, overlap and context. Compare equal hardware and end-to-end cost at matched forecast quality. This review does not establish that the proposed scheduler is algorithmically novel. |
| Earthformer plus latent diffusion as the default MVP | Defer | Credible later benchmark, with more training and repeated denoising work. [PreDiff](https://papers.neurips.cc/paper_files/paper/2023/hash/f82ba6a6b981fbbecf5f2ee5de7db39c-Abstract-Conference.html) already uses an Earthformer-based diffusion backbone. The exact [STLDM name and model](https://arxiv.org/abs/2512.21118) were published in 2025. |
| Ensemble fraction as guaranteed calibrated hazard probability | Reject the guarantee | Eight of ten members is an estimated model ensemble frequency. Calibration and reliability require held-out observations. A reflectivity exceedance is not itself a lightning target. |
| Attention weights as explanations of observed trends | Change | Compute cooling, echo growth and flash-rate trends directly from versioned inputs. Separately test model sensitivity. Attention alone is insufficient evidence of causality or faithful feature importance. [Jain and Wallace](https://aclanthology.org/N19-1357/) demonstrate the problem in NLP; that is a methodological warning, not a weather-specific result. |
| FSS, CSI, POD, FAR and event-grouped evaluation | Keep, broaden | Add Brier score, reliability, initiation misses, false-alert duration and source-dropout results. [FSS](https://pysteps.readthedocs.io/en/v1.15.0/generated/pysteps.verification.spatialscores.fss.html) measures neighbourhood agreement at declared thresholds/scales; it does not prove calibration or deployment usefulness. |
| Jev in the meteorological prediction path | Defer | Neither quantitative stale-data rules nor a trained forecast needs a language-based decision dependency. Optional interpretation of operator notes can be evaluated later. Its output confidence must never become weather probability. No Jev dependency is needed for this build. |
| Automatic national alert dispatch at an 80% threshold | Reject as an assumed integration | Keep local drafts and review. Neither a private threshold nor valid CAP XML establishes authority or access to SACHET dissemination. CAP is a message standard, not a publishing credential. |

## Corrections that matter before presenting the second note

1. **GraphCast is not a diffusion model.** It uses graph neural networks for global forecasting. Its task and cadence also differ from local lightning nowcasting. [Google DeepMind publication](https://deepmind.google/research/publications/22598/)
2. **PreDiff does not demonstrate general atmospheric energy conservation.** Its energy experiment is on N-body MNIST. Its SEVIR experiment uses anticipated precipitation intensity. The paper does not prove that a proposed NCUM-conditioned generator cannot produce an impossible storm. [Original PreDiff paper](https://papers.neurips.cc/paper_files/paper/2023/file/f82ba6a6b981fbbecf5f2ee5de7db39c-Paper-Conference.pdf)
3. **Pysteps is broader than unchanged echo translation.** STEPS includes multiscale stochastic evolution and uncertainty. Pure advection still has initiation/growth limitations, but presenting every pysteps method as a static-shape deterministic baseline is inaccurate. [Pysteps methods paper](https://gmd.copernicus.org/articles/12/4185/2019/)
4. **ConvLSTM or U-Net is not automatically useless.** Loss, target, training data and probabilistic formulation matter. A simpler model is a necessary comparator. Multisensor recurrent-convolutional thunderstorm forecasting already predicts lightning, hail and heavy precipitation in published work. [Leinonen et al., 2023](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2022GL101626)
5. **The Py-ART velocity example is mislabeled.** `calculate_velocity_texture` derives the texture of an existing velocity field. It does not extract radial velocity itself. [Official Py-ART API](https://arm-doe.github.io/pyart/API/generated/pyart.retrieve.calculate_velocity_texture.html)
6. **CAP meanings need correction.** `Expected` concerns when responsive action should occur, not merely when a storm arrives. `Extreme` describes threat to life/property, not a prescribed dBZ threshold. `Likely` has a generic probability interpretation in CAP, but neither CAP nor the reviewed evidence establishes the note's 80% NDMA policy. [CAP 1.2 specification](https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html)
7. **The Ghaziabad timeline is fiction for illustration.** Its 70 km/h wind, three-kilometre error, two-minute error, cell-broadcast delivery and grid actions are not results. Keep it explicitly simulated. A lightning jump at 14:15 cannot demonstrate forecasting the first flash of that already-electrifying storm at 14:30.

Further data-access and instrument claims should follow the [data atlas](DATA_SOURCES.md). Model choice cannot remove the need for matched, licensed observations and independent event labels.

## A leakage trap in otherwise useful tracking

DATing's documentation includes `split_IDs` and `will_merge`, which can refer to the **next** timestep. If an offline pipeline tracks the full event, then attaches these fields to earlier training examples, it can leak future information.

Run detection/tracking only on the observation prefix available at the forecast issue time. Alternatively timestamp each lineage edge when it becomes known, and filter by that timestamp. A split seen later is valid evaluation truth; it is not an earlier predictor. Tune pixel-area and distance thresholds to the actual projected grid instead of copying defaults after downsampling. [DATing parameters and output definitions](https://pysteps.readthedocs.io/en/stable/generated/pysteps.tracking.tdating.dating.html)

Satellite interpolation has the same boundary. Filling a 14:10 state using a 14:15 image is retrospective reconstruction, not valid 14:10 inference. Fill model tensors with finite neutral values plus masks; passing NaNs into ordinary neural layers is not by itself missing-data handling.

## Algorithm at each stage

These are recommendations for the next version, not claims about installed functionality.

| Stage | Recommended method | Gate before adding complexity |
|---|---|---|
| Ingestion | Provider adapters, immutable files/checksums, observation and receipt timestamps | Demonstrate one causal historical replay |
| Radar preparation | Py-ART/wradlib QC and georeferencing for raw radar, then a documented composite | Obtain actual overlapping radar data and quality metadata |
| Alignment | Metric projected grid, validity and age channels, source-specific resampling | Unit/projection checks and no future observations |
| Motion baseline | Existing global translation baseline, then compare local Lucas-Kanade optical flow | Local flow must improve representative held-out radar cases |
| Storm history | DATing or detection plus overlap tracking; parent-child records and growth features | Check ordinary motion, splits, merges, disappearance and sensor outages |
| Learned forecast | Compact ConvLSTM or temporal encoder-decoder; motion plus learned radar development | Establish skill over the motion baseline before adding attention/diffusion |
| Lightning | Direct occurrence classifier for a fixed area and future window; separate initiation cohort | Actual lightning labels, complete coverage rules and region/date holdouts |
| Timing extension | Conditional first-event hazard model with censoring | Prove useful timing and calibration beyond direct horizon classifiers |
| Reliability | Held-out calibration, model/data status kept separate, explicit unavailable outputs | Coverage-conditioned scorecards and replayed source failures |
| Delivery | Shared forecast snapshot API, operator website, location-focused phone interface | Both clients show the same issue, validity, expiry and provenance |
| Review | Versioned policy, local advisory draft, operator action and audit record | Operational authorization and integration testing before external dissemination |

For lightning, define the sensor product, flash/stroke type, radius and window explicitly. "Any observed flash in the next 30 minutes" is different from an instantaneous +30-minute map. "Time to next flash" is different from initiation after a verified previous absence. Exclude or censor unknown future coverage; no received events does not prove a quiet atmosphere.

## Website, app and computation

Use one backend forecasting service for both the website and mobile experience. Compute a regional forecast once per issue/model/input manifest and reuse it across viewers. The website supports map comparison, tracking, input evidence and review. The phone interface shows saved locations, the next relevant forecast window, instructions and expiry. A responsive installable web app is a sensible first delivery; a native app can follow a demonstrated need. These are design choices, not measured performance claims.

Keep raster arrays separate from storm records. A bounded recent-frame buffer helps streaming; chunked storage helps a larger archive. A spatial index helps object/asset lookup. H3 can support geographic joins, but it need not replace the model's metric grid. The present small replay does not need a distributed graph database or a microservice for each step.

Measure ingestion delay, decoding, gridding, inference, calibration, storage and client payload time separately. Report p50/p95 latency, peak memory, hardware, domain, grid spacing, ensemble size and model version. Multiple diffusion members and denoising steps add network evaluations; batching can change throughput, so "latent" alone does not prove consumer-GPU real-time operation. A 1 km output grid does not guarantee 1 km prediction accuracy.

Adaptive tiling is useful only if its saved work exceeds scheduling, duplicate halo processing and input-reading overhead without unacceptable misses. Compare it with fixed tiles on identical events, hardware and required coverage. Retain a whole-region background pass and a maximum time between visits to quiet tiles.

## Conformal prediction and extreme-value theory

Neither supplied note explicitly proposes conformal prediction or extreme-value theory. They should not be attributed to the friends.

Conformal methods could later provide prediction sets or intervals, but ordinary exchangeability assumptions do not automatically hold for neighbouring weather pixels and time steps. Adaptive conformal methods target long-run coverage under changing distributions; that is not a guarantee for every storm or a substitute for lightning probability calibration. Delayed or missing labels also affect updates. Defer until a representative real validation stream exists. [Gibbs and Candès, 2021](https://proceedings.neurips.cc/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html)

Extreme-value theory can help study tails of continuous rainfall or another well-defined severity variable. It does not create first-flash labels or turn high reflectivity into extreme lightning risk. Threshold choice, clustered events, seasonality and sample support need investigation. It offers little immediate value for the present tiny radar replay and synthetic binary classifier. [WMO guidance on extremes](https://www.wcrp-climate.org/documents/WCDMP_TD_1500.pdf)

## What to claim as the contribution

The defensible proposal is an India-focused, auditable forecast workflow that tests how sensor delays and failures affect first-flash usefulness. Tracking, multi-input fusion, graph networks, survival analysis and diffusion are established methods. Combining their names is not evidence of a new algorithm.

Test specific contributions in order: causal replay and coverage handling; useful tracked history; real lightning skill and calibration; then selective computation or graph learning if they improve the measured result. Keep an addition only when it improves the agreed metric or operator task enough to justify its cost. The first demonstration should show one held-out event, what was available at issue time, the forecast and later observations, followed by the same replay with a sensor removed.

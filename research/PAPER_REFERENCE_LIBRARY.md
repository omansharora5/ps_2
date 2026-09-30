# VAJRA paper reference library

Evidence cutoff and verification date: **30 September 2026**. This is a curated set of 12 primary research papers, with supporting official documentation where implementation details matter. It supports the accepted staged architecture in [Product flow and algorithms](../PRODUCT_FLOW_AND_ALGORITHMS.md). It is not an exhaustive survey or a claim that VAJRA reproduces the published results.

Publication year refers to the journal or proceedings version. An arXiv copy does not make a published article a preprint-only work. Recent entries R2 and R9 have verifiable journal metadata before the cutoff. No post-cutoff work or unverified accuracy figure is included.

## Which sources support which decisions?

| VAJRA decision | Most relevant references | What the evidence supports |
|---|---|---|
| Separate lightning from radar/precipitation prediction | R1, R2, R3 | Direct lightning targets and task-specific evaluation |
| Test first-lightning lead time and absent radar coverage | R2 | These are meaningful evaluation dimensions with existing prior art |
| Represent sensor age and missingness explicitly | R3, R4 | Multisensor adaptation and a general method for missing time-series inputs |
| Reuse tracking and maintain observed storm histories | R5 | Detection, motion-assisted association and radar quality assessment |
| Compare movement plus development against strong baselines | R6, R7 | Growth/decay beyond simple advection is an established approach |
| Consider diffusion after compact models establish a baseline | R8, R9 | Probabilistic precipitation research worth benchmarking later |
| Treat first-event timing as a censored prediction problem | R10 | A mathematical method to test, not existing India lightning validation |
| Verify probability quality and spatial accuracy separately | R11, R12 | Proper probability scoring and neighbourhood spatial verification |

## R1. ProbSevere LightningCast: A Deep-Learning Model for Satellite-Based Lightning Nowcasting

**Authors:** John L. Cintineo, Michael J. Pavolonis and Justin M. Sieglaff. **Year and venue:** 2022, *Weather and Forecasting*, 37, 1239–1257. **Status:** peer-reviewed journal article. **Primary source:** [NOAA article record](https://repository.library.noaa.gov/view/noaa/52868), [DOI 10.1175/WAF-D-22-0019.1](https://doi.org/10.1175/WAF-D-22-0019.1).

**Prediction target:** next-hour lightning observed by the GOES-16 Geostationary Lightning Mapper, using satellite imager inputs.

**Contribution:** Uses a convolutional semantic-segmentation model with visible and infrared ABI imagery to produce spatial lightning probabilities. This is direct prior art for anticipating electrical activity from developing clouds.

**Relevance to VAJRA:** Establishes a satellite-only comparison and a reason to train on lightning observations rather than call a cold-cloud or radar threshold a lightning probability.

**Transfer limitation:** GOES ABI/GLM imagery and labels are not interchangeable with INSAT channels or Indian ground-network records. Total lightning is not the same as cloud-to-ground strikes. Local label definitions, sensor matching and validation remain necessary.

## R2. The Impact of Radar Reflectivity Data in a Satellite-Based Lightning Nowcasting Model

**Authors:** John L. Cintineo, Michael J. Pavolonis, Lena Heuscher and Justin M. Sieglaff. **Year and venue:** 2026, *Weather and Forecasting*, 41, 149–168. **Status:** peer-reviewed journal article; cite the 2026 journal issue, even where earlier project pages mention development in 2025. **Primary source:** [NOAA article record and abstract](https://repository.library.noaa.gov/view/noaa/75509), [DOI 10.1175/WAF-D-25-0067.1](https://doi.org/10.1175/WAF-D-25-0067.1).

**Prediction target:** GLM-observed lightning from ABI imagery and MRMS reflectivity at the −10°C level.

**Contribution:** Tests satellite/radar combinations through ablations, including regions with and without radar coverage and first-flash events. It directly investigates complementary observation sources for lightning guidance.

**Relevance to VAJRA:** This is the closest recent comparator for the proposed first-lightning and imperfect-radar evaluation. The proposal should explain what Indian adaptation and recorded data latency add beyond this existing work.

**Transfer limitation:** Absence of geographic radar coverage does not represent every real outage, stale scan, beam blockage or storm-dependent communications failure. Its US results do not establish performance for Indian radar products or lightning networks.

## R3. Thunderstorm Nowcasting With Deep Learning: A Multi-Hazard Data Fusion Model

**Authors:** Jussi Leinonen, Ulrich Hamann, Ioannis V. Sideris and Urs Germann. **Year and venue:** 2023, *Geophysical Research Letters*, 50, e2022GL101626; first published 19 April 2023. **Status:** peer-reviewed research letter. **Primary source:** [Publisher article, DOI 10.1029/2022GL101626](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2022GL101626).

**Prediction targets:** lightning, hail and heavy precipitation, using the same network architecture with task-specific targets.

**Contribution:** Combines Swiss radar, satellite imagery, lightning, numerical forecasts and terrain information. It evaluates contributions from different data sources and describes adaptation when some inputs are unavailable.

**Relevance to VAJRA:** Strong prior art for both multisensor fusion and a compact recurrent-convolutional approach. It supports starting with a practical temporal model and testing each source's value instead of assuming a larger transformer is necessary.

**Transfer limitation:** Swiss observing systems, terrain and label construction differ from India. A forecast on a fine grid does not automatically possess that level of effective location accuracy. Attribution of predictive contribution does not establish physical causation.

## R4. Recurrent Neural Networks for Multivariate Time Series with Missing Values

**Authors:** Zhengping Che, Sanjay Purushotham, Kyunghyun Cho, David Sontag and Yan Liu. **Year and venue:** 2018, *Scientific Reports*, 8, article 6085. **Status:** peer-reviewed journal article; the earlier arXiv version dates to 2016. **Primary source:** [Journal article, DOI 10.1038/s41598-018-24271-9](https://www.nature.com/articles/s41598-018-24271-9), [author manuscript](https://arxiv.org/abs/1606.01865).

**Prediction domain:** general multivariate time-series classification, evaluated with clinical and synthetic data, not thunderstorm nowcasting.

**Contribution:** GRU-D represents missingness with masks and time intervals, and learns decay behavior for inputs and hidden states.

**Relevance to VAJRA:** Provides a sound reference for testing explicit observation-age and validity channels. It helps distinguish "not observed" from a measured zero.

**Transfer limitation:** The clinical evidence does not validate gridded weather fusion. Learned decay cannot be assumed to apply to every sensor, and missingness can change when systems or weather conditions change. Data age is not an automatic multiplier that reduces hazard probability.

## R5. A characterisation of Alpine mesocyclone occurrence

**Authors:** Monika Feldmann, Urs Germann, Marco Gabella and Alexis Berne. **Year and venue:** 2021, *Weather and Climate Dynamics*, 2, 1225–1244; published 16 December 2021. **Status:** peer-reviewed journal article. **Primary source:** [Publisher article, DOI 10.5194/wcd-2-1225-2021](https://wcd.copernicus.org/articles/2/1225/2021/).

**Analysis target:** observed thunderstorms and mesocyclones in the Swiss radar domain; not future lightning probability.

**Contribution:** Documents T-DaTing detection and tracking with thresholding, watershed separation, optical-flow advection and overlap matching. It also assesses radar observation quality. The primary purpose of the article is mesocyclone characterization.

**Relevance to VAJRA:** Reuse an existing tracking method to obtain storm history, then test whether that history improves lightning forecasts. The current [official DATing API](https://pysteps.readthedocs.io/en/stable/generated/pysteps.tracking.tdating.dating.html) separately documents split/merge outputs.

**Transfer limitation:** Radar thresholds, pixel-area filters and associations need local checking. Tracking can create algorithmic splits without a physically distinct storm splitting. Fields referring to the next timestep must not enter an earlier forecast. Tracking should run only through available history.

## R6. Lagrangian Integro-Difference Equation Model for Precipitation Nowcasting

**Authors:** Seppo Pulkkinen, V. Chandrasekar and Tero Niemi. **Year and venue:** 2021, *Journal of Atmospheric and Oceanic Technology*, 38, 2125–2145. **Status:** peer-reviewed journal article. **Primary source:** [Publisher article, DOI 10.1175/JTECH-D-21-0013.1](https://journals.ametsoc.org/abstract/journals/atot/38/12/JTECH-D-21-0013.1.xml).

**Prediction target:** radar-derived rain-rate fields.

**Contribution:** LINDA combines detected rain cells, advection, autoregressive growth/decay, scale-dependent loss of predictability and stochastic perturbations. It has deterministic and probabilistic configurations.

**Relevance to VAJRA:** A necessary comparator for the claim that learning storm development adds value. Beating unchanged echo transport alone would not show improvement over existing movement-plus-development methods. It is also relevant when evaluating the cost of a large neural model.

**Transfer limitation:** Its rain-rate formulation does not directly apply to flash counts or establish lightning initiation skill. Its runtime and forecast results depend on domain, resolution, ensemble configuration and hardware; measure them on the actual pilot.

## R7. Skilful nowcasting of extreme precipitation with NowcastNet

**Authors:** Yuchen Zhang, Mingsheng Long, Kaiyuan Chen, Lanxiang Xing, Ronghua Jin, Michael I. Jordan and Jianmin Wang. **Year and venue:** 2023, *Nature*, 619, 526–532; published online 5 July 2023. **Status:** peer-reviewed journal article. **Primary source:** [Publisher article, DOI 10.1038/s41586-023-06184-4](https://www.nature.com/articles/s41586-023-06184-4).

**Prediction target:** radar-based precipitation, evaluated on US and Chinese data.

**Contribution:** Combines a deterministic evolution network with a physics-conditioned stochastic generator to represent precipitation movement and development.

**Relevance to VAJRA:** Supports a motion-plus-development decomposition and makes clear that this decomposition is established prior art. It is a future rainfall benchmark, not the first model the project must implement.

**Transfer limitation:** It does not validate lightning, Indian sensors or all atmospheric conservation laws. Some study data are restricted. Pretrained inference assets do not remove the work needed to obtain matched data, reproduce training or validate a new domain.

## R8. PreDiff: Precipitation Nowcasting with Latent Diffusion Models

**Authors:** Zhihan Gao, Xingjian Shi, Boran Han, Hao Wang, Xiaoyong Jin, Danielle Maddix, Yi Zhu, Mu Li and Yuyang Wang. **Year and venue:** 2023, *Advances in Neural Information Processing Systems*, 36. **Status:** peer-reviewed conference paper. **Primary source:** [NeurIPS proceedings record](https://papers.neurips.cc/paper_files/paper/2023/hash/f82ba6a6b981fbbecf5f2ee5de7db39c-Abstract-Conference.html), [full paper](https://papers.neurips.cc/paper_files/paper/2023/file/f82ba6a6b981fbbecf5f2ee5de7db39c-Paper-Conference.pdf).

**Prediction domain:** probabilistic precipitation imagery on SEVIR and a separate synthetic N-body benchmark.

**Contribution:** A conditional latent diffusion pipeline with an Earthformer-UNet backbone and knowledge alignment during generation. Its energy-conservation example concerns N-body MNIST; SEVIR uses anticipated precipitation intensity.

**Relevance to VAJRA:** A reference for later probabilistic field generation and for understanding what a physically informed constraint actually means. Earthformer plus diffusion is not an unoccupied research direction.

**Transfer limitation:** These constraints do not prove general physical validity or lightning skill. Samples still need probabilistic evaluation. Training cost, sampling steps, ensemble size and end-to-end latency must be benchmarked rather than inferred from the word "latent".

## R9. STLDM: Spatio-Temporal Latent Diffusion Model for Precipitation Nowcasting

**Authors:** Shi Quan Foo, Chi-Ho Wong, Zhihan Gao, Dit-Yan Yeung, Ka-Hing Wong and Wai-Kin Wong. **Year and venue:** 2025, *Transactions on Machine Learning Research*; published-paper metadata identifies December 2025. **Status:** peer-reviewed journal article, with an arXiv distribution copy posted 24 December 2025. **Primary source:** [journal paper](https://openreview.net/pdf?id=f4oJwXn3qg), [author manuscript](https://arxiv.org/abs/2512.21118), [authors' official code and journal citation](https://github.com/sqfoo/stldm_official).

**Prediction target:** precipitation/radar-image sequences, evaluated on radar datasets including SEVIR, HKO-7 and MétéoNet.

**Contribution:** Separates deterministic forecasting from latent diffusion refinement and trains the autoencoder, conditioning network and denoising components together.

**Relevance to VAJRA:** A recent published comparator for balancing deterministic structure and stochastic detail. It also prevents presenting the name STLDM or this general construction as VAJRA's invention.

**Transfer limitation:** Its precipitation experiments are not Indian lightning validation. Its reported efficiency is configuration-specific. MétéoNet appearing in both projects does not make VAJRA's tiny replay a reproduction of its experiments.

The interactive OpenReview page triggered browser verification during this review. The indexed journal PDF, author manuscript and authors' repository agree on title/authors and the TMLR citation; the paper is not being classified from a third-party summary alone.

## R10. A scalable discrete-time survival model for neural networks

**Authors:** Michael F. Gensheimer and Balasubramanian Narasimhan. **Year and venue:** 2019, *PeerJ*, 7, e6257; published 25 January 2019. **Status:** peer-reviewed journal article; an earlier preprint appeared in 2018. **Primary source:** [Publisher PDF, DOI 10.7717/peerj.6257](https://peerj.com/articles/6257.pdf), [authors' implementation](https://github.com/MGensheimer/nnet-survival).

**Prediction domain:** time to an event with censoring, developed and evaluated for clinical/synthetic settings.

**Contribution:** Nnet-survival learns discrete conditional hazards with a likelihood that accounts for observed events and censored follow-up.

**Relevance to VAJRA:** Provides a method to test for first-lightning timing. Conditional hazards can produce coherent cumulative probabilities for the same event, location and issue time.

**Transfer limitation:** It is not a weather result. Initiation needs a defined quiet-history cohort. Lightning outages, track loss and detection efficiency affect censoring and event observation. Standard censoring assumptions need examination when storms themselves cause outages.

## R11. Strictly Proper Scoring Rules, Prediction, and Estimation

**Authors:** Tilmann Gneiting and Adrian E. Raftery. **Year and venue:** 2007, *Journal of the American Statistical Association*, 102, 359–378. **Status:** peer-reviewed methodological article. **Primary source:** [DOI 10.1198/016214506000001437](https://doi.org/10.1198/016214506000001437), [authors' published-paper copy](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf). The issue is from 2007; the publisher's later online-hosting date should not replace that citation year.

**Evaluation domain:** probabilistic forecasts for categorical and continuous outcomes.

**Contribution:** Develops the theory and examples of proper scoring rules, including quadratic and continuous ranked probability scores, with a weather forecasting application.

**Relevance to VAJRA:** Supports evaluating binary lightning probabilities with a proper score such as Brier score and any continuous ensemble with an appropriate distributional score. It explains why model confidence or image sharpness alone is inadequate.

**Transfer limitation:** A good aggregate score does not establish subgroup reliability, independence of nearby samples, local operational value or safety. Report calibration, first-flash misses, false-alert time and storm-level uncertainty alongside it.

## R12. Scale-Selective Verification of Rainfall Accumulations from High-Resolution Forecasts of Convective Events

**Authors:** N. M. Roberts and H. W. Lean. **Year and venue:** 2008, *Monthly Weather Review*, 136, 78–97. **Status:** peer-reviewed journal article. **Primary source:** [DOI 10.1175/2007MWR2123.1](https://doi.org/10.1175/2007MWR2123.1), [institution-hosted published paper](https://centaur.reading.ac.uk/31220/1/Roberts2008a.pdf).

**Evaluation target:** spatial precipitation forecasts.

**Contribution:** Uses neighbourhood event fractions to examine how forecast skill changes with spatial scale, providing the Fractions Skill Score framework.

**Relevance to VAJRA:** Complements exact-grid verification when displacement errors affect radar forecasts. Evaluate predeclared thresholds and neighbourhood scales rather than selecting the most flattering scale afterward.

**Transfer limitation:** Larger neighbourhoods tolerate larger displacement. FSS does not verify probability calibration or establish that a particular school received a useful warning. An application to lightning must use clearly defined, coverage-aware event fields rather than quietly reusing a rainfall threshold.

## Scientific assumptions the accepted architecture must test

1. **More inputs are not automatically better.** Spatial or temporal misalignment can outweigh additional information. Compare the same held-out storms with radar only, satellite only, radar plus satellite, and the full set. R2 and R3 already establish multisensor and missing-source prior art.
2. **Quality handling is not solved by appending a mask.** Some outages occur during the most dangerous events. Train and test realistic delay/coverage patterns, preserve unknown labels, and check regional/seasonal reliability. No reviewed source validates a universal hand-written age-to-hazard adjustment.
3. **Tracking may help mature storms more than initiation.** No detected object means no object history. Retain a dense background predictor, and test whether lineage adds value beyond the same inputs without tracking. Recomputing tracks with future frames would invalidate the experiment.
4. **Movement plus development is an established hypothesis, not the novelty claim.** Benchmark against LINDA as well as persistence and optical flow. Learn residuals in a declared physical/measurement space. A radar-growth result is not evidence of first-lightning skill.
5. **Timing semantics must remain consistent.** The current prototype predicts a 15-minute window ending at each lead. A future survival head predicts a cumulative event time. Those probabilities require different labels and must not be compared as if they were the same forecast product. Independent horizon sigmoid outputs are not conditional hazards.
6. **Source availability and censoring can bias first-flash results.** A first recorded flash may not be the first physical flash. Network changes, domain boundaries and incomplete quiet history can create false initiation examples. Document what the sensor observes and score misses, not only successful warning lead times.
7. **A newer architecture does not establish a better system.** PreDiff/STLDM provide precipitation research options. Keep compact models until a controlled comparison justifies greater data and compute cost. Test inference, input preparation and delivery together; no cited runtime is a VAJRA hardware guarantee.
8. **Operational value remains a separate experiment.** First-flash skill, calibration and a useful preparation deadline can support the proposal. They do not establish lives saved or authority to issue a public warning. Validate the operator workflow alongside the model, and keep simulation, retrospective evidence and live operation clearly distinguished.

The strongest supportable research claim is a **tested improvement in useful local warning under imperfect observations in a specified Indian pilot**. That result remains to be established using matched observations, frozen targets, causal replay, suitable baselines and independent evaluation.

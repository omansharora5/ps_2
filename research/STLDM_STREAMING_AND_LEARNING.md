# STLDM, rapid updates and controlled learning

Research checked on 30 September 2026 against primary papers, author code and provider documentation. Grounding and two architecture sketches precede implementation below. The existing baseline is repository commit `d8dc78a`. The architecture is proposed; the separate optional reference-inference experiment will be recorded in `docs/STLDM_GUIDE.md`.

Use the compact regional model as the pilot's shared inference worker. Add STLDM as an isolated precipitation challenger after reproducing its supplied example. Refresh a forecast when usable observations arrive; evaluate newly matured labels daily; change deployed weights only when a separately trained challenger passes review. Jev belongs after the numerical forecast, as optional officer decision support.

## What exists and what would change

Current code trace: `POST /api/image-runs` calls `nowcast/image_processing.py::image_run`, which loads the pinned French radar sample, passes two past frames to `extrapolate`, and exposes future truth only for scoring. Its persistence, global translation and dense optical-flow methods predict radar echoes. `scripts/train_images.py` separately validates event episodes, fits a compact ConvLSTM, selects a checkpoint on validation events, optionally fits temperature on separate calibration events, and freezes test evaluation. The API does not load those weights. There is no live regional scheduler, STLDM inference, daily learner or operational lightning model in this baseline. These boundaries are deliberate and must remain visible to callers. See [calibration evidence](../docs/CALIBRATION_AND_VERIFICATION.md).

The existing image sample has six frames at five-minute spacing. It cannot supply both the STLDM HKO input of five frames and its complete 20-frame future. Its grid and measurement encoding also differ. The existing sample is therefore unsuitable for a full pretrained STLDM benchmark without additional verified data.

## STLDM release audit

The exact title is **STLDM: Spatio-Temporal Latent Diffusion Model for Precipitation Nowcasting**, by Shi Quan Foo, Chi-Ho Wong, Zhihan Gao, Dit-Yan Yeung, Ka-Hing Wong and Wai-Kin Wong. The author citation names TMLR 2025; OpenReview's indexed PDF identifies publication in December 2025, while the repository introduction still says submitted. The arXiv version is dated 24 December 2025. Direct OpenReview access returned a browser challenge, so the author PDF and indexed publication header were cross-checked rather than claiming access to review discussions. [Author paper](https://arxiv.org/abs/2512.21118), [publication record](https://openreview.net/pdf?id=f4oJwXn3qg), [official repository](https://github.com/sqfoo/stldm_official).

| Item | Verified fact and integration consequence |
|---|---|
| Architecture | Native convolutional VAE and gSTA translator, followed by a spatiotemporal latent denoiser. The translator supplies a first forecast; denoising refines it. It already models time. An extra Earthformer is not required by this architecture. [Author module implementation](https://github.com/sqfoo/stldm_official/blob/49b23485734b5c00a2388febb657543afb12d6cf/stldm/modules.py) |
| Source identity | Reviewed Git commit `49b23485734b5c00a2388febb657543afb12d6cf`, dated 21 September 2026. Pin that identity instead of a moving `main`. [Commit record](https://api.github.com/repos/sqfoo/stldm_official/commits/49b23485734b5c00a2388febb657543afb12d6cf) |
| Source licence | MIT, copyright 2025 sqfoo. Preserve its notice and dependency notices. [Licence](https://github.com/sqfoo/stldm_official/blob/49b23485734b5c00a2388febb657543afb12d6cf/LICENSE) |
| Public checkpoint | `sqfoo/STLDM_official`, revision `cdb543e4f42ee754cb88f2c15abb74f0f987c98b`, public and ungated in the provider API. The model repository carries an MIT licence/card. `model.safetensors` is 324,054,852 bytes; provider LFS SHA-256 is `ed003bc16f59ac7f88ea5b81de8809b0ad28ceb4b0f8bd28c47907e958eafbbd`. This is roughly 324 MB of weights, not an inference-memory estimate. [Model API](https://huggingface.co/api/models/sqfoo/STLDM_official), [file manifest](https://huggingface.co/api/models/sqfoo/STLDM_official/tree/main?recursive=false), [licence](https://huggingface.co/sqfoo/STLDM_official/resolve/main/LICENSE) |
| Tensor contract | Released HKO model takes `[B,5,1,128,128]` and returns `[B,20,1,128,128]`. SEVIR configuration takes 13 frames and predicts 12. The supplied models use one radar-derived channel, not radar, satellite, lightning and NWP jointly. [Pinned configurations](https://github.com/sqfoo/stldm_official/blob/49b23485734b5c00a2388febb657543afb12d6cf/stldm/config.py) |
| Meaning of a pixel | HKO normalized radar values, SEVIR VIL, and MétéoNet preprocessing differ. SEVIR's loader selects `vil`; a sigmoid decoder output is a normalized field value, not a lightning probability. Preserve dataset encoding, cadence and physical units explicitly. [Dataset definitions](https://github.com/sqfoo/stldm_official/blob/49b23485734b5c00a2388febb657543afb12d6cf/data/config.py), [transform code](https://github.com/sqfoo/stldm_official/blob/49b23485734b5c00a2388febb657543afb12d6cf/data/dutils.py) |
| Inference access | `InferenceHub` accepts `[T,C,H,W]` or `[B,T,C,H,W]`, verifies the configured shape, moves data to the model device and returns predictions. Its HF branch calls `from_pretrained`, then performs local inference. The README's hosted wording does not make this a hosted forecast API. [Inference implementation](https://github.com/sqfoo/stldm_official/blob/49b23485734b5c00a2388febb657543afb12d6cf/stldm/inference.py) |
| Dependency state | README setup uses Python 3.9, PyTorch 1.12.1 with CUDA 11.6 and torchvision 0.13.1. Requirements include NumPy 1.24.4 and a large notebook/training environment. Do not apply that entire freeze to this app. Use an isolated checkout and a measured minimal inference environment. [Requirements](https://github.com/sqfoo/stldm_official/blob/49b23485734b5c00a2388febb657543afb12d6cf/requirements.txt) |

Two reproducibility details need correction before integration. The paper's appendix A says 50 sampling steps, while its runtime table reports 20 for STLDM. Released code distinguishes a 50-step diffusion schedule from 20 inference sampling steps. Record both. Also, the README mentions `2S`, but the current inference dispatch uses `2D`, `3D` and `HF`; use the checked code contract. [Configuration](https://github.com/sqfoo/stldm_official/blob/49b23485734b5c00a2388febb657543afb12d6cf/stldm/config.py), [dispatch](https://github.com/sqfoo/stldm_official/blob/49b23485734b5c00a2388febb657543afb12d6cf/stldm/inference.py).

The paper's HKO-7 timing table reports **0.55 / 0.66 / 2.41 seconds** for 128 / 256 / 512 spatial sizes, at 20 sampling steps on one RTX3090. Its training table reports **2 hours 23 minutes for 10,000 steps**, batch four, 128-pixel HKO-7, on that GPU. The paper describes 200,000 training steps overall. These are paper conditions, not measured VAJRA latency, ten-member ensemble latency, CPU performance or an Indian data-training budget. The table does not establish end-to-end ingest, queue or publication latency. [Paper, appendices A and E](https://arxiv.org/html/2512.21118v1#A5).

## Earthformer pairing and the useful benchmark ladder

Start with native STLDM unchanged. Replacing its translator with Earthformer changes learned conditioning and requires retraining; attaching a separate Earthformer forecast before a pretrained STLDM checkpoint changes the checkpoint's input distribution. Neither is a supported plug-in improvement.

**PreDiff** already uses an Earthformer-UNet latent diffusion backbone and explicit knowledge alignment. It is the relevant comparison if we want to test that family. Its released SEVIR-LR experiment consumes seven 128-pixel frames and predicts six, so it cannot be compared through unmatched frame counts or temporal resolutions. [Official PreDiff implementation, NeurIPS 2023](https://github.com/gaozhihan/PreDiff).

Use the following ladder on the same event splits, valid support and issue-time information:

1. Persistence and motion extrapolation establish whether the model beats transport.
2. LINDA tests development beyond simple transport; STEPS provides a probabilistic extrapolation comparator. LINDA's current API supports rain rate or **linear-scale reflectivity**. Its perturbation thresholds still need unit-aware configuration. Earlier project wording that restricts LINDA to rain rate is too narrow. [LINDA API](https://pysteps.readthedocs.io/en/stable/generated/pysteps.nowcasts.linda.forecast.html), [STEPS API](https://pysteps.readthedocs.io/en/stable/generated/pysteps.nowcasts.steps.forecast.html).
3. The compact native model establishes the trainable baseline. Native STLDM then tests whether generative forecasts improve useful precipitation scores within a measured budget.
4. Earthformer or PreDiff is a later distinct challenger if the simpler comparison identifies a need. Do not combine every named model in the mandatory path.

Score precipitation fields with unit-correct errors, threshold CSI/FSS, CRPS and ensemble spread/rank diagnostics. A single generated member cannot establish probability calibration. Record lead-specific sample counts and edge coverage. For lightning, use the separate 30-minute/8-km label, Brier/AP/reliability and first-event evaluation. Radar ensemble frequencies of exceeding a reflectivity threshold are not lightning probabilities.

The 2026 preprint **Spread/Error relationship and spatial error structure of precipitation ensemble nowcasting: Comparison of STEPS and generative AI**, by Martin Bonte, Lesley De Cruz, Fabian Debal and Stéphane Vannitsem, evaluates transferred LDCast against STEPS over Belgium. It reports slight underdispersion and limited ability to localize ensemble-mean errors. This supports examining spatial ensemble behavior, but is not an STLDM result or India validation. [Primary preprint, 27 January 2026](https://arxiv.org/abs/2601.19298).

## Forecast correction has three different meanings

| Operation | Proposed behavior | What changes |
|---|---|---|
| Rapid forecast refresh | On a usable new scan, construct a new as-of snapshot, estimate current motion/development and issue a new version. Later observations never overwrite an earlier forecast receipt. | Input/state and issue version; frozen weights remain fixed. |
| State correction or data assimilation | Estimate a current state from forecast and observations with an explicit observation operator and uncertainty model. Begin with re-anchoring an image forecast to new observations. Treat a learned residual or Kalman-style update as a separately verified experiment. | State estimate, not automatically network parameters. |
| Model learning | Once labels mature and pass coverage checks, train or recalibrate a challenger offline and compare it with the current deployed model. | A new version of weights or calibration, activated only after evidence passes. |

Rapidly refreshing forecasts has established precedent. NOAA's HRRR documentation describes hourly model runs with radar assimilation every 15 minutes during a pre-forecast hour. This is a physical analysis/forecast cycle, not evidence that a neural network should retrain every 15 minutes. Its US domain and methods cannot be treated as an India service. [NOAA HRRR explanation](https://rapidrefresh.noaa.gov/faq/HRRR.faq.html).

For a forecast issued at 12:00 with a target ending 12:30, a scan received at 12:05 can support a **new** issue. It cannot help produce the already-issued 12:00 prediction. A later corrected lightning file updates verification under its own label version. It does not retroactively turn that file into an available input. NWP initialization, source publication, local receipt and forecast valid time remain separate.

Do not nudge a binary lightning probability by copying a radar residual into it. A postprocessing correction needs a stated target, causal lagged errors and calibration on disjoint past events. Diffusion sampling iterations are also not repeated assimilation cycles: they refine one conditional sample from one frozen input snapshot.

## Daily learning with delayed labels

The daily job should always collect, reconcile coverage, compute monitoring reports and record the available event count. Training may be skipped when too few independent new events exist. A storm lasting across midnight remains one event; calendar days are scheduling units, not independence guarantees.

Maintain an immutable issue record and a separate label record with `target_end`, `coverage_complete`, provider revision and `label_available_at`. Negative lightning labels require covered follow-up through the full target window. First-event labels additionally need covered quiet history. Wait for a provider-specific completion rule rather than assuming the 30-minute horizon alone makes truth complete. Unresolved gaps stay unknown.

Keep four roles distinct: training/replay events, model-selection validation, calibration and final evaluation. Daily use of the same test set to decide promotion would turn it into a validation set. Use a locked final audit set sparingly and accumulate a new prospective shadow cohort after the candidate version is frozen. The existing four-way CLI is the base for this discipline; its eight-group minimum is only a software check.

A candidate may fine-tune a compact head or residual using newly matured events plus a bounded historical replay set stratified by season, sensor regime, region and storm severity. Cap repeated windows from one storm. Include rare severe cases and matched quiet periods. Compare against a frozen baseline and a periodic from-scratch retrain when feasible. Replay is a mitigation, not a guarantee against forgetting. Never learn from the model's own generated future as if it were observed truth.

Relevant primary learning evidence:

- **Overcoming catastrophic forgetting in neural networks**, Kirkpatrick et al., PNAS 2017, explains parameter interference and elastic weight consolidation. It motivates a retention test, not an automatic weather deployment recipe. [Paper](https://doi.org/10.1073/pnas.1611835114).
- **Dark Experience for General Continual Learning: a Strong, Simple Baseline**, Buzzega et al., NeurIPS 2020, combines replay with logit consistency. Begin with actual historical examples; logit replay is optional and must not preserve known sensor bias uncritically. [Proceedings](https://proceedings.neurips.cc/paper/2020/hash/b704ea2c39778f07c617f6b7ce480e9e-Abstract.html).
- **Provable Effects of Data Replay in Continual Learning: A Feature Learning Perspective**, Ding, Xu and Ji, AISTATS 2026, shows under its task-incremental theoretical setting that even full replay can forget when later noise dominates earlier signal. This strengthens the case for label QC and per-regime retention checks, not a claim about measured VAJRA performance. [Primary proceedings](https://proceedings.mlr.press/v300/ding26b.html).
- **Learning from Time-Changing Data with Adaptive Windowing**, Bifet and Gavaldà, SDM 2007, supplies ADWIN's change-detection idea. For this pilot, monitor availability, coverage and event-level error separately. Spatially correlated pixels do not satisfy a simple independent-stream interpretation of its guarantees. A drift alarm opens an investigation; it does not trigger promotion. [Author manuscript](https://www.cs.upc.edu/~gavalda/papers/adwin06.pdf), [publication DOI](https://doi.org/10.1137/1.9781611972771.42).

A champion/challenger report must include prospective Brier/log loss and reliability, alert performance at previously selected thresholds, first-flash misses, outage-stratified scores, rare-event retention, latency and memory. A sharper image, a lower training loss or yesterday's score alone cannot promote a model. Deploy weight, calibration and threshold-policy versions atomically, retain the previous bundle for rollback, and never mutate a model while an issue is in progress.

## Two architecture sketches

These are proposed interfaces, not commands currently available in VAJRA. Both candidates keep immutable raw observations, causal snapshots, delayed labels and model versions. They differ in state ownership and scheduling.

### Candidate A: shared regional worker with an optional challenger

Caller's usage first:

```python
accepted = regional.observe(raw_object_ref, received_at=now)
ticket = regional.request(region="pilot", issue_at=now, mode="live")
receipt = forecasts.latest(region="pilot", product="lightning30m")
comparison = experiments.request(snapshot=ticket.snapshot_id, model="stldm-hko-reference")
daily = learning.review(mature_labels_before=cutoff, champion=registry.active())
```

```python
ObservationRef = {sha256, source, acquired_at, published_at, received_at,
                  available_at, units, grid_id, validity_ref}
Snapshot = {id, region, issue_at, mode, observation_refs, source_ages,
            geometry_version, preprocessing_version}
ForecastBundle = {id, snapshot_id, model_version, calibration_version,
                  target_version, valid_times, output_refs, coverage, status}

RegionalForecasts.observe(ref, received_at) -> ObservationReceipt
RegionalForecasts.request(region, issue_at, mode) -> ForecastTicket
ForecastStore.latest(region, product) -> ForecastBundle | Unavailable
ExperimentQueue.request(snapshot, model) -> ExperimentTicket
LearningReview.review(mature_labels_before, champion) -> ReviewReport
```

The observation store owns raw identity and availability history. The regional scheduler owns snapshot construction, source-age policy, bounded queues and idempotency. One inference process per allocated device owns a loaded model and memory budget, microbatching compatible tiles rather than loading weights per user or city. The registry owns the complete immutable model/calibration/target bundle. The forecast store owns atomic publication and receipts. The learner cannot write the active registry pointer directly.

Keep one newest pending issue per region/product/mode and one running issue. A newer observation supersedes pending work, not the raw archive. A running obsolete result may complete, but a compare-and-swap publication check prevents it replacing a newer current forecast. Return a stale status if the latest valid result expires; never hide that state by relabeling its timestamp. A separate bounded experiment queue runs STLDM when it cannot starve required forecasts. Replay retains all selected issues and does not use live supersession.

Officer web, public web and mobile clients read the same published bundle. Place selection samples that regional result; it does not create another neural model. Jev may classify a structured receipt or route among approved options after task-specific testing. Its official limitations say it is not trained to generate text. Deterministic templates explain the numerical evidence; any separate generative explanation model would need its own controls. Jev cannot change probabilities or issue an authoritative warning. Offline clients can show a saved, time-stamped receipt but cannot refresh its meteorology. [Jev 1.13 task limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

### Candidate B: distributed actors per tile

Caller's usage first:

```python
router.publish(observation_ref, event_time=acquired_at, available_at=ready_at)
job = tile_service.issue(region="pilot", issue_at=now, registry_version="v7")
bundle = mosaic.wait_for(job, deadline=deadline, missing="explicit_mask")
review = learning.review(mature_labels_before=cutoff, champion="v7")
```

```python
TileLease = {tile_id, owner_epoch, expires_at}
TileIssue = {region_issue_id, tile_id, snapshot_digest, model_bundle, halo_spec}
TileResult = {region_issue_id, tile_id, owner_epoch, central_output_ref,
              missing_border_mask, valid_times, provenance}

TileActor.accept(observation_ref) -> OffsetAcknowledgement
TileActor.issue(TileIssue) -> TileResult
Mosaic.complete(region_issue_id, deadline) -> ForecastBundle
```

Each leased actor owns its bounded observation window and tile queue. A coordinator freezes one issue/model version and sends halo-aware work; the mosaic owner checks tile versions, neighboring support and duplicate boundaries before publication. Actors need restart checkpoints, idempotent offsets, lease fencing and state migration. Storm identities crossing tile boundaries require regional reconciliation instead of unrelated per-tile identities. Model replicas, repeated halos and transfer traffic consume resources even when actor code appears small.

This structure supports many independently active regions and multiple devices, but the public operation conceals a more difficult distributed completion protocol. Resources must bound running work and queue length separately. Ray's documented backpressure pattern illustrates the unbounded-queue problem; its logical resource declarations do not enforce physical memory use. [Queue bounds](https://docs.ray.io/en/latest/ray-core/patterns/limit-pending-tasks.html), [resource limits](https://docs.ray.io/en/latest/ray-core/patterns/limit-running-tasks.html).

### Selected pilot shape and accepted tradeoffs

Choose **A**. It puts availability, issue identity and publication ordering behind one regional operation, preserves the current modular API boundary and makes replay auditable on one host. Accept one-host capacity and a supervised worker restart in exchange for fewer distributed state transitions. Borrow B's explicit tile/halo contracts and lease-fencing idea if multiple workers are later required. Adopt distributed actors only after measured queue delay, device utilization and transfer costs demonstrate the need. Neither design exposes provider wire schemas or asks the UI to coordinate ingestion, calibration and model loading.

## Bounded memory, tiling and concurrent inference

The proposed native lightning model's central output remains 128 x 128 cells at 2 km, with six ten-minute inputs. This is **not** the pretrained STLDM input contract. Native model training must include an input halo. A starting halo is a declared experiment, not a proven constant: combine displacement over forecast lead, receptive-field margin, observation age and the 8-km target radius. For illustration only, 30 m/s for 30 minutes moves 54 km, or 27 cells at 2 km; this calculation is not an observed pilot speed bound. Estimate movement tails from training data and test border skill separately.

For the fixed 128-pixel STLDM checkpoint, preserve its trained grid/cadence and score a smaller central region with a declared border discard, or obtain/retrain a compatible larger-input model. Do not silently stretch 128 pixels across a new physical domain, insert a larger halo or change six ten-minute inputs into five frames and call it the same task.

Bound the observation window, decoder cache, queued snapshots, active batches and retained ensembles separately. A float32 input buffer alone costs `4*T*C*(H+2h)*(W+2h)` bytes per example; masks, model parameters, activations and diffusion state are additional. Benchmark peak resident/GPU memory. Chunk generated members to disk and accumulate scores where possible rather than retaining every member for every tile. LINDA already exposes callback output with `return_output=False` for this pattern. [LINDA output contract](https://pysteps.readthedocs.io/en/stable/generated/pysteps.nowcasts.linda.forecast.html).

Cache decoded observations by source hash, geometry and preprocessing version. Cache inference only with the complete snapshot hash, model/calibration version, sampling parameters and seed. Observation encoding can be reused only when the encoder sees identical values, masks and preprocessing; temporal hidden state cannot simply carry through gaps, revisions or model swaps. Maintain a coarse whole-region background pass even if heavy processing is concentrated around existing storms, because convective initiation can occur outside tracked echoes. For ensemble tiling, independent random seeds can create seams; coherent larger-domain members or shared boundary noise need explicit seam verification before use.

Measure acquisition-to-receipt delay, queue wait, decode/regrid, model compute, ensemble generation, serialization and publication separately. Record p50/p95 under simultaneous regional requests and sensor gaps. The model paper's GPU timer covers none of these service guarantees.

## Executed reference experiment and next benchmark

The isolated, pinned STLDM reference CLI now runs with strict single-channel shape, normalized-value and provenance checks. It loads the official safetensors checkpoint, processes only the supplied example's five past frames and generates one member. Future frames are used exclusively for the image-space comparison against persistence. The supplied example lacks operational availability/coverage evidence, so no UTC issue, Indian coordinates, dBZ conversion or lightning verification is invented. The [execution summary](../artifacts/stldm-reference-summary.json) records device, dependencies, source/weight/input hashes, sampling configuration, runtime and output shape. This is an executable compatibility test, not training or a live forecasting service.

Modern Torch compatibility succeeded without modifying the author source or downgrading the app. One CPU model call took 113.386315 seconds while other checks were running; persistence had lower normalized MAE/MSE on this one example. The [guide](../docs/STLDM_GUIDE.md) gives exact commands and limitations. Next, a matched multi-event precipitation benchmark should compare native STLDM with the baseline ladder. A new lightning head or multimodal STLDM extension would be a separately trained hypothesis requiring Indian labels, sensor age/mask inputs and a new evaluation contract.

The useful product claim is measurable regional freshness, honest missing-data handling, reproducible improvement and officer utility. Diffusion, motion-plus-development, replay and rapid forecast updates each have substantial prior art; their inclusion alone does not establish novelty.

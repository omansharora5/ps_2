# VAJRA presentation revision 2

The revised deck is [VAJRA_SIH26072_v2.pptx](VAJRA_SIH26072_v2.pptx). This revision changes slide 2's value propositions and NCR illustration, and replaces slide 3's architecture with the weather workflow. It preserves the reference deck's visual theme and native diagram elements.

## Architecture decision

The selected design has a forecast loop above a reviewed-learning loop, with immutable evidence between them. It adopts the two-loop candidate's state boundaries and the other candidate's explicit radar, INSAT, lightning and environmental inputs. This makes the distinction between a fresh forecast revision and a newly trained model visible.

The diagram uses blue connectors and device icons, pale purple data panels, orange prediction and evidence panels, a cyan archive cylinder and green approval elements. Its topology follows VAJRA's weather modules. It does not preserve the source deck's camera topology.

The intended forecast flow is source observations, alignment and quality checks, regional prediction, evidence checks, officer review and approved local delivery. The learning flow matches archived forecasts to later covered outcomes, reviews weak citizen evidence, freezes separate storm-event partitions, trains a candidate and evaluates it before promotion. The architecture document explains the [complete data flow and code boundaries](SIH26072_ARCHITECTURE_AND_DATA_FLOW.md).

The proposed archive joins source hashes, causal availability, forecast revisions and later outcomes. Current code stores these concerns across files and SQLite databases. The diagram does not represent a newly deployed database or distributed event service.

## Key value proposition labels

The slide uses short labels. This table supplies the meaning that those labels cannot carry on their own. An asterisk marks a deployment target or research hypothesis in the slide. Labels without an asterisk can still describe research components whose NCR skill is unestablished.

| Short label | Meaning | Current status and evidence boundary |
|---|---|---|
| 30-min Outlook | Estimate conditions over the next half-hour. | Research model horizon with six five-minute onset bins. Reliable NCR forecasts require matched observations and independent testing. |
| 5-min Refresh* | Check for newly available provider records every five minutes. | Live integration target. Provider publication cadence and permissions determine whether fresh data exists. |
| 10-min Updates* | Revise the current forecast on a ten-minute target cycle. | Live integration target. New revisions retain the previous issue records for later scoring. |
| Rolling Forecasts* | Recompute the future window as usable evidence arrives. | Bounded revision metadata queue exists. Provider subscription, regional serving and durable current-result publication remain pending. |
| Lightning Lead | Estimate lightning occurrence before the event. | Coverage-masked event and first-lightning heads exist. Indian network labels and held-out skill are still required. |
| Onset Windows | Express when the first event may occur, including no onset. | Research rain and lightning timing heads exist. Their hazards are not yet calibrated. Rain cessation requires a separate target. |
| Monsoon-aware | Condition supported calibration on the regional monsoon phase. | Research fitting exists with pooled fallback. A causal phase definition and enough independent NCR events are required. |
| Seasonal Z-R | Fit local radar-to-rain relationships by season. | Fitting and evaluation code exists. Matched radar and gauges must establish whether it improves held-out error. |
| Warm-rain Checks | Expose conditions that can make cold-cloud assumptions unreliable. | Descriptive quality flags. No validated regional warm-rain detector is claimed. |
| Dust Flags | Mark possible dust-related ambiguity in weather inputs. | Descriptive research flags. A labelled andhi evaluation is still needed. |
| Evidence Cards | Show source age, missing inputs and reasons for the forecast or hold. | Research evidence views exist. Live NCR paths, numeric radar loops and operational evidence remain pending. |
| Public Scorecards* | Publish comparable monthly probability and event scores. | Tools and empty-state views exist. A matched NCR forecast/outcome publication has not been produced. |
| Local Heatmaps* | Display the spatial distribution of risk around the selected locality. | Product target for admitted regional predictions. A display grid does not establish forecast accuracy at that resolution. |
| Citizen Feedback | Ask residents whether it is raining where they are now. | Website and native forms exist. Consent, reporting windows, duplicate checks and review are recorded. |
| Reviewed Learning | Train candidates from newly admitted evidence and inspect the result. | Bounded research learning jobs exist. Citizen votes need later alignment; no automatic promotion or guaranteed improvement occurs. |
| Native App | Provide local and operator views on a phone. | React Native application code exists. Operational alert service integration and field validation remain pending. |
| 12 Languages | Offer Indian-language access with English also available. | Twelve Indian locales plus English are included. Speech availability depends on installed voices and device support. |
| Voice Alerts* | Read valid approved guidance aloud. | Device speech controls exist. Automatic operational alert delivery and human comprehension testing remain pending. |
| Offline Relay* | Relay approved alerts through nearby Bluetooth peers. | Proposed Bitchat-inspired integration. No VAJRA BLE implementation or Bitchat interoperability is claimed. |
| Open Stack | Build on open tools and documented data providers. | The research software uses open libraries. Provider access, redistribution rights and infrastructure costs still apply. |
| Graceful Fallback* | Degrade explicitly when some inputs are unavailable. | Masks and source checks exist. Validated reduced-input models and operational failover require further work. |
| Compact Models | Share a modest temporal encoder across related prediction heads. | Compact ConvLSTM research implementation exists. Cost, memory and latency need measurements on the intended deployment hardware. |
| Model Benchmarks* | Compare models and baselines on the same eligible cases. | Baseline experiments and comparison tools exist. No completed NCR comparison against Google models is claimed. |
| Decision Research* | Evaluate whether a learned classifier helps triage ambiguous cases. | Optional shadow hypothesis. Deterministic evidence rules and authorised review retain the release decision. |

## What the NCR picture demonstrates

The background is real NASA GIBS Suomi-NPP VIIRS corrected-reflectance imagery for Delhi NCR on 27 June 2024. It is a daily mosaic, not a live feed or a verified exact acquisition time. The slide marks an approximate sample cell around Dwarka and adds an editable forecast scenario.

The future path, lead-time labels and changing rain footprint are illustrative. A single visible-light image cannot establish motion, surface rainfall or prediction accuracy. The sample cell is not an official administrative block. [Asset provenance](assets/README.md) records the provider request and geographic annotation anchors.

## Claims retained and corrected

The differentiation is the combination of local prediction, inspectable evidence, explicit withholding, regional science and reviewed improvement. Its benefit must be measured against compatible alternatives.

- Damini already provides location-based advance lightning alerts. The Ministry of Earth Sciences described alerts valid for the next 40 minutes. The deck therefore does not say that Damini only reports existing strikes or that VAJRA outperforms it. [PIB release](https://www.pib.gov.in/PressReleasePage.aspx?PRID=1813993).
- Monsoon-aware calibration and seasonal Z-R fitting are research choices. The deck does not claim that global models ignore monsoon phases or that regional Z-R research has never been done.
- Google WeatherNext supplies design inspiration. There is no Google weight transfer, verified superior NCR accuracy or completed comparable-task benchmark in this release.
- A high proportion of agreeing residents creates candidate evidence. It is not a calibrated rain probability and cannot establish lightning truth. The neutral prompt offers yes, no and unsure answers before showing the model's opinion.
- Bitchat supports nearby BLE relaying, but a working path and compatible peers are required. Internet-backed geographic channels are a different mechanism. Planned VAJRA alerts need verified issuers, expiry, geographic scope, revision, cancellation and deduplication. [Official Bitchat repository](https://github.com/permissionlesstech/bitchat), [protocol whitepaper](https://github.com/permissionlesstech/bitchat/blob/main/WHITEPAPER.md).
- Open alternatives cannot guarantee uninterrupted valid predictions. Radar, satellite, station and NWP fields carry different information. Missing required evidence must remain visible.
- The classifier is a research option. A deterministic policy can apply known evidence requirements without an LLM or agentic reasoning model.

The deck's accuracy statements remain tied to recorded experiments and known data gaps. No lives-saved count, percentage improvement, nationwide coverage, automatic daily accuracy gain or operational public warning capability is established.

## Repository references

- [Implemented system](../docs/IMPLEMENTED_SYSTEM.md)
- [Regional features and current limits](../docs/REGIONAL_FEATURES.md)
- [Numerical methods and training contracts](../docs/REGIONAL_SCIENCE_GUIDE.md)
- [Continuous forecast design](../docs/CONTINUOUS_FORECAST_DESIGN.md)
- [Operations and candidate learning](../docs/OPERATIONS_GUIDE.md)
- [Public verification](../docs/PUBLIC_VERIFICATION_GUIDE.md)
- [Offline delivery research](../research/OFFLINE_DELIVERY_AND_REGIONAL_TARGETING.md)
- [Recorded validation](../VALIDATION.md)

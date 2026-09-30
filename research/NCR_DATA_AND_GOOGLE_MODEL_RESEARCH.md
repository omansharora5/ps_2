# NCR observations, access routes, and Google model reuse

Verified on 30 September 2026. This note separates provider evidence, measurements retrieved during investigation, and proposed design choices. A provider catalogue is not proof that its full archive has been downloaded or that a forecast is validated over NCR.

## Decision

Build a regional 30-minute nowcasting model around reusable observation decoders, motion baselines and a compact trainable temporal model. Borrow WeatherNext 3's separation of observation modalities, frequent refresh and observation-based verification. Treat TimesFM as a possible station-series benchmark, not an image decoder. Neither source establishes our NCR lightning accuracy.

## Region and time definitions

NCR is larger than Delhi and its adjacent cities: the official constituent page includes districts in Haryana, Uttar Pradesh and Rajasthan. A small Delhi/Gurugram/Noida/Ghaziabad box must be labelled a **pilot domain**, not the complete legal NCR. Use the official boundary for later coverage claims. [NCR Planning Board](https://ncrpb.nic.in/ncrconstituent.html).

Proposed implementation contract: store source observation time, provider publication time, retrieval time and forecast issue time separately. Keep UTC internally and show IST in the app. An updated HTTP response or catalogue timestamp does not establish that a sensor observed the atmosphere recently.

## Sources and access

| Source | Direct route | Verified status | Appropriate use |
| --- | --- | --- | --- |
| IMD WIS2 surface SYNOP | [Collections](https://wis2box.imd.gov.in/oapi/collections?f=json), [Delhi-region example query](https://wis2box.imd.gov.in/oapi/collections/urn:wmo:md:in-imd:surface-based-observations.synop/items?f=json&limit=1000&bbox=76.5,28,78,29.3&datetime=2026-09-29T00:00:00Z/2026-09-30T23:59:59Z) | Public observations route, no personal API key. Availability varies; preserve successful snapshots. Parent collector is handling regional extraction. | Station values and quality metadata. Check precipitation accumulation periods before creating labels. |
| IMD Delhi observations bulletin | [Daily PDF](https://mausam.imd.gov.in/newdelhi/mcdata/delhi_forecast.pdf) | Successfully fetched: HTTP 200, 1,175,570 bytes at 2026-09-30 15:12:22 UTC. Bulletin issued 18:00 IST; surface observations extend to 17:30 IST. | Latest station-level daily/part-day rainfall evidence, not exact 30-minute timing. |
| IMD satellite WIS2 | [3DR metadata](https://wis2box.imd.gov.in/oapi/collections/discovery-metadata/items/urn:wmo:md:in-imd:satellite?f=json), [3DS metadata](https://wis2box.imd.gov.in/oapi/collections/discovery-metadata/items/urn:wmo:md:in-imd:satellite3ds?f=json) | Public notification and download links exist. One latest 3DR payload is WMO-framed BUFR, not a full image array. See investigation below. | Potential derived satellite measurements after decoding and checking their coordinates, units and observation time. |
| ISRO MOSDAC | [Catalogue](https://mosdac.gov.in/catalog-app/satellite.php), [API manual](https://www.mosdac.gov.in/downloadapi-manual), [registration](https://mosdac.gov.in/signup/) | Search is public. Scientific downloads require approved username/password credentials. No credentials or API key were generated. | Main INSAT scientific image-sequence route; obtain matched dates for wet and dry cases. |
| IMD radar | [Radar data portal](https://radarapi.imd.gov.in/dsp/frontend/login), [official Delhi radar page](https://mausam.imd.gov.in/responsive/radar.php?lang=en) | Portal request timed out in this check. Public page exposes rendered radar products and a historical-data enquiry route. No anonymous calibrated-volume API was verified. | Obtain numeric Delhi DWR volumes/grids, geometry, scan time and QC; display GIFs are a different product. |
| IITM lightning | [MoES dataset metadata](https://incois.gov.in/essdp/ViewMetadata?fileid=05f2bab9-054f-45cf-b77d-1eaf089252ff) | Official metadata describes Jan–Dec 2019 India event observations; no verified current anonymous event API or key. | Request event times, positions, detection quality, coverage/downtime and usage rights. |

The 30 September Delhi bulletin reports 0.0 mm both for the 24 hours ending 08:30 IST and for 08:30–17:30 IST at Safdarjung, Palam, Lodi Road, Ridge, Ayanagar, Pusa, Najafgarh, Mayur Vihar, Ghaziabad, Noida KVK Chholas, Faridabad and Gurgaon KVK. Rajghat has missing entries. Missing is not zero. These are observed dry windows at stations, not proof that every NCR block was dry. The bulletin also contains future forecasts: never mistake those forecast rows for observed training labels. [IMD bulletin](https://mausam.imd.gov.in/newdelhi/mcdata/delhi_forecast.pdf).

MOSDAC's documented example product is `3SIMG_L1B_STD`. The manual permits dataset/date/bounding-box queries and states 5,000 files per user per day with a maximum search count of 100. Use approved access, pagination and actual returned granule metadata; a bounding-box search may return full scenes rather than spatially cropped files. [MOSDAC API manual](https://www.mosdac.gov.in/downloadapi-manual).

The 3DS product guide identifies scientific L1B HDF data and derived cloud, moisture, wind and precipitation products. Decode calibration, navigation, missing values and native resolution instead of treating web colours as physical values. [ISRO product documentation](https://www.mosdac.gov.in/docs/INSAT-3DS_Operational_Products_V1.pdf).

## Public WIS2 satellite investigation

The IMD metadata classifies both satellite streams as WIS2 `core`. 3DS metadata provides a public MQTT subscription at `wis2box.imd.gov.in:8883`, with the provider-published shared credentials `everyone` / `everyone` and topic `origin/a/wis2/in-imd/data/core/weather/space-based-observations/insat-3ds/imager`. These are published service credentials, not a user-specific secret. [IMD 3DS metadata](https://wis2box.imd.gov.in/oapi/collections/discovery-metadata/items/urn:wmo:md:in-imd:satellite3ds?f=json).

HTTP discovery works without MQTT:

- [Latest 3DR notifications](https://wis2box.imd.gov.in/oapi/collections/messages/items?f=json&limit=10&metadata_id=urn:wmo:md:in-imd:satellite&sortby=-pubtime).
- [Latest 3DS notifications](https://wis2box.imd.gov.in/oapi/collections/messages/items?f=json&limit=10&metadata_id=urn:wmo:md:in-imd:satellite3ds&sortby=-pubtime).

At retrieval around 15:14 UTC, 30 September 2026, the 3DR query listed 11,005 matching notifications and latest publication `2026-09-30T15:10:01Z`. Its newest payload was 173,528 bytes, SHA-256 `83d5abb3dbf02811499db3904a07b5316a1e57e147ca4ce717d51b46c3b3f3d7`, and contained BUFR beginning at byte 40. [Exact payload](https://wis2box.imd.gov.in/data/2026-09-30/wis/urn:wmo:md:in-imd:satellite/DEMS_20260930_30143910.b).

The 3DS query listed 3,257 notifications; the latest returned publication was `2026-09-16T05:10:01Z`. It must be marked stale for a 30 September live service. Both notifications used a date-level midnight `datetime`; the actual observation time must be decoded from the payload rather than inferred from that field. Latest within this endpoint does not mean latest available through every IMD distribution channel.

Python `urllib.request` using the system trust configuration succeeded where `requests` initially failed certificate validation. The solution is an appropriate trust store; certificate verification must remain enabled. Save payload checksums and provider notifications together. Do not advertise this BUFR discovery as access to calibrated INSAT image sequences until the decoded contents support that claim.

The inspected first BUFR header reports edition 4, data category 5, master table version 31 and typical time `2026-09-30T13:30:00Z`. Thus the midnight notification date is not the header time. The section-3 descriptor is 310077; its official decoder definition contains satellite-derived wind variables. [ECMWF descriptor table](https://raw.githubusercontent.com/ecmwf/eccodes/develop/definitions/bufr/tables/0/wmo/31/sequence.def). Header inspection is not a full decode or geographic validation. The installed ecCodes Python package could not load its native library, so a scientifically verified NCR subset has not been produced. [Saved discovery and provenance](../data/ncr/satellite/wis2_satellite_discovery.json) retains the notification responses and checksum; the all-domain payload was inspected in memory and deliberately not stored as an NCR sample.

## What Google's models actually offer

### WeatherNext 3

The public announcement and paper are dated 3 September 2026; the specifications call the model release August 2026. It is a probabilistic global model with hourly refresh, not a published NCR-specific lightning nowcaster. [Announcement](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/introducing-weathernext-3/), [specification](https://developers.google.com/weathernext/guides/models).

Architecture: separate modality encoders map inputs to a shared icosahedral mesh transformer; decoders return the relevant outputs. Functional Generative Network noise creates ensemble members, and training minimizes marginal CRPS. It combines atmospheric analysis with geostationary satellite sequences, and learns observational outputs. Sparse station decoding conditions on local metadata. The paper explicitly accounts for operational latency; a nominal initialization timestamp is not the time a user could actually receive the forecast. [Paper](https://arxiv.org/html/2609.03582v1).

The operational rain products are approximately 0.1-degree grids with one-hour accumulation; approximately 5 km station outputs are temperature and dew point. The 64-member model has 15-day horizons in main cycles and 48-hour horizons in interim runs. These properties do not justify claiming a street-level 30-minute rain or lightning model. [Specifications](https://developers.google.com/weathernext/guides/models).

**WeatherNext 3 is not open source.** Google's official open-source page says so explicitly. WeatherNext 2, Gen and Graph have code, checkpoints and notebooks. WN2 is the recommended self-hosted research member of that family. The documentation identifies Apache-2.0 code and CC-BY-4.0 other materials; inspect each chosen artifact's terms. [Open-source model page](https://developers.google.com/weathernext/guides/osmodel).

WN3 forecast data access is an allowlist request, usually reviewed in 5–7 business days, through Google Cloud Storage, Earth Engine or BigQuery. This provides forecasts, not WN3 training weights or the underlying raw satellite archive. Historical data and real-time data have different terms. No account was submitted, approved or billed during this investigation. [Access guide](https://developers.google.com/weathernext/guides/access-forecast).

Proposed reuse: take native sensor quality/age seriously; keep separate input branches, learn against observations, maintain uncertainty, and refresh when valid new observations arrive. Use an authorized WN3 forecast as optional atmospheric context or comparison, never as an observed rain label. Rebuilding its global training system would be disproportionate for our pilot.

### TimesFM-3

Google announced TimesFM-3 on 31 August 2026. It is a 330-million-parameter time-series model supporting multiple targets, historical covariates and covariates known in the future. Temporal attention alternates with attention between variables. Patches represent contiguous numerical measurements; horizon masking lets it predict a full horizon in one pass, with quantile outputs. It is not an LLM and does not directly decode satellite/radar image tensors. [Google Research explanation](https://www.research.google/blog/timesfm-3-a-zero-shot-foundation-model-for-multivariate-forecasting/).

Code exists in [google-research/timesfm](https://github.com/google-research/timesfm), and the official checkpoint is [google/timesfm-3.0-pytorch](https://huggingface.co/google/timesfm-3.0-pytorch). The model card lists 20 transformer layers, width 1280, 16 heads, context patches of 32 and forecast patches of 64. These are patch lengths, not fixed minutes: a 30-minute horizon depends on the input sampling interval.

**Licensing changes the deployment decision.** Repository code is Apache-2.0, while downloaded TimesFM-3 weights are restricted to non-commercial, non-production use. The repository says authorized Google Cloud services allow production under Cloud terms. Weights through version 2.5 remain Apache-2.0. Do not interpret open code as permission to deploy the 3.0 checkpoint in a public warning service. [Official repository licence notice](https://github.com/google-research/timesfm#license-notice-for-pretrained-weights).

Proposed reuse: evaluate TimesFM-3 in a permitted research experiment on aligned station sequences; compare against simpler baselines. Use only covariates actually available at forecast issue time. Forecast outputs, future observed rainfall and retrospective reanalysis must not leak into the future-covariate slots. Do not flatten a full radar grid into thousands of station series merely to claim a Google integration.

## Regional model and dataset contract

This is a design recommendation, not a claim that all branches are implemented:

1. Store immutable raw observations and provenance. Decode radar with an appropriate Py-ART/wradlib reader and INSAT with calibrated HDF metadata. Preserve projection, channel identity and coverage.
2. Assemble causal sequences: several recent scans ending at issue time, plus only atmospheric forecasts already released. Keep sensor masks and observation age as explicit inputs.
3. Run persistence and local optical-flow extrapolation as measured baselines. Add storm tracking for growth, split and merge history.
4. Reuse the existing compact temporal-model training pipeline for a learned correction to motion and growth. Add dedicated rainfall and lightning heads only when their labels exist. A third-party radar checkpoint requires exact input/channel/scale matching and Indian fine-tuning/evaluation.
5. Produce forecast windows such as +15/+30/+60 minutes. Define whether the target is rain at the endpoint, any rain in the next 30 minutes, or accumulated amount; those are different targets.
6. On new usable observations, issue a new versioned forecast. Keep the earlier forecast unchanged for scoring. Frequent inference updates are different from changing model weights.
7. Retrain candidates in controlled batches. Promote only after held-out storm/day/season evaluation, calibration and comparison with existing baselines.

For rain/no-rain training, a label requires a valid measured accumulation or verified precipitation observation for the exact target support. Keep positive storms, correctly observed dry cases and difficult transitions. Missing gauges, radar outage and no crowd response are unknown, not dry. Separate daily bulletin labels from sub-hourly labels; do not copy a daily rain total into every 30-minute interval.

For lightning, retain event detection coverage and downtime. A no-event window is a valid negative only where the network could observe events. A rainy crowd report is not a lightning label. Keep crowd reports as separately quality-weighted evidence and test final skill against independent observations.

Evaluate by event-separated and time-forward splits. Track precision-recall, probability of detection, false-alarm ratio, CSI, Brier score and reliability; use FSS for spatial rain fields and CRPS for probabilistic quantities. Measure performance separately for wet, dry, onset and decaying cases, and report sensor-outage performance and delivery latency. A convincing demo is not an estimate of saved lives or established operational accuracy.

## Access work remaining

Approved MOSDAC credentials and calibrated image sequences; Delhi DWR scientific volumes and historical access; usable IITM lightning event labels with coverage; sub-hourly rain validation; and enough aligned regional storm/dry sequences remain the critical collection tasks. Provider authorization can be prepared for, but an API key cannot be fabricated or obtained merely by writing an adapter.

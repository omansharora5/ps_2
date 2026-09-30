# Indian data, prediction targets and citizen observations

Checked 30 September 2026. This note distinguishes existing project assets from proposed training inputs and features. Source availability, archive coverage and access permission are separate questions.

## What we are building

The main scientific deliverable is a predictive model for local thunderstorm and lightning nowcasting. Rainfall is a related output and useful observation task. A data pipeline, API, operator interface and mobile app collect inputs, deliver predictions and retain verification evidence. The model can use numerical weather prediction as an input while learning its own local forecast. No LLM is required for this pipeline.

The repository contains research forecasting code, optical-flow baselines and a compact ConvLSTM training path. It does not yet contain a model trained and independently validated on a large, matched Indian radar, satellite and lightning corpus. Citizen rain surveys and their training-label pipeline are proposed here; the existing citizen SMS draft is not that implementation.

## What is already downloaded

The [government-data inventory](../data/government/README.md) records 18 original source files totaling 11,232,879 bytes. Eight are weather payloads and ten are metadata or documentation. This is a small sample pack, not a large training corpus.

The Indian IMD sample contains 32 SYNOP reports from seven stations in the rectangle 84–86 degrees east, 24–27 degrees north, on 29 September 2026. Its 607 variable features are not 607 independent weather events. The station catalog has 432 station features. NASA POWER and NOAA GFS samples provide environmental data over India, but their providers are not Indian government agencies. American satellite, lightning and radar samples test parsers. The dates and locations across the sample pack are not aligned for Indian model training.

The exact previously successful IMD collection request is [this SYNOP query](https://wis2box.imd.gov.in/oapi/collections/urn:wmo:md:in-imd:surface-based-observations.synop/items?f=json&limit=1000&bbox=84,24,86,27&datetime=2026-09-29T00:00:00Z/2026-09-29T23:59:59Z). The current recheck timed out; the retained manifest and downloaded file establish the earlier collection. See [collections](https://wis2box.imd.gov.in/oapi/collections?f=json) and [station catalog](https://wis2box.imd.gov.in/oapi/collections/stations/items?f=json&limit=1000). Follow response pagination when supported; a request limit is not a guarantee of complete archive retrieval.

## Indian government sources for larger collection

| Source and links | Data and purpose | Access and current project status |
|---|---|---|
| ISRO MOSDAC: [satellite catalog](https://mosdac.gov.in/catalog-app/satellite.php), [download API manual](https://www.mosdac.gov.in/downloadapi-manual), [registration](https://mosdac.gov.in/signup/) | INSAT scientific image sequences and derived cloud, moisture and motion products. These are the primary satellite collection route. | Metadata search is available without login. Downloads require approved credentials and applicable product permissions. The manual states a 5,000-file daily user limit, not a promise that every product is available. No authenticated satellite download has been made for this project. |
| IMD DWR: [data portal](https://radarapi.imd.gov.in/dsp/frontend/login), [radar services](https://mausam.imd.gov.in/responsive/radar.php?lang=en) | Numeric reflectivity, velocity and other available radar products in repeated scans, with quality and geometry metadata. Needed for local storm structure and movement. | Portal/request route. Historical data contact is listed on the official radar services page. Raw archive access, time coverage, format and reuse permission need confirmation. No Indian radar sequence has been collected. Display images are not a substitute for calibrated arrays. |
| MoES/IITM: [lightning dataset metadata](https://incois.gov.in/essdp/ViewMetadata?fileid=05f2bab9-054f-45cf-b77d-1eaf089252ff) | Lightning events, including position, stroke type, amplitude and height according to the metadata. These can supply labels for lightning prediction after checking event definitions and network coverage. | The abstract explicitly describes January–December 2019 over India. Generic ongoing/till-date metadata does not establish a continuous current archive. Bulk event files, outage information and permissions have not been obtained. |
| NCMRWF: [data service](https://rds.ncmrwf.gov.in/), [IMDAA description](https://nwp.ncmrwf.gov.in/reanalysis), [login](https://rds.ncmrwf.gov.in/login) | IMDAA regional atmospheric reanalysis at about 12 km and hourly intervals, covering 1979–2020. A substantial archive for atmospheric context and historical studies. | Registration/login route. Not downloaded here. Reanalysis is not a live forecast or local rain gauge. Operational backtests must prevent use of observations assimilated after forecast issue time. |
| IMD Pune: [0.25-degree daily rainfall NetCDF archive](https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html), [gridded climatology service](https://dsp.imdpune.gov.in/home_gridded_climatology.php) | Long historical daily gridded rainfall for climatology, seasonal context and coarse validation. | Official archive route identified, but the download page timed out during this check. Exact latest year and file access were not verified. Daily values on a roughly 25 km grid cannot label rain in a small block during a 15-minute window. |

MOSDAC's [official INSAT-3DS product guide](https://www.mosdac.gov.in/docs/INSAT-3DS_Operational_Products_V1.pdf) identifies scientific products including `3SIMG_L1B_STD`, cloud mask `3SIMG_L2B_CMK`, cloud-top properties `3SIMG_L2B_CTP`, total precipitable water `3SIMG_L2B_TPW`, hydro-estimator rainfall `3SIMG_L2B_HEM`, multispectral rainfall `3SIMG_L2B_IMC` and atmospheric motion vectors `3SIMG_L2P_AMV`. Product availability and fields must be checked individually. A derived rainfall product is an estimate, not independent gauge truth.

Resolution differs between channels, spacecraft and derived products. For example, [INSAT-3DR payload specifications](https://mosdac.gov.in/insat-3dr-payloads) describe 1 km visible/SWIR, 4 km MIR/TIR and 8 km water-vapour imagery. The INSAT-3DS guide describes 4 km water-vapour imagery and cloud-top products computed over 9-by-9 boxes. Resampling these products onto a small display grid does not create measurements at that smaller scale.

No source in this table should be described as a currently integrated live Indian multi-sensor feed. Large archive existence, permission to retrieve it and successful ingestion must each be evidenced.

## Input parameters and how to obtain them

Use calibrated scientific arrays and their metadata. Decode fill values, scale factors, units, quality flags, timestamps and coordinates before calculating features. Preserve the original data alongside derived arrays.

| Input | Proposed measured or derived parameters | What the model can learn |
|---|---|---|
| Radar | Reflectivity in dBZ, reflectivity change, echo area and height where available, local motion, radial velocity in m/s; optional differential reflectivity, specific differential phase and correlation coefficient when supported | Where precipitation-sized particles occur, how echoes move and develop, and evidence about particle types. Radial velocity is motion along the radar beam, not a complete horizontal wind vector. |
| Satellite | TIR and water-vapour brightness temperatures in K, channel differences, cloud mask, cloud-top products, cooling rate in K/min, cloud texture and motion | Cloud growth, cooling and moisture patterns, including areas without usable radar. These are indirect indicators of surface rainfall. |
| Lightning network | Event time and position, event type, recent rate, distance from the target cell, quality and coverage | How electrical activity evolves. Future events form the lightning target; only past events can be input features. Do not mix strokes, flashes and optical events without a documented conversion. |
| Surface stations and rain gauges | Rain amount in mm over a defined interval, temperature and dew point, humidity, pressure, wind and gusts when available | What actually reached the surface and the local atmospheric state. Preserve reporting intervals and avoid interpreting missing rainfall as zero. |
| Atmospheric model | CAPE and CIN in J/kg, precipitable water in kg/m², winds at multiple heights, vertical shear, temperature and humidity profiles | Whether the surrounding atmosphere supports new storms or storm growth. Use operational forecasts available at issue time for operational evaluation. |
| Static and quality information | Terrain, land/sea mask, sensor age, native resolution, valid coverage, missing-data masks and radar geometry | Where evidence is weaker and how terrain or coverage affects interpretation. Missing radar is not evidence of clear weather. |

CAPE describes energy available to rising air; CIN describes inhibition. High CAPE alone does not guarantee a thunderstorm. Moisture, lifting and the atmospheric profile also matter. [NWS convective indices](https://www.weather.gov/lmk/indices).

Proposed model flow: align recent sensor sequences on a common grid and time axis, retain quality masks, estimate local motion, then use a compact temporal model to learn changes beyond moving the existing storm. Separate output heads predict rain, thunderstorm and lightning targets at defined lead times. Compare every learned model with persistence and optical-flow baselines before increasing complexity.

## What a threshold actually means

There are three different decisions:

1. Define the observed target. For rain, specify the measuring instrument, detection limit, accumulation interval and area. For lightning, specify event type, valid window, region and sensor coverage. An unobserved area is not a verified negative.
2. Learn a forecast from several features and their history. A single reflectivity, humidity or cloud-temperature cutoff cannot establish local surface rain reliably.
3. Choose an alert probability threshold using independent validation, calibration and the cost of misses versus false alarms. The operator can select an approved policy. The threshold is not itself proof of model reliability.

An illustrative radar conversion is `Z = 200 R^1.6`, with `dBZ = 10 log10(Z)` and rainfall rate `R` in mm/hour. Under this particular relation, 30 dBZ corresponds to about 2.7 mm/hour. This is not a universal Indian conversion. Drop-size distribution, hail, clutter, beam height, blockage and evaporation can change the relationship to ground rainfall. [NWS discussion of radar rainfall relationships](https://www.weather.gov/tae/research-zrpaper), [NWS radar rainfall estimation](https://www.weather.gov/mrx/radarrainfallestimates).

Current code uses 20 dBZ for echo segmentation/occurrence in `nowcast/image_processing.py` and 35 dBZ in a synthetic storm target in `nowcast/forecast.py`. These are prototype task definitions. Neither is an established Indian surface-rain or lightning threshold.

## Citizen reports: proposed training and verification flow

The proposed feature is crowdsourcing. It can supply local observations where instruments are sparse. Similar citizen weather reports already support scientific verification through NOAA's mPING work. [NOAA explanation](https://inside.nssl.noaa.gov/nsslnews/2016/03/significant-paper-using-citizen-science-reports-to-evaluate-estimates-of-surface-precipitation-type/).

1. Save the issued forecast, model version, target location and valid time before asking users. If a forecast issued at 15:00 concerns conditions at 15:30, ask about conditions at 15:30. Present conditions do not verify a future forecast.
2. Invite consenting users within the relevant area. Use a neutral question such as "What is happening where you are now?" with rain, no rain and cannot observe choices. Ask only what can be observed safely.
3. Sample predicted-dry and uncertain areas too. Asking only where rain was predicted hides missed rain. Retain the survey selection policy and invitation counts so sampling bias can be studied.
4. Record observation time separately from upload time, approximate location and accuracy, response type, a pseudonymous reporter identifier and report provenance. Minimize location retention and use coarse area subscriptions where adequate.
5. Limit duplicates, repeated submissions and coordinated spam. Consider geographic coverage and reporter independence. Ten reports from one building do not verify an entire block. No response does not mean no rain.
6. Combine reports with timestamps, coverage and independent instruments to assign a label-quality score. A majority is evidence, not certainty or a calibrated rain probability. Retain disagreements; an isolated report can reveal a real local shower missed by a coarse instrument.
7. Learn reporter reliability from independent observations rather than agreement with our own prediction. Keep unverified reports distinguishable from instrument observations and reviewed labels.
8. Add accepted reports as weak or confidence-weighted rain labels to a versioned training dataset. A rain report does not establish rain rate, hail or lightning. Lightning heads still need appropriate lightning labels.
9. Train a candidate in a batch after labels arrive, evaluate it on held-out storms and regions, calibrate it and promote only if it meets the agreed checks. Preserve the previous model for rollback.

Warnings must not wait for survey responses. The app can request feedback separately while delivering a time-sensitive warning. This workflow is a design proposal; the push-survey service, report adjudication and training integration are not implemented by this research note.

## Training and evaluation plan

Begin with a region where matched satellite, radar, station and lightning data can actually be obtained. Collect multiple seasons, independent storm episodes and quiet periods. Inspect data gaps before deciding which target and lead time are supportable. More files help only when the observations, labels and metadata are usable.

Keep forecast issue time, observation time, forecast valid time and data arrival time separate. Use only information available at issue time. Preserve units, native footprints and sensor outage periods through preprocessing. Save source URLs, checksums and acquisition terms in a manifest. Bound and resume downloads instead of scraping unrestricted volumes.

Split by storm/time blocks, with regional holdouts where possible. Adjacent frames from the same storm must not leak across training and test sets. Fit normalizers on training data; use separate validation data for threshold selection and calibration. Keep final test observations untouched by citizen-label filtering and model selection.

Measure probability quality with Brier score and reliability diagrams; measure event detection with probability of detection, false alarm ratio and critical success index at declared thresholds. Check skill against climatology, persistence and optical flow. Assess spatial tolerance with fractions skill score where suitable. Report results by lead time, region, season, storm severity and available sensor combination, with uncertainty estimated across independent storm episodes.

Evaluate the citizen-report contribution by comparing sensor-only training against sensor-plus-citizen training on the same independent instrument test set. Daily retraining is an optional schedule, not evidence of daily improvement. Keep a candidate in evaluation if improvement is absent or calibration worsens.

Precise app geofencing and precise weather prediction are different capabilities. Show model resolution, data freshness and uncertainty to operators. Where radar or station coverage is weak, use the available satellite and atmospheric context with missing-data masks, evaluate that mode separately and communicate lower confidence rather than inventing observations.

# Supplemental weather sources for the NCR pilot

Verified 30 September 2026 against provider documentation and small public endpoint probes. This is a source and design review, not a claim that each feed is integrated, that authenticated archives were downloaded, or that additional inputs improve measured forecast skill.

The supplied HOW_RAIN_PREDICTION_TRAINING_WORKS.md was reviewed as background material. Its implementation suggestions are proposals, not instructions that override the user's request or evidence from providers.

## Recommended roles

| Provider | Correct role | Access | Main restriction for our NCR model |
| --- | --- | --- | --- |
| Open-Meteo | Forecast atmospheric context and a baseline | Public forecast JSON without a key for permitted noncommercial use | Model output, including its current weather, is not observed rain truth |
| NASA GPM IMERG V07 | Coarse precipitation reference and weak training labels | Earthdata account; granule discovery and supported HTTPS/OPeNDAP/subsetting access | 0.1-degree cells and publication delays cannot establish rain in a small street/block at issue time |
| RainViewer | Optional attributed radar map overlay | Public JSON and rendered tiles | Current free API is past radar only; no numeric radar-volume or guaranteed NCR coverage contract |
| Iowa Environmental Mesonet (IEM) | Airport METAR history and observed-weather evidence | Public CSV without personal key | Official download page says precipitation amounts are unavailable for non-US stations; even returned NCR zeroes are not gauge truth |
| Meteostat | Additional station-history context with per-variable provenance | Public station/year files; hosted JSON API uses RapidAPI credentials | Public files may contain model-filled observations; do not silently label them measurements |
| NOAA GFS | Archived and current issued NWP context | Anonymous NOAA open bucket or NOMADS subset | Retain model cycle, forecast lead and actual availability; precipitation is a forecast, not a label |
| ERA5 | Historical atmosphere and research/pretraining context | CDS account/token and accepted dataset terms | Reanalysis with about five-day initial latency, not an operational current feed |
| NASA POWER | Historical broad-scale environmental context | Public point API without a personal key | Meteorology usually arrives 2–3 days late and is spatially coarse |

These feeds supplement IMD surface/radar observations, MOSDAC scientific imagery and acquired Indian lightning labels. None supplies all three missing Indian observation streams.

## Open-Meteo: working low-friction NWP context

The forecast endpoint supports hourly CAPE, convective inhibition, relative humidity, wind, precipitation and total-column integrated water vapour. Its current conditions are model based. Outside its native subhourly regions, including NCR, 15-minute output is interpolated from hourly data. Record the selected model explicitly when possible and retain the complete request and retrieval time. For retrospective issue-time tests, use archived runs and their availability rather than today's seamlessly updated historical values. [Forecast documentation](https://open-meteo.com/en/docs), [single-run archive](https://open-meteo.com/en/docs/single-runs-api).

A Delhi probe succeeded for latitude 28.61, longitude 77.21, 24 hourly records and these seven fields:

- cape: J/kg
- convective_inhibition: J/kg
- relative_humidity_2m: percent
- wind_speed_10m: m/s when wind_speed_unit=ms
- wind_direction_10m: degrees
- precipitation: mm over the documented hourly interval
- total_column_integrated_water_vapour: kg/m²

[Exact example request](https://api.open-meteo.com/v1/forecast?latitude=28.61&longitude=77.21&hourly=cape,convective_inhibition,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation,total_column_integrated_water_vapour&forecast_days=1&wind_speed_unit=ms&timezone=UTC).

The hosted free tier is for noncommercial use. Terms specify fewer than 10,000 calls/day, 5,000/hour and 600/minute; pricing also lists 300,000/month and weighted call counting for large requests. Cache shared regional results instead of issuing a provider request per app user. Attribution is required. Paid hosted access and the underlying open-data licence are separate questions. [Terms](https://open-meteo.com/en/terms), [pricing and attribution](https://open-meteo.com/en/pricing).

## IMERG: substantial archive, but estimated labels

IMERG combines multiple satellite retrievals into half-hourly 0.1° fields. The V07 archive extends into the TRMM era from January 1998. Nominal latencies are about four hours for Early, fourteen for Late, and several months for Final. NASA pages describe Final as approximately 3.5–4 months; actual latest available granules must be checked. These are estimated products, not independent dense NCR rain gauges. [NASA precipitation directory](https://gpm.nasa.gov/data/directory), [technical documentation](https://gpm.nasa.gov/resources/documents/imerg-v07-technical-documentation), [Final dataset description](https://daac.gsfc.nasa.gov/datasets/GPM_3IMERGHH_07/summary?keywords=IMERGHH).

Use the run matching the experiment:

- Final for delayed research labels, retaining the run/version and any gauge adjustment information.
- Early/Late for delayed monitoring or experiments that explicitly honour their availability time.
- Never provide an event-time Early field to a simulated forecast issued before that field could have arrived.

V07's main HDF variable is Grid/precipitation, renamed from precipitationCal. The value is a rate in mm/hour representing the half-hour interval. A complete valid interval's accumulation is rate × 0.5 hours; missing/fill values must be masked before conversion. Preserve quality fields, time bounds and native footprint. Upsampling an IMERG cell to a finer grid does not create block-scale observations. [V07 field changes](https://gpm.nasa.gov/sites/default/files/2023-07/IMERG_TechnicalDocumentation_final_230713.pdf), [NASA rate/interval interpretation](https://gpm.nasa.gov/resources/faq/how-intensity-precipitation-distributed-within-given-data-value-imerg).

Access should discover collection/granule links through Earthdata CMR/earthaccess, then use the supported authenticated download or subset service. Authorize the appropriate GES DISC application through Earthdata and store credentials locally outside Git. NASA's current tutorial repository includes Cloud OPeNDAP discovery and Harmony subsetting. A legacy GES DISC server banner warns that server access will end no earlier than 30 September 2026; do not build a permanent integration around an assumed legacy gpm1 URL. No authenticated IMERG file download was performed during this research review. [NASA tutorials](https://github.com/nasa/gesdisc-tutorials), [Earthdata application authorization](https://urs.earthdata.nasa.gov/documentation/for_users/how_to_preauth_app), [legacy server migration notice](https://snpp-omps.gesdisc.eosdis.nasa.gov/data/).

Calling IMERG the universally best open label source is unsupported. For this project it is a useful, large, coarse reference, with station and numeric radar evaluation needed to establish local skill. Satellite-derived inputs and IMERG labels can also share retrieval errors; reserve independent station evaluation.

## RainViewer: document conflict resolved conservatively

The general homepage still advertises nowcasts, approximately five-minute updates and no published hard rate limit. Its specific API transition notice states that from 1 January 2026 nowcast and satellite IR data were discontinued, maximum zoom is seven, rate limiting is 100 requests/IP/minute, and only Universal Blue remains. The dedicated Weather Maps documentation describes two hours of past radar at ten-minute intervals. Use the specific contract and live response, not the broader marketing description. [Transition notice](https://www.rainviewer.com/api/transition-faq.html), [Weather Maps API](https://www.rainviewer.com/api/weather-maps-api.html), [general API page](https://www.rainviewer.com/api.html).

A live probe of [weather-maps.json](https://api.rainviewer.com/public/weather-maps.json) returned 13 past frames, an empty radar.nowcast array and an empty satellite.infrared array. The presence of these keys must not be interpreted as available future or satellite frames.

The returned host and frame path construct tile URLs. A frame's timestamp is map generation time; its constituent radar scans can have different observation times. The coverage mask is infrequently updated, so even mask coverage does not certify a current working radar. The source-attribution page lists IMD, but that alone cannot establish fresh Delhi coverage on a given day. [Map timestamp and coverage contract](https://www.rainviewer.com/api/weather-maps-api.html), [IMD listed among sources](https://www.rainviewer.com/sources.html).

Design recommendation: show this as an optional past radar overlay with source credit, generation time and coverage status. Do not decode tile colours into trustworthy calibrated radar measurements, train the main model from them, or label an empty tile as dry weather. Personal/educational use and visible attribution are covered by current free terms; operational/commercial reliance needs a separate arrangement. [Terms on the API page](https://www.rainviewer.com/api.html).

## IEM and Meteostat: verify whether a value was measured

IEM's India archive exposes airport observations, with little additional quality control. The official form expressly warns that precipitation amounts are unavailable for non-US stations. The source provides raw METAR, temperature, dew point, winds, cloud layers and present-weather codes. A successful 29 September 2026 VIDP/VIDD probe returned p01i=0.00 even where the raw report had no numeric precipitation accumulation group. Consequently, neither missing nor apparently numeric zero IEM precipitation is accepted as gauge-verified dry evidence for NCR. Keep raw reports and use appropriately parsed present-weather evidence instead. [India download form and variable definitions](https://mesonet.agron.iastate.edu/request/download.phtml?network=IN__ASOS).

[Example two-station request](https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=VIDP&station=VIDD&data=all&sts=2026-09-29T00:00:00Z&ets=2026-09-30T00:00:00Z&tz=UTC&format=onlycomma&missing=M&trace=T&report_type=3&report_type=4). The request end is exclusive. The current backend documents a one-second per-IP throttle, up to 1,000 station-years per request and possible 503 responses under load. [IEM API contract](https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?help).

METAR classification is a project design choice: only use the observed weather section for current labels. Forecast remarks such as TEMPO/BECMG/NOSIG do not record the eventual outcome. Rain in the vicinity is not rain at the station. Missing weather codes, an absent accumulation group, or a missing report are not independent no-rain labels. Deduplicate station/time reports and do not count the same underlying METAR obtained from two aggregators as two instruments.

Meteostat's no-key annual station files are documented at https://data.meteostat.net/hourly/{year}/{station}.csv.gz. The CSV includes a header and a per-variable _source column, and can include model substitutes for missing measurements. Whole-year Parquet is also available but currently labelled beta. Preserve provenance, exclude model-filled or unidentified-source precipitation from observation labels, and verify station inventory before bulk requests. [Station/year CSV documentation](https://dev.meteostat.net/data/timeseries/hourly), [annual Parquet documentation](https://dev.meteostat.net/data/bulk/hourly).

Meteostat's hosted point/hourly JSON endpoint requires a RapidAPI key; model filling defaults to true, so disable it when requesting observational evidence. The documented normal reporting offset is around two to three hours, with later revisions possible. Thus Meteostat is not simply a no-key, instant, independent gauge network. [JSON point/hourly contract](https://dev.meteostat.net/api/point/hourly).

## GFS, ERA5 and POWER: different clocks and purposes

NOAA's GFS bucket permits anonymous access without an AWS account and provides four daily model cycles. A public prefix listing on the review date included gfs.20210101/ and gfs.20210102/; this is evidence of available historical prefixes, not proof every date/field is complete. Do not assume the AWS archive has the same short retention as a live NOMADS server. [NOAA AWS registry](https://registry.opendata.aws/noaa-gfs-bdp-pds/), [verified prefix-list request](https://noaa-gfs-bdp-pds.s3.amazonaws.com/?list-type=2&prefix=gfs.&delimiter=/&max-keys=2).

For NCR subsets the [NOMADS 0.25-degree filter](https://nomads.ncep.noaa.gov/gribfilter.php?ds=gfs_0p25) lists CAPE, CIN, PWAT, UGRD, VGRD, RH and precipitation variables. Select each field's intended vertical level, keep units and accumulation start/end, and avoid treating forecast accumulation as an instantaneous rate. Fetch only the required messages/region and cache each model cycle. A run's initialization time is earlier than its publication; operational backtests must also account for publication delay.

ERA5 offers hourly historical atmosphere on a 0.25-degree distributed grid from 1940 onward. ERA5T usually arrives about five days after the event and can be revised two to three months later. Its assimilation can use information unavailable at a forecast issue time. It is valuable for research context but cannot replace archived issued NWP in an operationally faithful test. CDS access needs an account, personal token and manual acceptance of dataset terms; this review did not create credentials. [ERA5 dataset](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview), [CDS API setup](https://cds.climate.copernicus.eu/en/how-to-api).

NASA POWER meteorology uses MERRA-2/GEOS-IT sources, generally becoming available about two days after real time; its FAQ gives 2–3 days for meteorology and 5–7 days for solar data. Typical meteorological resolution is 0.5° × 0.625°. Requesting many nearby points may return the same underlying cell. These are useful slow environmental/context data rather than fresh NCR storm evidence. Some precipitation products have different underlying sources, so retain parameter-specific provenance. [POWER source description](https://power.larc.nasa.gov/docs/methodology/data/sources/), [latency FAQ](https://power.larc.nasa.gov/docs/faqs/data/), [resolution and request guidance](https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/).

## Corrections to the supplied training explanation

The useful parts are retained: issue-time availability, explicit missingness, independent storm splits, separate rain/lightning targets, probability calibration and comparison with motion baselines. The following details need correction before becoming project claims or labels:

1. Future labels need not always come from a different instrument. Forecasting future radar from past radar is legitimate; independent surface observations are needed to establish surface-rain skill. Same-time target-derived inputs would leak the answer.
2. A gauge is a point observation with its own error and accumulation period. It does not automatically label every point in a surrounding 3 km cell. A universal gauge/radar/IMERG weight of 3/2/1 is an unvalidated design proposal.
3. The sample-count arithmetic is wrong: six hours/day × six ten-minute slots/hour × 90 days × two seasons gives 6,480 slots, not approximately 970. With approximately 178 cells that gives roughly 1.15 million overlapping cell-times, not independent storm examples. Include quiet periods and report actual independent events.
4. The worked example's 15:33 arrival is outside a 15:00–15:30 target interval. A 15:45 gauge value does not verify that interval unless its explicit accumulation bounds match. The quoted historical 79% frequency and 81% output are hypothetical and must be labelled as such.
5. Stationary persistence holds the last observed field fixed. Advective or Lagrangian persistence moves it using an estimated velocity. Optical flow is one way to obtain that velocity; these baselines should be named separately.
6. Cold cloud tops are an indirect clue, not proof of a currently strong updraft or surface rain. Warmer-topped rain is also possible. Absolute -60°C/-30°C rules and a claim that storms generally intensify over short leads should not be operational rules without local validation.
7. The suggested 0.5 mm/30-minute threshold and 3 km grid are design examples. Establish instrument sensitivity, temporal support and a defined area event before adopting them. Do not advertise unsupported resolution by resampling coarse labels.
8. Raw class frequency, sensor density and claimed 55%/85% accuracy ranges are not NCR measurements. Estimate these from the acquired dataset. Focal or class-weighted training can change calibration; assess and recalibrate using representative held-out data.

The cited Delhi Z–R study is real: it compares 2019 Delhi radar/gauge cases and reports better overall Marshall–Palmer performance, while relationships vary by season/intensity. It supports local calibration, not a universal conversion or a new model's accuracy claim. [Original study, DOI 10.1016/j.pce.2025.104182](https://www.sciencedirect.com/science/article/abs/pii/S1474706525003328).

## Integration and validation decisions

Every retained record should include provider/product/version, observation or model initialization time, valid start/end, retrieval time, units, native footprint, source URL, quality/missingness and the role: observed feature, model context, estimated label, or display-only. A forecast-window builder must enforce availability at issue time and preserve the future label interval exactly.

For a first NCR experiment, compare the existing sensor/motion baseline against the same baseline plus archived NWP context. Add quality-controlled station evidence and later matched scientific satellite/radar sequences. Treat IMERG as a separate weak-label experiment at an appropriate scale. Evaluate by storm, lead time and rain intensity using Brier/reliability, POD/FAR/CSI and neighbourhood skill, with confidence intervals grouped by independent storms. Additional providers earn inclusion by measured held-out improvement; duplicated or low-quality feeds can reduce reliability.

This research verified documentation, a live Open-Meteo response, IEM CSV response, RainViewer timeline response and NOAA bucket listing. It did not verify fresh calibrated NCR radar, obtain Indian lightning event access, download authenticated IMERG/ERA5 archives, or measure a forecast-quality improvement.

# SIH26072: training, evaluation and operational data sources

**30 September collection update:** actual IMD WIS2, NASA POWER, NOAA GFS and GOES/GLM/NEXRAD samples are now downloaded and inspected. See the [government data inventory](../data/government/README.md) for exact files, units, times, hashes and access evidence. The earlier research below records the state before that collection; Indian raw DWR, INSAT and ground-lightning training access remain outstanding.

Research/access check date: **29 September 2026**. This is a data acquisition plan and evidence record, not a claim that an Indian forecasting model has been trained. Provider documentation, direct endpoint checks and actual sample inspection are distinguished below. No accounts were created, permissions obtained, or Indian operational data agreements executed during this work.

## 1. The decision that determines feasibility

Use **MétéoNet for the immediately reproducible radar replay**, **SEVIR for subsequent multimodal model development**, and **IMD DWR + INSAT + Indian ground lightning for the eventual Indian validation/pilot**. The latter requires access confirmation. A European or US score establishes a method benchmark; it does not establish accuracy for India.

The inputs and labels must remain separate:

| Scientific question | Required target | What is insufficient |
|---|---|---|
| Will radar echo reach an area? | Future quality-controlled reflectivity on a known grid | A satellite picture, a current warning, or rain occurrence elsewhere |
| Will lightning occur within a stated radius/time window? | Future detected flashes/strokes, with network coverage and sensor quality metadata | Reflectivity threshold alone, climatology, or a lightning forecast used as truth |
| Will a storm produce dangerous surface wind/hail? | Independently verified gust/hail observations or reports | A high echo-top proxy without hazard-specific validation |
| Does an alert improve decisions? | Timestamped alert delivery, acknowledgement and user-action observations | Model image quality alone |

**Engineering recommendation:** make data freshness, missingness, source identity and licensing first-class fields. A silent missing feed must never become a zero-lightning label or a “safe” forecast. Preserve observation time, receipt time, forecast reference time, valid time and product version independently.

## 2. India: the essential sources and their access conditions

### 2.1 IMD Doppler Weather Radar

The public [IMD radar service](https://mausam.imd.gov.in/responsive/radar.php?lang=en) exposes radar displays and identifies a historical-data contact. A dedicated [Radar Data Supply Portal contact page](https://radarapi.imd.gov.in/dsp/frontend/contact) and [request workflow user guide](https://radarapi.imd.gov.in/Received_data/dsp_userguide.pdf) also exist. The guide appears in official search results, but a direct retrieval in this environment failed certificate-chain verification; it was not bypassed. Consequently this research does not establish a functioning approved archive download.

**Request package:** select a pilot radar/domain, start/end dates, native scan cadence, requested fields (reflectivity, velocity, spectrum width and dual-polarization fields where available), volume geometry, calibration/QC flags, outages, file specification, archive completeness, research/redistribution terms and a separate live-feed agreement. These are requirements to request, not a verified promise that every station supplies every field. Determine actual resolution/cadence from files; do not impose a universal “1 km every 5 min” claim on the whole network.

**Use:** regional training and independent radar verification. **Risk:** beam blockage, changing scan strategies, range-dependent beam height, attenuation, calibration changes and missing scans require station-specific quality controls. Rendered web images lose numeric precision and often include legends/borders, making them unsuitable substitutes for calibrated volume or raster records.

### 2.2 IMD API gateway and official warnings

The current [IMD API reference](https://api.imd.gov.in/public/api_reference.html) documents current observations, AWS/ARG observations, district/station nowcasts and warnings. Its index includes radar imagery and lightning, but the retrieved page does not establish raw radar-volume or historical lightning access. The [API management portal](https://api.imd.gov.in/public/index.php) provides registration/login. A direct unauthenticated request to `https://api.imd.gov.in/api/v1/districtnowcast` returned **HTTP 401** during this research.

Warnings are useful for operator context, baseline comparison and dissemination provenance; they are **not independent observation labels**. The API also uses different numeric color mappings for district warning versus nowcast products, so adapters must decode by product schema. A schema index is evidence that a service is documented, not that this project is authorized to consume or redistribute it. Confirm token provisioning, rate limits, retention and usage rights with the provider before wiring an operational adapter.

An additional official route is [IMD WIS2box](https://wis2box.imd.gov.in/) and its [SYNOP OGC collection](https://wis2box.imd.gov.in/oapi/collections/urn%3Awmo%3Amd%3Ain-imd%3Asurface-based-observations.synop?f=html). This is a lead for surface observations, not a substitute for dense radar or lightning supervision; archive depth and actual fields still require inspection.

### 2.3 INSAT-3D / 3DR / 3DS through MOSDAC

For training, use calibrated scientific products, chiefly thermal brightness temperatures, water vapor, cloud-top properties/motion and appropriate sounder/environment fields. The [INSAT-3DR payload specification](https://mosdac.gov.in/insat-3dr-payloads) gives native nadir sampling of 1 km for VIS/SWIR, 4 km for MIR/TIR and 8 km for WV. Its normal frame acquisition takes 25 minutes; acquisition duration is not a live delivery guarantee. The [IMD 2025 monsoon report](https://mausam.imd.gov.in/imd_latest/monsoon_report_2025_2.pdf) describes 3DR/3DS staggered observations at 15-minute intervals, with individual imager cadence of 30 minutes. An adapter must inspect actual acquisition timestamps rather than fabricate intermediate observations.

The [INSAT-3DS operational product specification, V1](https://www.mosdac.gov.in/docs/INSAT-3DS_Operational_Products_V1.pdf) identifies `3SIMG_L1B_STD`, HDF geolocation, cloud-top/cloud-mask/precipitable-water products and sounder products. It explicitly changes WV sampling from the older 8 km to 4 km. Product names, calibration tables and version transitions therefore need explicit adapters. The document distinguishes HDF records from JPEG chips and flags the storm-index output as images only: a product name alone does not imply downloadable numeric training arrays.

**Download process:** inspect [MOSDAC satellite catalog](https://mosdac.gov.in/catalog-app/satellite.php), select the exact dataset ID and date/region, then use the official [mdapi manual/client](https://www.mosdac.gov.in/downloadapi-manual). Metadata search can be anonymous; downloads require approved MOSDAC credentials. The manual states a maximum of **5,000 files per user per day**. Store credentials outside the repository. No credentialed data download was performed here.

**Latency and reuse:** the [2020 MOSDAC dissemination guidelines](https://www.mosdac.gov.in/look/DOCS/mosdac-data-guidelines_english.pdf) distinguish browse images, scientific datasets and model products. General users receive archive access, NRT geophysical products and other products with three-day latency; NRT access rights are case-by-case. Raw redistribution/resale is restricted, with separate treatment of value-added products and agreements; source/DOI credit is required. These published guidelines are not a current service-level agreement. Also, the [3DR cloud-microphysics catalog entry](https://www.mosdac.gov.in/doi/194/) retains research-only/noncommercial wording, whereas the general policy describes business use. Record product-specific terms and resolve such inconsistencies with MOSDAC before commercial reuse. Ordinary registration must not be advertised as guaranteed real-time L1B access.

### 2.4 IITM ground lightning, Damini and Indian networks

[IITM Thunderstorm Dynamics](https://www.tropmet.res.in/28-Thunderstorm%20Dynamics-project) lists Damini as an alert product. This establishes an existing service, not a publicly licensed historical event API.

The [MoES Earth System Science Data Portal record](https://incois.gov.in/essdp/ViewMetadata?fileid=05f2bab9-054f-45cf-b77d-1eaf089252ff) describes Earth Networks lightning observations over India for **January–December 2019**, including stroke type, amplitude, height and coordinates. It links an IITM LAS endpoint and names the scientific contact. Metadata also says “ongoing” while its abstract specifies 2019; do not infer continuous contemporary coverage. A direct request to `https://ardc.tropmet.res.in/las/UI.vm` failed with an expired-certificate error. Event files, an open license, completeness and live access were **not verified**.

**Request:** event timestamp precision, location and uncertainty, stroke/flash definition, CG/IC classification, deduplication rules, polarity/current if available, detection-efficiency maps, downtime and research/production rights. Store network version so sensor deployment changes cannot masquerade as changes in thunderstorm climate. Total optical lightning from GLM/LIS cannot simply be relabeled as Indian cloud-to-ground strikes.

## 3. Immediately reproducible sample: MétéoNet

[Météo-France's repository](https://github.com/meteofrance/meteonet) covers the northwest and southeast of France for 2016–2018, with radar, station, model and satellite products under [Etalab Open Licence 2.0](https://github.com/meteofrance/meteonet/blob/master/LICENCE.md). The [full data index](https://meteonet.umr-cnrm.fr/dataset/) and [dataset summary](https://meteofrance.github.io/meteonet/english/data/summary/) distinguish full archives from tiny repository samples. Use attribution and identify transformed output. No account was required for the samples below.

Downloaded and checked locally:

| File | Bytes | SHA-256 |
|---|---:|---|
| `data/external/reflectivity_new_SE_2018_12.2.npz` | 4,693,593 | `ed83a05b302dbd13b1ee6872bdb10e7a2da5940151c0f33fb393431997be5719` |
| `data/external/radar_coords_SE.npz` | 30,660 | `311531ff06b0fffbd970eba1360c916c49c86afbcb70c77839668976d9a31287` |

Direct sources: [reflectivity sample](https://raw.githubusercontent.com/meteofrance/meteonet/master/data_samples/radar/reflectivity_new_SE_2018_12.2.npz), [coordinate grid](https://raw.githubusercontent.com/meteofrance/meteonet/master/data_samples/radar/radar_coords_SE.npz). Full provenance and contiguous runs are in [the local manifest](../data/external/meteonet_manifest.json); [the original license](../data/external/METEONET_LICENCE.md) is retained.

The provider's [radar documentation](https://meteofrance.github.io/meteonet/english/data/rain-radar/) specifies 0.01° EPSG:4326 pixel centers, nominal five-minute cadence, `data` in tenths of dBZ, `prob` in percent and `height` in meters. Reflectivity `-200` means missing; `-100` means non-detection. The current rain-probability field is not a forecast probability, and selected measurement height is not storm-top height. The [first-party notebook](https://github.com/meteofrance/meteonet/blob/master/notebooks/radar/open_reflectivity_new_product.ipynb) independently confirms sentinel handling. Implementation should convert valid data to floating point before dividing by 10 to retain half-dBZ values.

Actual inspection found `data`, `prob` and `height` shaped **(27, 515, 784)**, all `int16`. Coordinates span latitudes **41.105–46.245° N**, longitudes **2.005–9.835° E**. The sparse dates cover 11–20 December 2018 and are naive Python datetimes; their timezone was not independently established. Only the six records at indices **14–19** form the longest uninterrupted five-minute run:

`2018-12-19 10:10, 10:15, 10:20, 10:25, 10:30, 10:35`.

Two input frames therefore permit a truthful replay evaluated against four later observations at **+5, +10, +15 and +20 minutes**. The sample cannot validate a 60-minute model, support train/test claims or establish Indian lightning accuracy. Sample sparsity must not be interpreted as radar outages in the complete MétéoNet archive. Object-typed datetime arrays require a trusted-file loader; verify the recorded checksum before permitting NumPy pickle decoding, and never apply that loader blindly to arbitrary uploads.

## 4. Open international training and evaluation datasets

### 4.1 SEVIR: the most useful multimodal starting point

The [creator's SEVIR tutorial](https://github.com/MIT-AI-Accelerator/eie-sevir/blob/master/examples/SEVIR_Tutorial.ipynb) defines US storm-centered 384 km squares and four-hour, 49-frame sequences at five-minute intervals. Modalities are visible (768×768), infrared `ir069`/`ir107` (192×192), radar VIL (384×384) and discrete GLM flash records. Lightning entries contain time and location; future flashes can be binned into explicit time/space labels. **VIL is not reflectivity or rain rate**, and its encoded values require the documented nonlinear decoding. About one-fifth of selected cases are associated with NWS storm events; the remainder are randomly sampled. Selection affects event prevalence and calibration.

The [SEVIR registry](https://registry.opendata.aws/sevir/) documents unrestricted use and anonymous `s3://sevir/` access in `us-west-2`. Independent direct checks returned HTTP 200 for [CATALOG.csv](https://sevir.s3.us-west-2.amazonaws.com/CATALOG.csv) (33,838,047 bytes) and the [lightning object listing](https://sevir.s3.us-west-2.amazonaws.com/?list-type=2&prefix=data/lght/&max-keys=5). A small listed example is [February 2018 lightning HDF5](https://sevir.s3.us-west-2.amazonaws.com/data/lght/2018/SEVIR_LGHT_ALLEVENTS_2018_0201_0301.h5), 278,026 bytes. Listing/HEAD checks establish reachability; the complete training archive was not downloaded or trained on.

Acquisition commands, for a later training machine:

```powershell
aws s3 cp --no-sign-request s3://sevir/CATALOG.csv CATALOG.csv
aws s3 ls --no-sign-request s3://sevir/data/
```

Select catalog event IDs and required modalities before requesting shards. Do not blindly sync the complete archive. Prevent episode overlap between splits; multiple catalog rows for an event are modalities, not independent examples. Reserve independent regions/seasons and a chronologically later Indian dataset for transfer validation.

### 4.2 NOAA MRMS

[NOAA NSSL](https://www.nssl.noaa.gov/projects/mrms/) documents approximately 1 km spatial grids and a two-minute update cycle, with three-dimensional mosaics at 31 levels. Use numeric reflectivity/QPE/QC products appropriate to the task, not map-server screenshots. The [NOAA-managed MRMS registry](https://registry.opendata.aws/noaa-mrms-pds/) documents anonymous `s3://noaa-mrms-pds/`, public reuse with attribution/no implied NOAA endorsement, and a major version transition in October 2020. Product semantics changed, so archive version must be retained. A live S3 listing returned HTTP 200. Download compressed GRIB2 and decode using a tested GRIB library; sample product files can be small, but full multiyear coverage is a separate storage project. US performance does not establish Indian performance.

### 4.3 NOAA/Unidata NEXRAD

[NCEI's NEXRAD product page](https://www.ncei.noaa.gov/products/radar/next-generation-weather-radar) distinguishes Level I, II and III records. Level II is suitable for volume-processing work; Level III contains derived products. The [current archive registry](https://registry.opendata.aws/noaa-nexrad/) moves Level II storage to **`s3://unidata-nexrad-level2`**; older tutorials naming `noaa-nexrad-level2` are outdated after the September 2025 deprecation. Anonymous listing of KTLX on 20 May 2019 succeeded and returned approximately 2.9 MB volume files. Cadence follows scan strategy; infer it from actual timestamps. Use reflectivity/velocity and available dual-polarization fields with geometry/QC. This is useful for radar-processing development but raises substantial sensor/domain adaptation issues before use with IMD radar.

### 4.4 GOES ABI and GLM

The [NOAA GOES registry](https://registry.opendata.aws/noaa-goes/) exposes anonymous scientific netCDF data and notes the operational transition to **GOES-19 for GOES-East in April 2025**, with GOES-18 serving GOES-West. GOES-16 is valuable for historical SEVIR-era work, but should not be assumed to be a current live feed. The [GLM instrument specification](https://goes-r.noaa.gov/spacesegment/glm.html) gives roughly 8 km sampling near nadir, 14 km near the field edge and 20-second product latency. The LCFA listing independently returned 20-second netCDF objects in `noaa-goes19/GLM-L2-LCFA/2025/120/00/`; two listed files were 543,975 and 531,687 bytes.

GLM provides **total optical lightning**, with event/group/flash hierarchies. Choose and retain one label definition. ABI provides precursor cloud evolution; match acquisition times, projection and parallax. GOES observes the Americas, not India. Its radiometry, cadence and lightning detection characteristics differ from INSAT plus Indian radio networks; cross-sensor training needs validation, not a simple channel rename.

### 4.5 Weather4cast

The [organizer's 2023 starter kit](https://github.com/agruca-polsl/weather4cast-2023) describes 11 satellite bands, 15-minute frames, approximately 12 km inputs and 2 km radar-derived outputs over 10 European regions during 2019–2021. Its task uses one hour of inputs to forecast eight hours. This is a useful methodological benchmark for satellite-to-radar transfer.

However, the [2025 data access page](https://weather4cast.net/neurips2025/get-the-data/) redirected to a login/access gate, and the [2025 terms](https://weather4cast.net/neurips2025/terms-and-conditions/) restrict datasets to the competition unless agreed otherwise, prohibit redistribution/commercial exploitation and impose publication/source requirements. **Do not treat Weather4cast as unrestricted SIH training data.** Dataset edition and organizer permission matter independently of the starter-code license. No restricted files were downloaded.

## 5. Global environmental context and India-relevant independent observations

### 5.1 ERA5 for retrospective analysis

[ERA5 single-level metadata](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview) describes global hourly reanalysis from 1940 onward on a 0.25° grid, with early availability about five days behind real time. [Copernicus independently confirms the five-day delay](https://climate.copernicus.eu/climate-reanalysis). Useful features include temperature/dewpoint, winds, pressure and CAPE; pressure-level fields support shear and vertical moisture diagnostics. The [current CDS API instructions](https://cds.climate.copernicus.eu/how-to-api) require registration, personal access token and acceptance of dataset terms. Current collection metadata labels the license CC BY 4.0; retain the terms/version used at download.

**Design implication:** ERA5 is suitable for climatology, retrospective environmental features and controlled research. It is not a live operational feed. Reanalysis incorporates later observations, so substituting ERA5 values into an allegedly live backtest can introduce unavailable information. Train/test with issue-time operational forecasts when evaluating the deployable system, or explicitly call the experiment a retrospective upper bound.

### 5.2 GFS for issue-time operational context

[NOAA NOMADS](https://nomads.ncep.noaa.gov/) lists GFS 0.25° hourly products from six-hourly model cycles; [NCEI GFS documentation](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast) describes forecast/analysis archives and access. The [current production directory](https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/) was anonymously reachable. Use small geographic/variable/level subsets via the documented GRIB filter, not whole global forecasts for every request. Temperature, humidity, winds, pressure and instability variables provide large-scale context; inspect the selected product inventory for exact levels/units.

Operational replay must select a model run that had actually arrived before the prediction's issue time. Keep cycle, lead, availability time and model version. A 0.25° field does not resolve an individual thunderstorm; it contextualizes the observation-driven nowcast. Forecast archive availability and retention differ from the live directory, so build an intentional archive before claiming reproducible long-period backtests.

### 5.3 NASA GPM IMERG

[NASA's IMERG page](https://gpm.nasa.gov/data/imerg) provides Early, Late and Final products in several scientific formats, with half-hourly products and registration instructions for Earthdata/PPS access. The [V07 technical documentation](https://gpm.nasa.gov/sites/default/files/2023-07/IMERG_TechnicalDocumentation_final_230713.pdf) specifies nominal latencies of approximately **4 hours, 14 hours and 3.5 months**, respectively. The general web page includes older wording of roughly 2.5 months for Final alongside newer 3.5-month guidance; record run/version and actual production time rather than treating a generic latency as a guarantee.

Use approximately 0.1° precipitation estimates as broad independent retrospective rainfall context, especially where gauges are sparse. It is **not an up-to-the-minute thunderstorm input** for a 0–60-minute warning and is not lightning truth. Retain uncertainty/quality fields and distinguish rain rate from accumulation. Do not spatially upsample IMERG and call the resulting pixels observed 1 km rainfall.

### 5.4 NASA ISS-LIS, TRMM-LIS and LIS/OTD climatology

NASA's live [CMR collection query for ISS-LIS V3](https://cmr.earthdata.nasa.gov/search/collections.json?short_name=isslis_v3_fin) independently identifies collection **C3838944284-GHRC_DAAC**, covering **1 March 2017–16 November 2023**. Use [its Earthdata granule search](https://search.earthdata.nasa.gov/search/granules?p=C3838944284-GHRC_DAAC), not stale third-party catalog links. The [NASA instrument performance paper](https://ntrs.nasa.gov/citations/20205010423) describes storm-scale optical lightning and cross-network comparison. ISS-LIS observed through orbital overpasses, not continuous five-minute coverage of India. It is useful for sampled validation/calibration and climatology, with observation/view-time masks; no observed flash outside a satellite pass is not a negative label.

[NASA Earthdata's lightning collections](https://search.earthdata.nasa.gov/search?fsm0=Atmospheric+Electricity&fst0=Atmosphere&zoom=2) list TRMM-LIS V5 (1998–8 April 2015), older 0.5° LIS/OTD climatologies and a newer 0.1° reprocessed flash climatology spanning the OTD/TRMM/ISS records. Climatology gives spatial/seasonal priors, not event-time warning labels. The [NASA climatology user guide](https://ghrc.nsstc.nasa.gov/pub/lis/climatology/LIS-OTD/HRMC/doc/LISOTD_climatology_dataset.pdf) describes flash-count/view-time corrections and HDF/netCDF products. Prefer current NASA collection metadata and download-specific authentication instructions. No Earthdata-authenticated event granule was downloaded during this work.

## 6. A defensible acquisition and training sequence

1. **Now:** use the verified six-frame French radar sequence to test decoding, timestamps, motion extrapolation, masks, rendering and comparison with persistence. Mark its exact date/domain in the product. It proves a pipeline, not a trained Indian warning model.
2. **Open-data research:** obtain a selected SEVIR subset with paired satellite/VIL/lightning and independent episodes. Establish persistence, motion-advection and climatology baselines before a recurrent/transformer model. Track sampling bias, missing modalities and observation masks.
3. **Indian access:** request a pilot region and multiple seasons of numeric DWR, coincident INSAT acquisitions and Indian lightning events. Confirm NRT permission separately from archive access. Inspect actual overlap/completeness before choosing grid and horizon.
4. **Indian validation:** group splits by storm episode/day and geography, reserve later seasons and independent radar sites, fit normalization/calibration only on training/validation data, and keep held-out test labels inaccessible to tuning.
5. **Shadow pilot:** run without autonomous public warnings, record issued predictions and real arrival times, compare with later observations and official products, and evaluate data-outage behavior.

These steps are proposed engineering work, not experiments already completed. The minimal metadata contract should include source, product/version, geographic footprint/projection, observation/reference/valid/receipt timestamps, units/scales, missingness/QC, license, content hash and transformation lineage.

Storage estimates must be calculated from the chosen representation. For example, a **proposed** float32 training tensor with 12 frames × 4 channels × 256 × 256 pixels is 12 MiB before targets/masks/compression. Ten thousand such examples would be about 117 GiB before overhead. That is an arithmetic planning example, not a measured archive size or required sample count. Prefer chunked region/time storage and retain immutable originals separately.

## 7. Data-specific failure modes to test

| Failure | Required behavior |
|---|---|
| Five-minute sample has a 30-minute gap | Reject the sequence or use an explicitly trained variable-time model; do not squeeze the gap away |
| Missing radar cell | Mask it in metrics/inference; never score it as dry |
| Lightning sensor unavailable | Mark label coverage unknown; do not infer no lightning |
| Satellite band is daytime-only | Carry availability/solar context; do not feed a nighttime zero as a real observation |
| US/French model used over India | Show unvalidated transfer status; collect Indian calibration/test data |
| ERA5/IMERG Final is available only after issue time | Exclude from operational inputs; use as retrospective context/targets if appropriate |
| New product changes encoding | Version-specific decoding and unit checks before model input |
| Observation-derived rain probability is present | Preserve its source meaning; never rename it thunderstorm confidence |
| Forecast target mixes stroke and flash counts | Normalize definitions explicitly and report the target used |

## 8. Verified facts that change the pitch

ISRO's [2025–26 annual report](https://www.isro.gov.in/media_isro/pdf/AnnualReport/Annual_Report_2025_26_Eng_29042026_Rev.pdf), sections 2.1(j–l), already reports a probabilistic deep-learning lightning nowcasting system with 30–120-minute leads using INSAT and ground lightning, plus convective-initiation and overshooting-top work. “First AI satellite/lightning fusion system” is therefore not defensible. A stronger differentiator is a reproducible, availability-aware Indian pilot that shows which evidence was present at issue time, how uncertainty affects a local action, and how performance changes during sensor outages. This is a proposed product distinction that still needs validation, not a demonstrated scientific novelty.

Access evidence is retained in [dataset_evidence.json](dataset_evidence.json). Critical claims were checked through more than one route where feasible: provider specification plus sample parsing for MétéoNet; registry plus live object listing for SEVIR/NOAA; collection documentation plus direct CMR lookup for ISS-LIS; product documentation plus policy/manual for MOSDAC. Multiple pages from one institution corroborate consistency but are not independent scientific replications. Remaining unverified items are explicitly identified above.

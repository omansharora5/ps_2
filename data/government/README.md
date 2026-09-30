# Government data collected for VAJRA

Collected and verified on **30 September 2026**. This folder contains actual downloaded scientific data, original source metadata/documentation, and convenient CSV derivatives.

**18 source files, 11,232,879 bytes, about 11.23 MB:** eight weather-data payloads and ten inventories, catalogs or documentation files. Four derived files add 507,683 bytes. Manifests, reports, scripts and the pre-existing French radar sample are outside those totals. The new source files come directly from IMD/NASA or from documented NOAA cloud-distribution archives; the US radar object uses the explicitly identified UCAR Unidata mirror.

The [complete inventory](inventory.json) retains each source URL, provider, retrieval time, units/time evidence, SHA-256 and limitations. [Verification results](../../artifacts/government_data_validation.json) confirm all 22 raw/derived data files and scientific parser checks. These files have not been connected to the simulator-trained forecasting model.

## What was actually collected

| Data | Region and time | Actual content | Local file or folder | Appropriate use |
|---|---|---|---|---|
| IMD SYNOP | 84–86°E, 24–27°N; reports 29 Sep 2026, 00–21 UTC | 607 features: 353 numeric and 254 null/coded; 32 reports at 7 stations; 18 field names | [Original GeoJSON](india/imd_synop_bihar_region_20260929.geojson), [CSV](derived/imd_synop_bihar_region_20260929.csv) | Indian station/interval/unit adapter; sparse surface context |
| IMD station catalog | Provider catalog snapshot | 432 station features; includes identifiers used to join the SYNOP sample | [Original catalog](india/imd_stations.json) | Station lookup; catalog presence does not prove complete observations |
| NASA POWER | Patna query, 25.5941°N, 85.1376°E; 1–7 Jun 2024 UTC | 168 hourly records × 6 variables = 1,008 values, no returned fill sentinels | [Original JSON](india/nasa_power_patna_20240601_20240607.json), [CSV](derived/nasa_power_patna_20240601_20240607.csv) | Coarse MERRA-2/POWER environmental analysis |
| NOAA GFS | Global raw fields; derived box 82–89°E, 23–28°N; 12 May 2025, 06 UTC run, +3 hours | 7 original GRIB messages; Indian subset has 609 grid points/field, 4,263 CSV rows | [Selected raw GRIB](gfs/gfs_20250512_06_f003_selected.grib2), [Indian GRIB subset](gfs/gfs_20250512_06_f003_bihar.grib2), [CSV](gfs/gfs_20250512_06_f003_bihar.csv) | Numeric forecast-context adapter; one model time |
| NOAA GOES-16 ABI | CONUS, 15 Jun 2024, 18:01:17.8–18:03:56.3 UTC | One channel-13 thermal image, 1,500×2,500 cells; 3,702,838 valid brightness temperatures | [NOAA manifest with exact path](noaa/manifest.json), `noaa/raw/` | NetCDF calibration, quality and projection handling |
| NOAA GOES-16 GLM | Americas, 15 Jun 2024, 18:02–18:03 UTC | Three adjacent 20-second files; 7,389 optical event records; flash-record counts 87, 94 and 93 by file | [NOAA manifest](noaa/manifest.json), `noaa/raw/` | Event/group/flash hierarchy, times and locations |
| NOAA/NWS NEXRAD | KTLX, Oklahoma; volume start 15 Jun 2024, 18:05:28 UTC | One N0B Level III product, code 153; 720×1,840 bins, 375,181 finite decoded reflectivity values | [Original radar product](noaa/raw/TLX_N0B_2024_06_15_18_05_28) | Radar decoder and polar geometry fixture |

The IMD box includes a Jharkhand station; it is not an administrative Bihar boundary. IMD feature count is not a count of independent storms or station reports. Original observation intervals can begin before the report date. The GLM flash-record counts are not a count of unique ground strikes.

## Official sources and terms

| Provider | Official source/catalog | Access and terms established here |
|---|---|---|
| IMD | [WIS2 collections](https://wis2box.imd.gov.in/oapi/collections?f=json), [SYNOP discovery record](https://wis2box.imd.gov.in/oapi/collections/discovery-metadata/items/urn:wmo:md:in-imd:surface-based-observations.synop?f=json) | Anonymous numeric download worked; this discovery record declares WMO core data. No blanket licence or access assumption for other IMD products |
| NASA | [POWER hourly API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/), [meteorology method](https://power.larc.nasa.gov/docs/methodology/meteorology/), [attribution guidance](https://power.larc.nasa.gov/docs/referencing/) | Public download worked; retain NASA POWER/API version/MERRA-2 attribution. Guidance includes publication/redistribution notification; no external notification was sent |
| NOAA GFS | [NCEI GFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast), [NWS disclaimer](https://www.weather.gov/disclaimer) | Public archive byte-range download worked; acknowledge NOAA/NCEP, no endorsement. Archive retention is not assumed from one successful historical file |
| NOAA ABI | [NCEI CMIP catalog](https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C01502) | Official catalog identifies the NOAA AWS distribution used |
| NOAA GLM | [NCEI LCFA catalog](https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc:C01527/html) | Official lightning-product definition and dataset citation retained |
| NOAA/NWS radar | [NCEI Level III catalog](https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C00708), [NOAA cloud access](https://www.ncei.noaa.gov/products/ncei-data-noaa-open-dissemination-program) | NOAA-produced record from UCAR Unidata's AWS mirror, rather than a NOAA-operated download hostname |

Per-file links and constraints are in [India manifest](india/manifest.json), [NOAA manifest](noaa/manifest.json), and [GFS manifest](gfs/manifest.json). NOAA's [open-data policy](https://www.ncei.noaa.gov/sites/default/files/2023-12/NCEI%20PD-10-2-02%20-%20Open%20Data%20Policy%20Signed.pdf) is linked by the NOAA collection. Publicly reachable does not imply unrestricted reuse of every Indian weather product.

## Units and easy-to-open files

The [IMD CSV](derived/imd_synop_bihar_region_20260929.csv) keeps one row for every source feature. It retains station/report/feature IDs, report time, phenomenon interval, units, value and description. A missing numeric value is blank with `numeric_value_missing=True`; it is never changed to zero. Multiple rows with the same variable name may represent different observation intervals or coded attributes.

The [NASA CSV](derived/nasa_power_patna_20240601_20240607.csv) has one row per UTC hour. Units are `T2M=C`, `RH2M=%`, `PS=kPa`, `WS10M=m/s`, `WD10M=Degrees`, `PRECTOTCORR=mm/hour`, as returned by NASA. These are grid-box environmental values, not measurements from a Patna weather station. Source support is approximately 0.5°×0.625° for the meteorological dataset; interpolation does not create 2 km observations.

The [GFS CSV](gfs/gfs_20250512_06_f003_bihar.csv) uses NOAA wgrib2's seven columns, **without a header**:

```text
reference_time_UTC, valid_time_UTC, variable, level, longitude, latitude, value
```

| GFS field | Level | Units | Decoded subset range |
|---|---|---|---|
| TMP | 2 m above ground | K | 268.457–315.457 |
| RH | 2 m above ground | % | 15.9–98.4 |
| UGRD | 10 m above ground | m/s, eastward component | −3.1504–7.4696 |
| VGRD | 10 m above ground | m/s, northward component | −5.43689–5.86311 |
| CAPE | surface | J/kg | 2–751 |
| CIN | surface | J/kg | −64.0604–−0.0604248 |
| PWAT | entire atmosphere | kg/m² | 2.72332–52.9649 |

These are sample model values, not observed storm severity. The box contains terrain outside Bihar as well. The nearest retained grid point to the Patna query is 25.5°N, 85.25°E. Native output spacing is 0.25°. The subset includes no vertical wind profile, so it cannot produce vertical shear. [Decoded inspection](gfs/inspection.json), [NOAA CSV semantics](https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/csv.html).

## Why this is not yet a training dataset

The dates and locations differ. The ABI scan and three GLM intervals overlap in time, but are not yet geographically collocated. The radar scan is later. A single satellite image cannot establish motion, and one minute of lightning cannot label a 30-minute future window.

India still needs coincident numeric DWR scans, calibrated INSAT products and independently observed lightning events with coverage/outage metadata. The current collection proves actual download and parsing. It does not establish a live feed, complete archive, model skill, forecast calibration or historical product delivery time.

| Still needed for Indian training | Official route | Current collection status |
|---|---|---|
| Numeric DWR sequences and QC | [IMD radar data portal](https://radarapi.imd.gov.in/dsp/frontend/contact) | Not obtained through an approved archive request; website images are insufficient |
| Calibrated INSAT sequences | [MOSDAC catalog](https://mosdac.gov.in/catalog-app/satellite.php), [download manual](https://www.mosdac.gov.in/downloadapi-manual) | Approved credentials and product permissions required; no authenticated download performed |
| Ground lightning events and network coverage | [MoES/IITM metadata](https://incois.gov.in/essdp/ViewMetadata?fileid=05f2bab9-054f-45cf-b77d-1eaf089252ff) | Event archive, coverage and reuse terms not obtained; Damini displays are not independent training labels |
| Multiple matched storms and quiet periods | Those providers for one chosen region and period | Not collected; these small reference files cannot substitute |

Required access fields and collection findings are described in [India notes](../../research/GOVERNMENT_INDIA_COLLECTION.md), [NOAA notes](../../research/GOVERNMENT_NOAA_COLLECTION.md), [GFS notes](../../research/GOVERNMENT_GFS_COLLECTION.md) and [the broader source atlas](../../research/DATA_SOURCES.md).

## Reproduce and verify

Use the isolated data environment so scientific readers do not change the working application dependencies. The tested environment was Python 3.14 on Windows; the pinned dependency list is an environment record, not a promise of compatibility on every platform.

```powershell
# Only if the data environment is absent:
python -m venv .venv-data
.\.venv-data\Scripts\python.exe -m pip install -r data/government/noaa/parser-requirements.txt

# Verify/reuse the fixed source snapshots:
.\.venv-data\Scripts\python.exe scripts/collect_india_data.py
.\.venv-data\Scripts\python.exe scripts/collect_noaa_data.py
.\.venv-data\Scripts\python.exe scripts/collect_gfs_data.py --decode

# Recreate CSV views and the consolidated inventory:
.\.venv-data\Scripts\python.exe scripts/prepare_government_pack.py

# All local checks, including NetCDF/radar parsing, with no data downloads:
.\.venv-data\Scripts\python.exe scripts/verify_government_data.py --scientific
```

On a fresh Windows decode, the GFS collector obtains NOAA's official wgrib2 3.1.3 executable and supporting DLLs in `tools/wgrib2/`; it does not install a system program. Tool downloads are separate from the data counts above. [Tool provenance](../../tools/wgrib2/provenance.json) records URLs and hashes. Other operating systems need a compatible `wgrib2` on PATH. Existing verified derivatives are reused without invoking the decoder.

The collectors retain raw bytes, use bounded downloads and validate checksums. TLS verification stayed enabled. Reruns verify the saved snapshot rather than silently replacing it with today's values. Expand into a training archive only after defining a common region, time range, label contract, permissions and storage budget.

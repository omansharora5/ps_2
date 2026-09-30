# Collected Indian government and NASA data

Collected and inspected **30 September 2026 UTC**. This is an actual downloaded starter pack, not a list of prospective sources. It contains **11 unmodified response bodies totaling 955,042 bytes**; including the manifest, the collection directory contains **989,885 bytes**, below the **25,000,000-byte** cap. No downloaded file is connected to the simulator-trained forecasting model.

The strongest result is a successful public download of **IMD numeric surface observations for India**. The separate NASA sample supplies historical environmental context at Patna. Neither sample contains the lightning labels or dense radar/satellite sequence required for the proposed lightning model.

## Files and provenance

All paths below are relative to the repository root. [The manifest](../data/government/india/manifest.json) has a top-level `files` list suitable for consolidation. Every downloaded file has its exact requested and resolved URLs, provider, retrieval timestamp, byte count, SHA-256, content type/format, terms reference, data role, time/geographic coverage and units where applicable, plus an explicit reason it is not training-ready. Documentation files have null observation times and empty measurement units rather than invented values.

| Downloaded file in `data/government/india/` | Bytes | Contents and inspection |
|---|---:|---|
| `imd_collections.json` | 11,837 | Raw IMD OGC API collection catalog. |
| `imd_synop_metadata.json` | 4,394 | SYNOP discovery record; producer, WMO policy classification, advertised extent and links. |
| `imd_synop_queryables.json` | 907 | Raw queryable schema, including report time, station identifier, field name, units and numeric value. |
| `imd_stations.json` | 346,192 | **432 station features**, matching the response's `numberMatched=432`; no next page. |
| `imd_synop_bihar_region_20260929.geojson` | 259,266 | **607 unique scalar/descriptor features**, covering **32 reports at 7 stations**. |
| `nasa_power_patna_20240601_20240607.json` | 19,351 | **168 UTC hours × 6 variables = 1,008 scalar values**; no `-999` fill values. |
| `nasa_power_hourly_docs.html` | 32,713 | Original NASA hourly API documentation. |
| `nasa_power_meteorology_docs.html` | 25,236 | Original NASA meteorological data methodology. |
| `nasa_power_acknowledgements.html` | 16,756 | NASA POWER project/provider acknowledgements. |
| `nasa_power_referencing.html` | 18,436 | NASA attribution and publication/redistribution guidance. |
| `wmo_wis2_guide.html` | 219,954 | Official WMO WIS2 guide, including core-data policy. |

These byte counts and feature counts were computed from the saved files. Provider response bodies were preserved without JSON reserialization, filtering, rounding, unit conversion or removal of missing values. The downloader requests identity transfer encoding; the preservation contract is the response body after standard HTTP content-transfer decoding.

## IMD surface observations: what was obtained

The [IMD WIS2 catalog](https://wis2box.imd.gov.in/oapi/collections?f=json) exposes a SYNOP observation collection and station metadata. This is a separate public interface from the IMD gateway endpoints that previously returned authentication errors. A failure at one endpoint is not evidence that all IMD data are inaccessible.

The [saved observation query](https://wis2box.imd.gov.in/oapi/collections/urn:wmo:md:in-imd:surface-based-observations.synop/items?f=json&limit=1000&bbox=84,24,86,27&datetime=2026-09-29T00:00:00Z/2026-09-29T23:59:59Z) requested longitude **84–86°E**, latitude **24–27°N**, and report times on **29 September 2026 UTC**, with a maximum of 1,000 features. This is a geographic box around Bihar that also includes Daltonganj in Jharkhand; it is not an administrative Bihar polygon.

The response contains all **607 matching features** for that query, with no next-page link. Of these, **353 have finite numeric `value` fields** and **254 have null `value` fields**; coded descriptions and absent measurements must not be converted to zero. There are **18 distinct field names**. The seven station identifiers join to the downloaded station catalog as follows:

| WIGOS station identifier | Source station name |
|---|---|
| `0-20000-0-42383` | MOTIHARI |
| `0-20000-0-42387` | MUZAFFARPUR |
| `0-20000-0-42488` | CHAPRA |
| `0-20000-0-42492` | PATNA |
| `0-20000-0-42587` | DALTONGANJ |
| `0-20000-0-42588` | DEHRI |
| `0-20000-0-42591` | GAYA (42591-0) |

Report timestamps span **00:00–21:00 UTC**, with eight distinct report times separated by three hours across the combined sample. **Not every station reports at every time**: 32 reports across seven stations do not form a complete 7 × 8 grid. The actual point extent is **84.06–85.4°E, 24.05–26.66667°N**. `phenomenonTime` spans **28 September 15:00 UTC through 29 September 21:00 UTC**, because some measurements represent intervals preceding their report time.

| Fields in the saved sample | Units exactly as supplied |
|---|---|
| Air/dewpoint temperature; specified-period maximum/minimum temperature | `Celsius` |
| Mean-sea-level pressure; 24-hour pressure change | `hPa` |
| Horizontal visibility; cloud-base height | `m` |
| Total cloud cover | `%` |
| Wind direction; direction of an observed phenomenon/cloud | `deg` |
| Wind speed | `m/s` |
| Total precipitation/water equivalent | `kg m-2` |
| Cloud amount/type; present weather; past weather | `CODE TABLE` |

The manifest retains the full field-name-to-unit mapping and per-field counts. For example, the five precipitation features are **not automatically hourly rainfall**: their own phenomenon intervals must be used. Repeated field names can occur within a report, so preserve the feature ID and interval rather than overwriting them in a simple station/time/name dictionary. Code-table descriptions require a documented decoder before quantitative use; null numeric values alone are not reliable categorical labels.

**Terms:** The [IMD discovery record](https://wis2box.imd.gov.in/oapi/collections/discovery-metadata/items/urn:wmo:md:in-imd:surface-based-observations.synop?f=json) explicitly declares `wmo:dataPolicy: core`. The [official WIS2 guide](https://wmo-im.github.io/wis2-guide/guide/wis2-guide-APPROVED.html) describes core data as free and unrestricted and encourages source attribution. No separate licence link was present in this dataset record. This supports use of this identified core dataset; it does not establish blanket rights or access to every IMD product.

**Limits:** Discovery metadata advertises an interval beginning **27 July 2024**, but this collection only verifies the requested day. It does not prove complete historical retention, station continuity, quality control, guaranteed refresh cadence or an availability SLA. The collection-level spatial extent also lists latitude endpoints in reverse order; the manifest therefore reports the actual observed point extent separately instead of silently trusting that bounding box. Neither report time nor the response-generation timestamp establishes when the observation first became available to a historical forecaster.

## NASA POWER environmental context at Patna

The [exact saved NASA query](https://power.larc.nasa.gov/api/temporal/hourly/point?parameters=T2M,RH2M,PS,WS10M,WD10M,PRECTOTCORR&community=AG&longitude=85.1376&latitude=25.5941&start=20240601&end=20240607&format=JSON&time-standard=UTC) requests **25.5941°N, 85.1376°E**, **1–7 June 2024**, and explicitly sets `time-standard=UTC`. The returned header confirms **UTC**, API **v2.10.2**, and sources **MERRA2, POWER**. Each parameter has all **168 hourly entries**, from `2024060100` to `2024060723`; there are no response messages or `-999.0` fill values.

| Parameter | Source description | Source unit |
|---|---|---|
| `T2M` | Temperature at 2 Meters | `C` |
| `RH2M` | Relative Humidity at 2 Meters | `%` |
| `PS` | Surface Pressure | `kPa` |
| `WS10M` | Wind Speed at 10 Meters | `m/s` |
| `WD10M` | Wind Direction at 10 Meters | `Degrees` |
| `PRECTOTCORR` | Precipitation Corrected | `mm/hour` |

NASA's [hourly documentation](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/) specifies hourly values and original source spatial support. Its [meteorological methodology](https://power.larc.nasa.gov/docs/methodology/meteorology/) describes MERRA-2 grid-box values on a **0.5° × 0.625°** grid. Accordingly, this is coarse environmental context sampled near Patna, **not a Patna ground station, radar observation or 2 km forecast field**. It cannot be made into independent high-resolution observations by interpolation.

The sample's date differs from the IMD sample's date. They must not be joined as simultaneous model inputs. Historical reanalysis availability also differs from operational forecast availability; `historical_available_at` remains null. Filling that field with this download's retrieval time would not reconstruct a valid historical operational input.

**Attribution:** NASA Langley Research Center POWER, funded through NASA's Earth Science Division; POWER Hourly API **v2.10.2**, accessed **30 September 2026**, with MERRA-2 source data. The [NASA referencing guide](https://power.larc.nasa.gov/docs/referencing/) requests provider/service/version/access-date references and publication/redistribution notification. No notification was sent. A standalone licence is not embedded in the downloaded JSON, so the manifest links the actual referencing guidance and records that limitation rather than inventing an SPDX licence.

## Reproduction and verification

[The collector](../scripts/collect_india_data.py) uses `requests`, connect/read timeouts of **10/40 seconds**, a checked per-file wall-clock budget of **90 seconds**, a **5 MB per-file limit**, and a **25 MB total directory limit**. The read timeout still bounds any individual blocked read between wall-clock checks. There is no unbounded pagination, polling, account creation, credential use or automatic retry storm. The selected region/day fits in one response; expansion would need explicit pagination and completeness checks.

Run from the repository root:

```powershell
.\.venv-data\Scripts\python.exe scripts\collect_india_data.py
.\.venv-data\Scripts\python.exe scripts\collect_india_data.py --verify-only
```

The existing `.venv-data` environment was supplied with `requests 2.34.2` and `truststore 0.10.4`. On Windows, truststore allows the OS certificate chain validation used successfully here; **certificate and hostname validation remain enabled**. The script otherwise uses requests' normal validation and records failures.

Files are written through a temporary file and atomic replacement. Existing artifacts must match their stored SHA-256 and size before reuse; changed source URLs or corrupted artifacts cause an error. This freezes the collected snapshot rather than silently refreshing it. The default rerun was tested with HTTP/HTTPS proxies pointing to an unreachable local port: it reused all **11 files**, returned success, and left every raw file **and the manifest byte-for-byte unchanged**. `--verify-only` and a separate SHA/count inspection also passed. Output remained **989,885 bytes**.

**Access failures were recorded, not bypassed:** the initial Python certifi request to IMD failed certificate-chain validation. Windows validated HTTPS and then requests using the OS trust store succeeded. The initially proposed `api.power.larc.nasa.gov` hostname failed DNS resolution; the endpoint documented by NASA, `power.larc.nasa.gov/api/`, returned HTTP 200. These exploratory failures and their resolutions are in `manifest.json` under `discovery_access_failures`; exact exploratory attempt seconds were not captured and are left null. Successful file retrieval timestamps are recorded individually. The wrong `/docs/faqs/general/` documentation path also returned HTTP 404 during discovery; it was not saved as a valid data source.

## What this enables next

This pack supports a real IMD ingestion adapter, unit/missingness handling, station lookup, timestamp/interval tests, and NASA environmental-data exploration. It provides concrete examples for the proposed provenance contracts and demonstrates that public Indian numerical observations are obtainable.

Training the proposed 30-minute lightning-occurrence model still needs suitably sampled Indian radar/satellite sequences, independently observed lightning targets, historical availability information, enough independent events and quiet periods, and an event-disjoint evaluation design. The present sparse SYNOP day and single-point NASA week are not that training corpus. They remain outside the existing simulation and forecasting paths.

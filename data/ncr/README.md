# Downloaded Delhi metro / NCR pilot observations

The [supplemental collection guide](../../docs/SUPPLEMENTAL_DATA_GUIDE.md) adds actual Open-Meteo, IEM, Meteostat and POWER samples, RainViewer frame references, IMERG catalogue records and numeric GFS fields. These are context or separately qualified evidence; they do not change the original IMD observation meanings below.

Collected 30 September 2026. The pilot rectangle is 76.5–78.0 degrees east and 28.0–29.3 degrees north. It includes Delhi-area station reports and is not the whole statutory NCR.

## Actual September station data

The IMD query covers 1–30 September 2026. The retained response contains **11,479 variable records from 631 station reports at four stations**: New Delhi/Palam, New Delhi/Safdarjung, Meerut and Rohtak. Latest report time is **30 September 12:00 UTC, 17:30 IST**. Station names are joined from the previously collected [IMD station catalogue](../government/india/imd_stations.json); per-observation coordinates remain unchanged even where catalogue coordinates differ.

- [Complete normalized observations, CSV](surface/runs/7e39147106ca7e0f0d9deb67f685c68967f4840987362657e0e916035bbc6947/observations.csv)
- [Categorical weather reports, CSV](surface/runs/7e39147106ca7e0f0d9deb67f685c68967f4840987362657e0e916035bbc6947/present_weather_labels.csv)
- [Measured precipitation intervals, CSV](surface/runs/7e39147106ca7e0f0d9deb67f685c68967f4840987362657e0e916035bbc6947/precipitation_labels.csv)
- [Source requests, hashes, counts and limitations](surface/runs/7e39147106ca7e0f0d9deb67f685c68967f4840987362657e0e916035bbc6947/manifest.json)
- [Packaged snapshot](../../artifacts/NCR_2026-09_observations.zip)

The manifest records a **partial** collection because one provider page reported a different total count: 11,000 versus 11,479. All 12 returned pages were downloaded, with 11,479 unique feature IDs and no conflicting records, but we do not certify complete archive coverage despite that metadata disagreement.

| Evidence found | Count | What it means |
|---|---:|---|
| Present-weather rain descriptions | 25 | Rain reported at a station observation time |
| Present-weather drizzle descriptions | 11 | Drizzle reported at a station observation time |
| Thunderstorm with rain and/or snow description | 5 | Mixed precipitation wording retained; not silently converted to rain-only truth |
| Explicit no-precipitation-at-observation description | 2 | Point-time absence, not a half-hour dry interval |
| Other/omitted present weather | 588 | Retained as unknown for this precipitation classifier; haze/mist are not proof of dry conditions |
| Explicit zero precipitation accumulations | 195 | Reported 0.0 water-equivalent over one-hour intervals |
| Exact measured 30-minute accumulation labels | 0 | No such labels were obtained in this collection |

Example wet observations: Meerut reported continuous rain on 2 September at 03:00 UTC; Palam reported continuous drizzle at that same observation time. All categorical descriptions and original timestamps are preserved. These are observations, not model forecasts.

The positive weather reports and zero accumulation measurements describe different observation semantics and possibly different times. Do not overwrite one with the other. Never spread an hourly amount across two invented half-hours. A station report does not label every surrounding map pixel. The source reports total precipitation water equivalent in kg/m², numerically equivalent to liquid-water depth in mm, but precipitation phase and instrument detection limits are not established by that field alone.

## Current satellite-derived sample

[Satellite snapshot manifest](satellite/snapshots/4c4980b3dbe4ef3aa8e6a216be0b12d7facaa2693fc53075998b66245d2493ae/manifest.json) records a **162,456-byte public IMD BUFR payload**. It contains satellite-derived wind information, not calibrated image arrays. Publication time is 30 September 15:20:01 UTC; first BUFR message typical time is 13:15 UTC. Full coordinate decoding and NCR coverage remain unverified. The file is an all-domain source sample awaiting filtering, not an NCR training image. The [discovery record](satellite/wis2_satellite_discovery.json) retains earlier source investigation.

## Scientific satellite imagery located, not downloaded

The public MOSDAC catalogue returned **30 INSAT-3DS L1B matches** for 30 September and this bounding box, with provider-estimated total size **12,972 MB**. Only two catalogue entries were requested and saved, covering **14:00–14:30 and 14:30–15:00 UTC**. This is metadata, not 13 GB of downloaded imagery. The returned spatial extent is a full scene; a search box is not a downloaded NCR crop.

See the [MOSDAC preview](mosdac/previews/eeb9e6055e622e99aba107cc94ba975936db1084449381c3c2b8dabbdbc59753/manifest.json) and its [original response](mosdac/previews/eeb9e6055e622e99aba107cc94ba975936db1084449381c3c2b8dabbdbc59753/response.json). The provider's catalogue-updated timestamp is preserved verbatim and was ahead of retrieval time; it is not used as observation time.

Approved MOSDAC credentials are still required for scientific downloads. Numeric Delhi radar sequences and lightning event labels are also outstanding. No current 30-minute NCR training corpus or validated NCR model has been created from these files.

## Reproduce and use

Commands, API endpoints and the architecture are in the [NCR backend guide](../../docs/NCR_BACKEND_GUIDE.md). Checkpoint reuse and causal inference are in the [model guide](../../docs/NCR_MODEL_GUIDE.md). The [research note](../../research/NCR_DATA_AND_GOOGLE_MODEL_RESEARCH.md) links official data providers, terms and the verified Google model details.

Raw files are content-addressed, manifests preserve request and retrieval times, and CSV/JSON derivatives retain their source hashes. Provider publication, observation and retrieval timestamps are different fields. Verify hashes before reuse; source accessibility does not establish completeness, a public-warning licence, or model skill.

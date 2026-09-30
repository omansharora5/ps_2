# NOAA numeric starter collection

Collected and verified **30 September 2026**. Five unmodified NOAA-produced files total **4,934,674 bytes (4.93 MB)**, below the 40 MB raw-data limit. These are historical **parser/reference fixtures**, not a training corpus or Indian observations. No model or application integration was changed.

## Files and actual decoded content

The [machine-readable manifest](../data/government/noaa/manifest.json) has a top-level `files` list with root-relative paths, exact source URLs, providers/distribution mirrors, retrieval times, bytes, SHA-256, formats, observation times, geography, units, terms, data role and limitations. It also records variable shapes, packing attributes, decoded ranges and missing-value handling.

All observation times below are UTC on **15 June 2024**, a fixed historical date chosen for reproducible access, without asserting a particular severe-weather case.

| Manifest ID | Original product | Observation time | Bytes | Parsed result |
|---|---|---|---:|---|
| `abi_c13` | GOES-16 ABI `ABI-L2-CMIPC`, mode 6, channel 13, CONUS | 18:01:17.8–18:03:56.3 | 4,089,488 | `CMI(y,x)` = **1,500 × 2,500**, brightness temperature in K; **3,702,838** valid values, **187.761–327.875 K** |
| `glm_180200` | GOES-16 `GLM-L2-LCFA` | 18:02:00–18:02:20 | 188,220 | **2,182 events / 967 groups / 87 flashes** |
| `glm_180220` | GOES-16 `GLM-L2-LCFA` | 18:02:20–18:02:40 | 202,556 | **2,800 events / 1,222 groups / 94 flashes** |
| `glm_180240` | GOES-16 `GLM-L2-LCFA` | 18:02:40–18:03:00 | 198,460 | **2,407 events / 1,119 groups / 93 flashes** |
| `radar_ktlx_n0b` | NEXRAD Level III, KTLX `N0B`, product code **153** | Volume start **18:05:28**; product time **18:06:40** | 255,950 | **720 × 1,840** encoded reflectivity bins; **375,181** finite decoded values, **−17.0 to 47.5 dBZ** |

These are results read from the downloaded files. The ABI `CMI` storage is signed `int16` with unsigned interpretation, scale factor and offset; treating stored integers as Kelvin would be wrong. Automatic NetCDF masking/scaling was enabled. Its 47,162 masked pixels were excluded from the range; all 3,702,838 unmasked DQF values are zero. The manifest preserves the original quality definitions and fixed-grid projection.

GLM coordinates use degrees north/east, energies use joules, flash area uses square metres, and event/flash time offsets use seconds from the per-file UTC origin. Every event-parent-group and group-parent-flash link resolves within its file. Per-file flash records must not be blindly summed into a claim about unique ground strikes. GLM optical lightning events, groups and flashes are different objects; the original product preserves their relationships. [NOAA GLM dataset definition and citation](https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc:C01527/html).

The three GLM file coverage intervals are adjacent and lie inside the ABI scan interval. Their geographic extent is wider: observed event coordinates across the files span approximately **29.55°S to 53.37°N** and **118.34°W to 42.70°W**. Temporal overlap does not establish pixelwise collocation or useful labels. The KTLX radar site is **35.333°N, 97.278°W**, with a decoded maximum product range of 460 km. Its scan begins after the ABI/GLM sample; it is a separate radar-parser fixture. A complete radar scan end is not asserted and remains `null` in the manifest.

## Official provenance and access

1. **Satellite:** [NOAA NCEI ABI CMIP catalog, DOI 10.7289/V5736P36](https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C01502) directly lists the `noaa-goes16` AWS public archive used here. It describes CMIP as numeric NetCDF4 imagery and distinguishes CONUS, full-disk and mesoscale scenes. Channel 13 is the clean infrared band, approximately 10.3 µm. [NOAA channel explanation](https://prod-01-alb-www-noaa.woc.noaa.gov/jetstream/satellites/goes-west-goes-17).
2. **Lightning:** [NOAA NCEI GLM LCFA catalog, DOI 10.7289/V5KH0KK6](https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc:C01527/html) describes the 20-second event/group/flash product. These numeric files were downloaded from the NOAA GOES-16 AWS bucket without credentials.
3. **Radar:** [NOAA NCEI Level III catalog, DOI 10.25921/ncz0-wn95](https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C00708) establishes NOAA/NWS production. The individual object came from **UCAR Unidata’s `unidata-nexrad-level3` AWS distribution mirror**, explicitly distinguished from a NOAA-operated host. The [current NEXRAD AWS registry](https://registry.opendata.aws/noaa-nexrad/) names that mirror; [NOAA’s cloud-access documentation](https://www.ncei.noaa.gov/products/ncei-data-noaa-open-dissemination-program) documents dissemination of the NEXRAD archive through cloud partners. [NWS product cross-reference](https://www.weather.gov/source/datamgmt/xr04_X_ref_by_NNN.html) identifies N0B as reflectivity product 153.

Use the dataset citations above with the subset and access date. [NCEI’s Open Data Policy](https://www.ncei.noaa.gov/sites/default/files/2023-12/NCEI%20PD-10-2-02%20-%20Open%20Data%20Policy%20Signed.pdf) describes NOAA data as public domain in the United States. Dataset-specific citation and use constraints remain linked per manifest entry. The distribution registry requests attribution and prohibits implying NOAA endorsement; modified products must be labelled as modified. No global rights claim was inferred solely from an open download URL.

## Reproduce and verify

The collector is [scripts/collect_noaa_data.py](../scripts/collect_noaa_data.py). Its URLs, sizes and SHA-256 hashes are pinned to this exact sample. It enforces a 40,000,000-byte raw collection limit, downloads to temporary files, rejects HTML and wrong lengths/hashes, parses before publishing each raw file, and writes manifests atomically. It refuses to overwrite modified or untracked originals. Partial successful entries are retained for retry; a lock prevents concurrent collectors. Download exceptions, if any, are written to `download_failures.json`.

The separate `.venv-data` environment contains the parsers; the existing application environment was not modified. The tested environment used **Python 3.14**, **netCDF4 1.7.4** and **MetPy 1.7.1**. [Pinned environment packages](../data/government/noaa/parser-requirements.txt) record all installed dependency versions. MetPy's Level3File handles the NIDS product encoding and converts reflectivity levels with `map_data`. [Parser documentation](https://unidata.github.io/MetPy/latest/api/generated/metpy.io.Level3File.html).

```powershell
# From the repository root, only if the isolated environment is absent:
python -m venv .venv-data
.\.venv-data\Scripts\python.exe -m pip install -r data/government/noaa/parser-requirements.txt

# Fetch the fixed collection, or verify/reuse already collected originals:
.\.venv-data\Scripts\python.exe scripts/collect_noaa_data.py

# Recheck local files without network access or writes:
.\.venv-data\Scripts\python.exe scripts/collect_noaa_data.py --verify-only
```

**Executed checks:** initial download/decoding, offline verification, and a repeated collection. All passed. The repeated collection left every raw file's SHA-256 and modification time unchanged and reproduced the manifest byte for byte. No `.part` files remain. [Verification record](../data/government/noaa/verification.json).

## Access limits and unsuccessful alternatives

- The official GCP KTLX Level III **day bundle** for 15 June 2024 was listed at **439,598,712 bytes**. Its payload was not downloaded because it exceeds this task's limit; an individual N0B object was selected instead.
- The queried historical `TLX_N0Q_2024_06_15_18` AWS prefix returned zero keys. This is an empty query result, not evidence that NOAA radar data are unavailable. The N0B prefix returned eight objects.
- Several NOAA documentation URLs were not extractable through the browser tool. Direct HTTPS access retrieved the official NCEI cloud-access page; alternate official catalog endpoints supplied product metadata. No TLS verification was disabled and no account or authentication workaround was used.
- All five selected raw object downloads succeeded. Discovery/access outcomes are recorded in [access_attempts.json](../data/government/noaa/access_attempts.json).

## Appropriate use and outstanding work

This pack supports real parser, unit conversion, timestamp, quality-mask, parent-link and georeferencing experiments. It is **not** enough for model fitting, calibration, storm tracking, skill estimation or a real nowcast. A single ABI image cannot establish cloud motion. One minute of GLM files cannot establish a 30-minute future-occurrence target. These western-hemisphere products do not cover India and are not substitutes for Indian radar, INSAT, lightning-network or NWP access.

Future dataset construction needs contiguous history and future-label windows, validated space/time alignment, quality/parallax handling, missing-data masks, geographically relevant sampling, storm-separated evaluation and recorded operational availability. `retrieved_at_utc` is this collection's download time. Product creation times and archive modification dates are not proven historical delivery times; `historical_available_at_utc` is therefore deliberately `null`. The collected files have **not entered the simulator-trained model**.

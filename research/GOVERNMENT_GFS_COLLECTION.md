# NOAA GFS collection and decoding evidence

Collected 30 September 2026. [Manifest](../data/government/gfs/manifest.json), [decoded inspection](../data/government/gfs/inspection.json), [collector](../scripts/collect_gfs_data.py).

The source is the NOAA/NCEP GFS 0.25° product, initialized **12 May 2025 at 06 UTC**, forecast lead **3 hours**, valid **09 UTC**. [Official NCEI GFS documentation](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast) links the cloud distribution. The exact [source inventory](https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.20250512/06/atmos/gfs.t06z.pgrb2.0p25.f003.idx) returned HTTP 200.

Seven complete original GRIB2 messages were obtained with HTTP byte-range requests and concatenated without changing values: 2 m temperature and relative humidity; 10 m eastward/northward wind; surface CAPE/CIN; entire-atmosphere precipitable water. The manifest records each byte range, unit, SHA-256 and archive header. The saved index is **40,472 bytes** and selected raw messages are **5,302,691 bytes**. The collector rejects a full-object response to a Range request, unexpected Content-Range, over-budget content and incomplete GRIB framing.

NOAA wgrib2 **3.1.3** decoded the file. The Python ecCodes wrapper installed in an isolated experimental environment could not locate its native library on this Windows system. It was not treated as a successful decoder. The official [NOAA Windows binary directory](https://ftp.cpc.ncep.noaa.gov/wd51we/wgrib2/Windows10/v3.1.3/) supplied wgrib2 and its DLLs; provenance remains in `tools/wgrib2/provenance.json`.

The command `-small_grib 82:89 23:28` selected **29 longitude × 21 latitude = 609 grid points**, including Bihar and surrounding areas. The resulting regional GRIB was converted with `-csv` to **4,263 rows** across the seven variables. [NOAA CSV documentation](https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/csv.html) defines reference time, valid time, field, level, longitude, latitude and value. Original physical units were retained. The derived regional GRIB and CSV have independent hashes and a transformation record.

The [data inventory](../data/government/README.md) gives variable ranges and file links. The independent verification confirmed every CSV reference time as 06 UTC and valid time as 09 UTC, all seven variables, file checksums and seven complete messages. Truncated GRIB, an HTML payload and appended junk were rejected. A repeat collector run verified raw and derived checksums without rewriting them.

**Availability limitation:** HTTP Last-Modified is 09:37:05 UTC for the selected archive object, with a slightly later index modification. This is object metadata, not proof of when the operational system first offered the product. `historical_available_at_utc` remains null. The 09 UTC valid time must not be mistaken for an arrival time or used to justify an earlier operational forecast.

**Scientific limitation:** these are model forecast values at one time. They are not surface observations, a thunderstorm forecast or lightning labels. Native 0.25° output is coarse environmental context. The surface-only selected wind fields cannot produce vertical wind shear. This date does not coincide with the IMD or NASA samples and has no paired Indian target observations.

**Terms:** retain NOAA/NCEP source attribution and do not imply endorsement. The manifest links the [NWS disclaimer](https://www.weather.gov/disclaimer). One working historical archive URL does not establish unlimited retention or a service guarantee.

# NCR supplemental samples

Collected on 30 September 2026. Raw responses, normalized rows and checksum manifests are kept together in each source directory. The collectors publish complete snapshots atomically and reuse matching requests/content on retries.

| Directory | Rows | Content |
| --- | ---: | --- |
| `open_meteo` | 48 | Hourly GFS model context for a Delhi point, 30 Sep to 1 Oct |
| `iem` | 554 | VIDP/VIDD reports from 23 through 29 Sep, including 20 present rain/drizzle codes |
| `meteostat` | 168 | Delhi Palam hourly values, with per-variable source metadata |
| `power` | 168 | Delhi requested environmental hours, 144 with values and 24 missing |
| `rainviewer` | 13 | Past radar frame references; coverage and individual scan times unverified |
| `imerg` | 48 | Early V07 catalogue entries, not downloaded precipitation arrays |

See the [collection, API and training guide](../../../docs/SUPPLEMENTAL_DATA_GUIDE.md) for commands and access requirements, and the [provider review](../../../research/SUPPLEMENTAL_WEATHER_SOURCES.md) for primary references. The relative links above traverse from `data/ncr/supplemental` to the repository root.

`raw.bin` preserves provider bytes. Formats are JSON for Open-Meteo/POWER/RainViewer/IMERG, CSV for IEM and compressed CSV for Meteostat. `rows.json` contains normalized records. `manifest.json` records exact source requests, retrieval time, role, limitations and file hashes; `manifest.sha256` checks the manifest itself.

These records do not constitute matched 30-minute NCR training episodes. No row in this collection is admitted automatically as rain ground truth. Unreported station weather stays unknown, Indian IEM numeric precipitation is withheld, and model-filled values retain their provenance. See the neighbouring [GFS snapshot](../gfs/gfs_20260930_12_f003_ncr/manifest.json) for actual numeric forecast fields.

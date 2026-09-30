"""Collect a bounded public IMD/NASA starter pack without changing model inputs.

Run with requests and (recommended on Windows) truststore installed.
Existing files are checksum-verified and reused; --verify-only performs no HTTP.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/government/india"
MANIFEST = OUT / "manifest.json"
BUDGET = 25_000_000
PER_FILE = 5_000_000
IMD = "https://wis2box.imd.gov.in/oapi/collections"
SYNOP = "urn:wmo:md:in-imd:surface-based-observations.synop"
WMO_TERMS = "https://wmo-im.github.io/wis2-guide/guide/wis2-guide-APPROVED.html"
NASA_TERMS = "https://power.larc.nasa.gov/docs/referencing/"
NASA_LIMITS = (
    "NASA POWER requests project/service/version/access-date attribution and publication/redistribution notification. "
    "The JSON response does not include a standalone licence. No notification has been sent; "
    "no service SLA or historical forecast availability is established."
)
NASA_URL = (
    "https://power.larc.nasa.gov/api/temporal/hourly/point?"
    "parameters=T2M,RH2M,PS,WS10M,WD10M,PRECTOTCORR&community=AG"
    "&longitude=85.1376&latitude=25.5941&start=20240601&end=20240607"
    "&format=JSON&time-standard=UTC"
)


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(body):
    return hashlib.sha256(body).hexdigest()


def atomic_write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def persisted_bytes():
    return sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())


def verify_file(entry):
    path = (ROOT / entry["path"]).resolve()
    if not path.is_relative_to(OUT.resolve()):
        raise ValueError("Manifest path leaves owned output directory")
    body = path.read_bytes()
    if len(body) != entry["bytes"] or digest(body) != entry["sha256"]:
        raise ValueError(f"Existing artifact differs from manifest: {entry['path']}")
    return body


def bounds(features):
    coordinates = [f["geometry"]["coordinates"] for f in features
                   if f.get("geometry", {}).get("type") == "Point"]
    if not coordinates:
        return None
    return [min(c[0] for c in coordinates), min(c[1] for c in coordinates),
            max(c[0] for c in coordinates), max(c[1] for c in coordinates)]


def inspect_json(kind, obj):
    result = {"observed_time_range": None, "timezone": None, "geography": None,
              "units": {}, "inspection": {}}
    if kind in ("synop", "stations"):
        features = obj.get("features", [])
        result["geography"] = {"country": "India", "crs": "OGC:CRS84",
                               "observed_point_bbox_lon_lat": bounds(features)}
        result["inspection"] = {
            "feature_count": len(features), "number_matched": obj.get("numberMatched"),
            "number_returned": obj.get("numberReturned"),
            "has_next_page": any(link.get("rel") == "next" for link in obj.get("links", [])),
        }
        if kind == "stations":
            result["inspection"]["station_names"] = sorted(
                {f["properties"].get("name", "") for f in features})
            return result
        properties = [f["properties"] for f in features]
        report_times = sorted({p["reportTime"] for p in properties})
        phenomena = [t for p in properties for t in p.get("phenomenonTime", "").split("/") if t]
        units = defaultdict(set)
        field_counts = Counter()
        numeric = 0
        for p in properties:
            units[p["name"]].add(p.get("units"))
            field_counts[p["name"]] += 1
            value = p.get("value")
            numeric += isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        result["units"] = {key: sorted(values, key=str) for key, values in sorted(units.items())}
        result["timezone"] = "UTC (source timestamps end in Z)"
        result["observed_time_range"] = {
            "report_time_start": min(report_times) if report_times else None,
            "report_time_end": max(report_times) if report_times else None,
            "phenomenon_time_start": min(phenomena) if phenomena else None,
            "phenomenon_time_end": max(phenomena) if phenomena else None,
            "historical_available_at": None,
        }
        result["inspection"].update({
            "unique_feature_ids": len({f["id"] for f in features}),
            "numeric_value_count": numeric,
            "null_value_count": sum(p.get("value") is None for p in properties),
            "station_count": len({p["wigos_station_identifier"] for p in properties}),
            "station_ids": sorted({p["wigos_station_identifier"] for p in properties}),
            "report_count": len({p["reportId"] for p in properties}),
            "report_times": report_times, "field_counts": dict(sorted(field_counts.items())),
            "source_response_timestamp": obj.get("timeStamp"),
        })
    elif kind == "power":
        parameters = obj["properties"]["parameter"]
        keys = sorted({t for values in parameters.values() for t in values})
        fill = obj["header"]["fill_value"]
        result.update({
            "observed_time_range": {
                "valid_time_start": datetime.strptime(keys[0], "%Y%m%d%H").isoformat() + "Z",
                "valid_time_end": datetime.strptime(keys[-1], "%Y%m%d%H").isoformat() + "Z",
                "historical_available_at": None,
            },
            "timezone": obj["header"]["time_standard"],
            "geography": {"country": "India", "requested_place": "Patna, Bihar",
                           "requested_longitude": 85.1376, "requested_latitude": 25.5941,
                           "response_geometry": obj["geometry"],
                           "spatial_support": "Source grid-box average, not an in-situ Patna station"},
            "units": {key: value["units"] for key, value in obj["parameters"].items()},
            "inspection": {
                "hour_count": len(keys), "parameter_count": len(parameters),
                "scalar_count": sum(len(v) for v in parameters.values()),
                "fill_value": fill,
                "missing_value_count": sum(v == fill for values in parameters.values() for v in values.values()),
                "per_parameter_count": {key: len(values) for key, values in parameters.items()},
                "source_header": obj["header"], "source_parameters": obj["parameters"],
                "response_messages": obj.get("messages", []),
            },
        })
    return result


def specs():
    return [
        ("imd_collections", "imd_collections.json", IMD + "?f=json", "catalog"),
        ("imd_synop_metadata", "imd_synop_metadata.json", f"{IMD}/discovery-metadata/items/{SYNOP}?f=json", "metadata"),
        ("imd_synop_queryables", "imd_synop_queryables.json", f"{IMD}/{SYNOP}/queryables?f=json", "schema"),
        ("imd_stations", "imd_stations.json", IMD + "/stations/items?f=json&limit=1000", "stations"),
        ("imd_synop_bihar_region_20260929", "imd_synop_bihar_region_20260929.geojson",
         f"{IMD}/{SYNOP}/items?f=json&limit=1000&bbox=84,24,86,27"
         "&datetime=2026-09-29T00:00:00Z/2026-09-29T23:59:59Z", "synop"),
        ("nasa_power_patna_20240601_20240607", "nasa_power_patna_20240601_20240607.json", NASA_URL, "power"),
        ("nasa_power_hourly_docs", "nasa_power_hourly_docs.html", "https://power.larc.nasa.gov/docs/services/api/temporal/hourly/", "documentation"),
        ("nasa_power_meteorology_docs", "nasa_power_meteorology_docs.html", "https://power.larc.nasa.gov/docs/methodology/meteorology/", "documentation"),
        ("nasa_power_acknowledgements", "nasa_power_acknowledgements.html", "https://power.larc.nasa.gov/docs/acknowledgements/", "documentation"),
        ("nasa_power_referencing", "nasa_power_referencing.html", NASA_TERMS, "documentation"),
        ("wmo_wis2_guide", "wmo_wis2_guide.html", WMO_TERMS, "documentation"),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {
        "schema_version": 1, "collection": "India government surface observations and NASA environmental starter pack",
        "created_at_utc": utc_now(), "budget_bytes": BUDGET,
        "raw_policy": "Unmodified HTTP response bodies after standard content-transfer decoding; no reserialization, filtering or value conversion",
        "training_ready": False, "files": [], "access_failures": [],
    }
    for entry in manifest["files"]:
        if entry["id"].startswith("nasa_"):
            entry["licence_terms_url"] = NASA_TERMS
            entry["unresolved_limits"] = NASA_LIMITS
    existing = {entry["id"]: entry for entry in manifest["files"]}
    for entry in existing.values():
        verify_file(entry)
    if args.verify_only:
        if not existing:
            raise SystemExit("No manifest files to verify")
        if persisted_bytes() > BUDGET:
            raise SystemExit("Output directory exceeds the declared byte budget")
        print(json.dumps({"verified_files": len(existing), "raw_bytes": sum(e["bytes"] for e in existing.values()),
                          "directory_bytes": persisted_bytes(), "within_budget": persisted_bytes() <= BUDGET}))
        return
    try:
        import truststore
        truststore.inject_into_ssl()
        tls_backend = "OS trust store via truststore; hostname and certificate verification enabled"
    except ImportError:
        tls_backend = "requests default certificate verification; truststore unavailable"
    import requests
    session = requests.Session()
    session.headers.update({"User-Agent": "VAJRA-research-starter-pack/1.0", "Accept-Encoding": "identity"})

    def save_manifest():
        manifest["raw_bytes"] = sum(e["bytes"] for e in manifest["files"])
        payload = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        current_size = MANIFEST.stat().st_size if MANIFEST.exists() else 0
        if persisted_bytes() - current_size + len(payload) > BUDGET:
            raise RuntimeError("Manifest would exceed total output budget")
        atomic_write(MANIFEST, payload)

    failed = False
    for identity, filename, url, kind in specs():
        if identity in existing:
            if existing[identity]["source_url"] != url:
                raise ValueError(f"Source URL changed for existing artifact: {identity}")
            print("REUSED", identity)
            continue
        started = time.monotonic()
        try:
            with session.get(url, timeout=(10, 40), stream=True) as response:
                response.raise_for_status()
                if response.status_code != 200:
                    raise ValueError(f"Expected HTTP 200, got {response.status_code}")
                chunks = []
                size = 0
                for chunk in response.iter_content(chunk_size=65536):
                    size += len(chunk)
                    if size > PER_FILE or persisted_bytes() + size + 100_000 > BUDGET:
                        raise ValueError("Download budget exceeded")
                    if time.monotonic() - started > 90:
                        raise TimeoutError("Per-file wall-clock budget exceeded")
                    chunks.append(chunk)
                body = b"".join(chunks)
                media = response.headers.get("Content-Type", "application/octet-stream")
                obj = json.loads(body) if kind != "documentation" else None
                inspection = inspect_json(kind, obj) if obj is not None else {
                    "observed_time_range": None, "timezone": None, "geography": None, "units": {}, "inspection": {}}
                provider = "India Meteorological Department (IMD)" if identity.startswith("imd_") else (
                    "NASA Langley Research Center POWER / NASA GMAO MERRA-2" if identity.startswith("nasa_") else "World Meteorological Organization")
                role = {"synop": "sparse surface station observations for adapter/QC development",
                        "power": "historical coarse-grid meteorological context; reanalysis-derived",
                        "stations": "station reference metadata"}.get(kind, "provenance and source documentation")
                reason = {"synop": "Single bounded region/day; not radar or lightning labels; includes null/code-table values, heterogeneous phenomenon intervals, and unknown historical publication latency.",
                          "power": "One grid location and seven days at hourly cadence; no lightning/radar labels; retrospective values do not prove operational availability and do not align in date with the IMD sample."}.get(kind, "Metadata/documentation only, not model examples or outcome labels.")
                terms = WMO_TERMS if identity.startswith("imd_") or identity.startswith("wmo_") else NASA_TERMS
                limits = ("IMD SYNOP discovery metadata declares wmo:dataPolicy=core. No separate explicit licence URL was present in that dataset record. This classification does not grant blanket access to other IMD products or imply archive completeness/SLA."
                          if identity.startswith("imd_") else (NASA_LIMITS if identity.startswith("nasa_") else "Retain provider attribution; this policy guide does not establish any particular dataset's completeness or operational SLA."))
                entry = {"id": identity, "path": (OUT / filename).relative_to(ROOT).as_posix(),
                         "source_url": url, "resolved_url": response.url, "provider": provider,
                         "retrieved_at_utc": utc_now(), "bytes": len(body), "sha256": digest(body),
                         "media_type": media, "format": "HTML" if obj is None else ("GeoJSON" if obj.get("type") in ("Feature", "FeatureCollection") else "JSON"),
                         "http_status": response.status_code, "http_date": response.headers.get("Date"),
                         "etag": response.headers.get("ETag"), "tls_verification": tls_backend,
                         "licence_terms_url": terms, "unresolved_limits": limits,
                         "data_role": role, "not_training_ready_reason": reason, **inspection}
            atomic_write(OUT / filename, body)
            manifest["files"].append(entry)
            save_manifest()
            print("SAVED", identity, len(body))
        except (requests.RequestException, ValueError, TimeoutError) as exc:
            failed = True
            manifest["access_failures"].append({"id": identity, "source_url": url,
                                                "attempted_at_utc": utc_now(), "error_type": type(exc).__name__,
                                                "error": str(exc), "tls_verification_disabled": False})
            save_manifest()
            print("FAILED", identity, type(exc).__name__, str(exc))
    session.close()
    if persisted_bytes() > BUDGET:
        raise RuntimeError("Output budget exceeded")
    print(json.dumps({"files": len(manifest["files"]), "raw_bytes": manifest.get("raw_bytes", 0),
                      "directory_bytes": persisted_bytes(), "manifest": str(MANIFEST)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

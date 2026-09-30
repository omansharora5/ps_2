"""Bounded, provenance-preserving IMD surface collection for a Delhi metro pilot."""

from collections import Counter
from datetime import date, datetime, timedelta, timezone
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "data/ncr/surface"
BASE = "https://wis2box.imd.gov.in/oapi/collections"
COLLECTION = "urn:wmo:md:in-imd:surface-based-observations.synop"
BBOX = (76.5, 28.0, 78.0, 29.3)
REGION = {"id": "delhi_metro_pilot_v1", "bbox_lon_lat": list(BBOX),
          "description": "Delhi and nearby NCR locations; rectangle, not the statutory NCR boundary"}
PRECIP = "total_precipitation_or_total_water_equivalent"
PAGE_BYTES = 4_000_000
TOTAL_BYTES = 40_000_000
NORMALIZER_VERSION = 2


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def instant(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValueError("Explicit UTC timestamps required")
    return result


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def digest(body):
    return hashlib.sha256(body).hexdigest()


def atomic(path, body):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".ncr-", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def blob(root, body):
    sha = digest(body)
    path = Path(root) / "raw" / (sha + ".json")
    if path.exists():
        if digest(path.read_bytes()) != sha:
            raise ValueError("Existing content-addressed raw file is corrupt")
    else:
        atomic(path, body)
    return {"path": path.relative_to(root).as_posix(), "sha256": sha, "bytes": len(body)}


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def normalize(feature, raw_sha, retrieved_at):
    props = feature["properties"]
    if feature.get("geometry", {}).get("type") != "Point":
        raise ValueError("Surface observation must have point geometry")
    lon, lat = feature["geometry"]["coordinates"][:2]
    if number(lon) is None or number(lat) is None or not BBOX[0] <= lon <= BBOX[2] or not BBOX[1] <= lat <= BBOX[3]:
        raise ValueError("Provider returned a point outside the requested region")
    report = props["reportTime"]
    instant(report)
    if instant(report) > instant(retrieved_at):
        raise ValueError("Observation report time is in the future")
    return {"feature_id": str(feature["id"]), "report_id": props["reportId"],
            "station_id": props["wigos_station_identifier"], "longitude": lon, "latitude": lat,
            "variable": props["name"], "units": props.get("units"), "value": number(props.get("value")),
            "source_description": props.get("description"), "report_time_utc": report,
            "phenomenon_time_utc": props.get("phenomenonTime"), "raw_sha256": raw_sha,
            "retrieved_at_utc": retrieved_at, "historical_available_at_utc": None}


def precipitation_label(record):
    if record["variable"] != PRECIP:
        return None
    result = {key: record[key] for key in ("feature_id", "station_id", "longitude", "latitude", "report_time_utc", "raw_sha256")}
    result.update({"state": "unknown", "amount_mm": None, "interval_start_utc": None,
                   "interval_end_utc": None, "duration_minutes": None,
                   "eligible_as_exact_30_minute_label": False,
                   "interpretation": "Reported precipitation water equivalent at one station; phase and instrument detection limit unverified"})
    try:
        start, end = record["phenomenon_time_utc"].split("/")
        minutes = (instant(end) - instant(start)).total_seconds() / 60
        if minutes <= 0 or instant(end) > instant(record["report_time_utc"]):
            raise ValueError("Invalid accumulation interval")
        result.update(interval_start_utc=start, interval_end_utc=end, duration_minutes=minutes)
    except (ValueError, TypeError, AttributeError):
        result["reason"] = "Missing or invalid accumulation interval"
        return result
    value = record["value"]
    if record["units"] not in ("kg m-2", "kg m**-2", "kg/m2", "mm") or value is None or value < 0:
        result["reason"] = "Unknown unit, missing value, or negative/trace code requiring provider interpretation"
        return result
    result.update(state="wet" if value > 0 else "reported_zero", amount_mm=float(value),
                  eligible_as_exact_30_minute_label=minutes == 30,
                  reason="Positive accumulation" if value > 0 else "Explicit measured zero; missing records are never zero")
    return result


def present_weather_label(record):
    if record["variable"] != "present_weather":
        return None
    # Exact provider descriptions, not a substring match that could turn "no rain" into rain.
    categories = {
        "RAIN, NOT FREEZING, CONTINUOUS": "rain",
        "RAIN, NOT FREEZING, INTERMITTENT": "rain",
        "RAIN (NOT FREEZING)": "rain",
        "DRIZZLE, NOT FREEZING, CONTINUOUS": "drizzle",
        "DRIZZLE, NOT FREEZING, INTERMITTENT": "drizzle",
        "THUNDERSTORM, SLIGHT OR MODERATE, WITHOUT HAIL*, BUT WITH RAIN AND/OR SNOW AT TIME OF OBSERVATION": "thunderstorm_with_rain_or_snow",
        "THUNDERSTORM, BUT NO PRECIPITATION AT THE TIME OF OBSERVATION": "explicit_no_precipitation",
    }
    category = categories.get(record["source_description"], "unknown")
    if record.get("conflicting_provider_versions"):
        category = "unknown"
    return {"feature_id": record["feature_id"], "station_id": record["station_id"],
            "longitude": record["longitude"], "latitude": record["latitude"],
            "observed_at_utc": record["phenomenon_time_utc"], "category": category,
            "provider_description": record["source_description"], "raw_sha256": record["raw_sha256"],
            "eligible_as_exact_30_minute_label": False,
            "interpretation": "Categorical present-weather report at a station; not an accumulated amount or a 30-minute coverage label"}


def normalize_pages(pages):
    records, conflicts = {}, set()
    for obj, evidence in pages:
        if obj.get("type") != "FeatureCollection" or not isinstance(obj.get("features"), list):
            raise ValueError("Expected an IMD GeoJSON FeatureCollection")
        for feature in obj["features"]:
            record = normalize(feature, evidence["sha256"], evidence["retrieved_at_utc"])
            previous = records.get(record["feature_id"])
            keys = ("station_id", "variable", "units", "value", "source_description", "phenomenon_time_utc", "report_time_utc", "longitude", "latitude")
            if previous and any(previous[k] != record[k] for k in keys):
                conflicts.add(record["feature_id"])
            records.setdefault(record["feature_id"], record)
    for identifier in conflicts:
        records[identifier]["value"] = None
        records[identifier]["conflicting_provider_versions"] = True
    rows = sorted(records.values(), key=lambda r: (r["report_time_utc"], r["station_id"], r["feature_id"]))
    return rows, [label for row in rows if (label := precipitation_label(row)) is not None], sorted(conflicts)


def request_url(start, end):
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if start > end or (end - start).days > 92 or end > datetime.now(timezone.utc).date():
        raise ValueError("Choose an ordered window of at most 93 days ending no later than today UTC")
    params = {"f": "json", "limit": 1000, "bbox": ",".join(map(str, BBOX)),
              "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z", "sortby": "reportTime"}
    return f"{BASE}/{COLLECTION}/items?" + urlencode(params)


def next_url(obj):
    links = [link["href"] for link in obj.get("links", []) if link.get("rel") == "next"]
    if not links:
        return None
    if len(links) != 1:
        raise ValueError("Ambiguous pagination")
    parts = urlsplit(links[0])
    expected = urlsplit(f"{BASE}/{COLLECTION}/items")
    if parts.scheme != "https" or parts.netloc != expected.netloc or parts.path != expected.path or parts.fragment:
        raise ValueError("Pagination leaves the documented IMD collection")
    params = dict(parse_qsl(parts.query))
    params["f"] = "json"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), ""))


def fetch(url):
    import requests
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass
    with requests.get(url, timeout=(10, 30), stream=True, allow_redirects=False,
                      headers={"User-Agent": "VAJRA-NCR-research/1", "Accept": "application/geo+json,application/json"}) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("Unexpected provider response")
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > PAGE_BYTES:
                raise ValueError("Provider page exceeds bounded download size")
            chunks.append(chunk)
        return b"".join(chunks)


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    if rows:
        fields = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def collect(root, start, end, *, refresh=False, getter=fetch):
    root = Path(root).resolve()
    url = initial_url = request_url(start, end)
    window_start = instant(f"{start}T00:00:00Z")
    window_end = instant(f"{end}T00:00:00Z") + timedelta(days=1)
    root.mkdir(parents=True, exist_ok=True)
    if not refresh:
        for existing in reversed(sorted((root / "runs").glob("*/manifest.json"))):
            previous = json.loads(existing.read_text(encoding="utf-8"))
            if previous.get("request_url") == url and previous.get("status") == "complete" and previous.get("normalizer_version") == NORMALIZER_VERSION:
                verify(root, previous)
                return previous
    attempted = utc_now()
    pages, entries, seen, failures, matches = [], [], set(), [], set()
    while url:
        try:
            if url in seen or len(seen) >= 64:
                raise ValueError("Pagination repeated or exceeded 64 pages")
            seen.add(url)
            body = getter(url)
            if len(body) > PAGE_BYTES or sum(x["bytes"] for x in entries) + len(body) > TOTAL_BYTES:
                raise ValueError("Collection exceeds its byte budget")
            obj = json.loads(body)
            evidence = blob(root, body) | {"request_url": url, "retrieved_at_utc": utc_now()}
            if obj.get("numberMatched") is not None:
                matches.add(int(obj["numberMatched"]))
            page_rows, _, _ = normalize_pages([(obj, evidence)])
            if any(not window_start <= instant(row["report_time_utc"]) < window_end for row in page_rows):
                raise ValueError("Provider returned a report outside the requested time window")
            entries.append(evidence)
            pages.append((obj, evidence))
            url = next_url(obj)
        except Exception as error:
            # Never include credential-bearing provider responses or tracebacks in a public manifest.
            failures.append({"request_url": url, "error_type": type(error).__name__})
            break
    rows, labels, conflicts = normalize_pages(pages)
    count_ok = len(matches) == 1 and next(iter(matches)) == len(rows)
    state = "complete" if not failures and not conflicts and count_ok else "partial" if rows else "unavailable"
    snapshot = digest(encode({"normalizer_version": NORMALIZER_VERSION, "request": initial_url, "raw": [e["sha256"] for e in entries],
                              "state": state, "failures": failures}))
    run = root / "runs" / snapshot
    observation_body, label_body = encode(rows), encode(labels)
    weather = [label for row in rows if (label := present_weather_label(row)) is not None]
    if (run / "manifest.json").exists():
        previous = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        verify(root, previous)
        return previous
    derivatives = []
    for name, body in (("observations.json", observation_body), ("precipitation_labels.json", label_body),
                       ("observations.csv", csv_bytes(rows)), ("precipitation_labels.csv", csv_bytes(labels)),
                       ("present_weather_labels.json", encode(weather)), ("present_weather_labels.csv", csv_bytes(weather))):
        atomic(run / name, body)
        derivatives.append({"path": (run / name).relative_to(root).as_posix(), "sha256": digest(body), "bytes": len(body)})
    manifest = {"schema_version": 1, "normalizer_version": NORMALIZER_VERSION, "id": snapshot, "region": REGION, "status": state,
                "provider": "India Meteorological Department", "request_url": initial_url,
                "requested_start": start, "requested_end": end, "attempted_at_utc": attempted,
                "completed_at_utc": utc_now(), "latest_observed_at_utc": max((r["report_time_utc"] for r in rows), default=None),
                "earliest_observed_at_utc": min((r["report_time_utc"] for r in rows), default=None),
                "files": entries, "derivatives": derivatives, "failures": failures,
                "conflicting_feature_ids": conflicts, "provider_matched_counts": sorted(matches),
                "completeness_note": "All declared records retrieved" if count_ok else "Provider counts vary or do not equal unique returned records; completeness unverified",
                "counts": {"variable_records": len(rows), "station_reports": len({r["report_id"] for r in rows}),
                           "stations": len({r["station_id"] for r in rows}), "precipitation_states": dict(Counter(l["state"] for l in labels)),
                           "present_weather_categories": dict(Counter(l["category"] for l in weather)),
                           "accumulation_minutes": sorted({l["duration_minutes"] for l in labels if l["duration_minutes"]}),
                           "exact_30_minute_labels": sum(l["eligible_as_exact_30_minute_label"] for l in labels)},
                "training_ready_30_minutes": False,
                "limitations": ["Station points do not cover every grid cell.", "Retrospective download does not establish historical delivery latency.",
                                "Positive total water equivalent is precipitation evidence, not independent precipitation-phase classification.",
                                "Missing values and conflicting revisions remain unknown.", "No matched radar, satellite image and lightning corpus is established."],
                "terms_url": f"{BASE}/discovery-metadata/items/{COLLECTION}?f=json"}
    atomic(run / "manifest.json", encode(manifest))
    return manifest


def verify(root, manifest):
    root = Path(root).resolve()
    for entry in manifest["files"] + manifest["derivatives"]:
        path = (root / entry["path"]).resolve()
        if not path.is_relative_to(root) or entry["bytes"] > TOTAL_BYTES:
            raise ValueError("Invalid artifact path or size")
        body = path.read_bytes()
        if len(body) != entry["bytes"] or digest(body) != entry["sha256"]:
            raise ValueError("NCR artifact failed integrity verification")


def latest(root):
    manifests = [json.loads(p.read_text(encoding="utf-8")) for p in Path(root).glob("runs/*/manifest.json")]
    if not manifests:
        return None
    return max(manifests, key=lambda item: item["completed_at_utc"])


def read_rows(root, manifest, kind):
    names = {"observations": "observations.json", "precipitation": "precipitation_labels.json", "present_weather": "present_weather_labels.json"}
    if kind not in names:
        raise ValueError("Unknown record kind")
    entry = next(e for e in manifest["derivatives"] if Path(e["path"]).name == names[kind])
    path = (Path(root) / entry["path"]).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError("Invalid artifact path")
    body = path.read_bytes()
    if digest(body) != entry["sha256"]:
        raise ValueError("Derived observations failed integrity verification")
    return json.loads(body)

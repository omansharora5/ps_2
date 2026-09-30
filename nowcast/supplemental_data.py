"""Bounded NCR evidence collection. No source in this module is block-scale rain truth."""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlencode, urlsplit

from .ncr_data import BBOX, ROOT, encode, instant, utc_now

DEFAULT_ROOT = ROOT / "data/ncr/supplemental"
VERSION = 1
POINT = {"latitude": 28.6139, "longitude": 77.2090}
VARIABLES = {
    "temperature_2m": "°C", "relative_humidity_2m": "%", "dew_point_2m": "°C",
    "pressure_msl": "hPa", "wind_speed_10m": "m/s", "wind_direction_10m": "°",
    "precipitation": "mm", "cape": "J/kg", "convective_inhibition": "J/kg",
    "total_column_integrated_water_vapour": "kg/m²",
}
CATALOG = {
    "open_meteo": {"role": "nwp_forecast_context", "access": "public_no_key_noncommercial",
                   "url": "https://open-meteo.com/en/docs", "credit": "Open-Meteo / NOAA GFS",
                   "note": "Hourly model context; precipitation is not a measured rain label. Keep retrieval time for causal use."},
    "iem": {"role": "airport_observation", "access": "public_no_key",
            "url": "https://mesonet.agron.iastate.edu/request/download.phtml?network=IN__ASOS",
            "credit": "Iowa Environmental Mesonet",
            "note": "Indian precipitation amounts are unavailable. Returned p01i zeroes are not dry labels; retain METAR weather evidence."},
    "meteostat": {"role": "mixed_station_archive", "access": "public_bulk_no_key",
                  "url": "https://dev.meteostat.net/data/timeseries/hourly", "credit": "Meteostat and original data providers",
                  "note": "Station/year CSV may contain model fill; preserve each variable's source. JSON API separately needs RapidAPI."},
    "power": {"role": "coarse_historical_environment", "access": "public_no_key",
              "url": "https://power.larc.nasa.gov/docs/services/api/temporal/hourly/", "credit": "NASA POWER",
              "note": "Delayed, coarse environmental estimates. PRECTOTCORR is not local gauge truth."},
    "rainviewer": {"role": "rendered_radar_display", "access": "public_limited_use",
                   "url": "https://www.rainviewer.com/api/weather-maps-api.html", "credit": "RainViewer and radar data providers",
                   "note": "Past rendered frames only. NCR coverage and individual scan freshness are unverified. Never interpret an empty tile as dry."},
    "imerg": {"role": "satellite_precipitation_catalogue", "access": "public_catalogue_earthdata_download",
              "url": "https://www.earthdata.nasa.gov/data/catalog/ges-disc-gpm-3imerghh-07", "credit": "NASA GPM / GES DISC",
              "note": "Catalogue records only until authenticated files are downloaded. Native 0.1-degree estimates can be weak labels, not block-scale truth."},
}
HOSTS = {"api.open-meteo.com", "mesonet.agron.iastate.edu", "data.meteostat.net",
         "power.larc.nasa.gov", "api.rainviewer.com", "cmr.earthdata.nasa.gov"}


def fetch(url: str, limit: int = 8_000_000) -> bytes:
    import requests

    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.username or parsed.password:
        raise ValueError("Unapproved public provider URL")
    with requests.get(url, timeout=(15, 90), stream=True, allow_redirects=False,
                      headers={"User-Agent": "VAJRA-NCR-research/1.0"}) as response:
        if response.status_code != 200:
            raise ValueError(f"Provider returned HTTP {response.status_code}")
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > limit:
                raise ValueError("Provider response exceeds collection limit")
            chunks.append(chunk)
    return b"".join(chunks)


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def iso(value: str) -> str:
    return instant(value).isoformat().replace("+00:00", "Z")


def query(base: str, params: dict) -> str:
    return base + "?" + urlencode(params, doseq=True)


def interval(start: str, end: str, max_days=31):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if not 0 < (last - first).days <= max_days:
        raise ValueError(f"Use an exclusive end date, 1 to {max_days} days after start")
    if last > datetime.now(timezone.utc).date() + timedelta(days=1):
        raise ValueError("Historical collection cannot extend into the future")
    return first, last


def open_meteo(payload: bytes):
    obj = json.loads(payload)
    if obj.get("utc_offset_seconds") != 0:
        raise ValueError("Expected Open-Meteo UTC times")
    hourly, units = obj["hourly"], obj["hourly_units"]
    times = hourly["time"]
    coords = [number(obj.get(key)) for key in POINT]
    if any(value is None or abs(value - POINT[key]) > 0.5 for value, key in zip(coords, POINT)):
        raise ValueError("Open-Meteo returned a grid point outside the Delhi request neighbourhood")
    decoded_times = [instant(timestamp + "Z") for timestamp in times]
    if not 1 <= len(times) <= 48 or any(t.minute or t.second or t.microsecond for t in decoded_times):
        raise ValueError("Expected at most 48 hourly Open-Meteo slots")
    if any(b - a != timedelta(hours=1) for a, b in zip(decoded_times, decoded_times[1:])):
        raise ValueError("Open-Meteo slots must increase hourly without duplicates")
    for field, expected in VARIABLES.items():
        if units.get(field) != expected or len(hourly[field]) != len(times):
            raise ValueError(f"Unexpected Open-Meteo schema or units: {field}")
    rows = []
    for index, timestamp in enumerate(times):
        valid = iso(timestamp + "Z")
        rows.append({"valid_at_utc": valid, "model": "gfs_global", "model_initialized_at_utc": None,
                     "latitude": obj["latitude"], "longitude": obj["longitude"],
                     "values": {field: number(hourly[field][index]) for field in VARIABLES},
                     "units": VARIABLES, "precipitation_interval_start_utc":
                     (instant(valid) - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
                     "label_eligible": False})
    return rows, {"requested_point": POINT, "returned_point": {key: obj[key] for key in POINT},
                  "model_initialization_known": False, "availability_rule": "first retrieval of this snapshot",
                  "generationtime_ms_is_model_issue_time": False}


def raining_code(codes: str) -> str:
    # Only positive present-weather evidence. No code does not establish dry weather.
    for code in codes.split():
        if re.fullmatch(r"[+-]?(?:TS|SH|FZ)?(?:RA|DZ|RASN|SNRA)", code):
            return "reported_rain_or_drizzle"
    return "unknown"


def iem(payload: bytes):
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    if not {"station", "valid", "metar", "wxcodes", "p01i"} <= set(reader.fieldnames or []):
        raise ValueError("Unexpected IEM CSV schema")
    rows = []
    for raw in reader:
        if raw["station"] not in {"VIDP", "VIDD"}:
            raise ValueError("Unexpected airport outside requested stations")
        values = {key: number(raw.get(key)) for key in ("tmpf", "dwpf", "relh", "sknt", "drct", "mslp")}
        rows.append({"station": raw["station"], "observed_at_utc": iso(raw["valid"].replace(" ", "T") + "Z"),
                     "latitude": number(raw.get("lat")), "longitude": number(raw.get("lon")),
                     "temperature_c": None if values["tmpf"] is None else (values["tmpf"] - 32) * 5 / 9,
                     "dew_point_c": None if values["dwpf"] is None else (values["dwpf"] - 32) * 5 / 9,
                     "relative_humidity_percent": values["relh"], "wind_direction_degrees": values["drct"],
                     "wind_speed_m_s": None if values["sknt"] is None else values["sknt"] * 0.514444444,
                     "pressure_msl_hpa": values["mslp"], "precipitation_mm": None,
                     "provider_p01i_unusable": raw.get("p01i"), "present_weather_codes": raw["wxcodes"],
                     "present_weather_evidence": raining_code(raw["wxcodes"]), "raw_metar": raw["metar"],
                     "label_eligible": False})
    return rows, {"precipitation_amounts_supported_for_india": False,
                  "independent_of_imd_airport_observations": False,
                  "historical_report_availability_known": False}


def meteostat(payload: bytes, start: str, end: str):
    with gzip.GzipFile(fileobj=io.BytesIO(payload)) as archive:
        decoded = archive.read(20_000_001)
    if len(decoded) > 20_000_000:
        raise ValueError("Meteostat expanded file exceeds limit")
    reader = csv.DictReader(io.StringIO(decoded.decode("utf-8-sig")))
    if not {"year", "month", "day", "hour", "temp_source", "prcp_source"} <= set(reader.fieldnames or []):
        raise ValueError("Meteostat per-variable source columns required")
    units = {"temp": "degC", "rhum": "%", "prcp": "mm", "wdir": "degrees", "wspd": "km/h",
             "wpgt": "km/h", "pres": "hPa", "cldc": "%", "coco": "condition_code"}
    rows = []
    for raw in reader:
        observed = datetime(*(int(raw[k]) for k in ("year", "month", "day", "hour")), tzinfo=timezone.utc)
        if not start <= observed.date().isoformat() < end:
            continue
        rows.append({"station": "42181", "observed_or_modelled_at_utc": observed.isoformat().replace("+00:00", "Z"),
                     "values": {key: number(raw.get(key)) for key in units}, "units": units,
                     "variable_sources": {key: raw.get(key + "_source") or "unknown" for key in units},
                     "label_eligible": False})
    return rows, {"station": "42181", "name": "Delhi Palam", "model_fill_must_be_preserved": True,
                  "independent_of_other_airport_archives": False, "historical_report_availability_known": False}


def power(payload: bytes):
    obj = json.loads(payload)
    fields = obj["properties"]["parameter"]
    fill = obj["header"]["fill_value"]
    times = sorted(set().union(*(series.keys() for series in fields.values())))
    rows = []
    if obj["header"].get("time_standard") != "UTC":
        raise ValueError("NASA POWER must use UTC")
    for timestamp in times:
        values = {key: number(series.get(timestamp)) for key, series in fields.items()}
        values = {key: None if value == fill else value for key, value in values.items()}
        rows.append({"valid_at_utc": datetime.strptime(timestamp, "%Y%m%d%H").replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
                     "values": values, "units": {key: obj["parameters"][key]["units"] for key in fields},
                     "label_eligible": False})
    return rows, {"requested_point": POINT, "geometry": obj.get("geometry"), "fill_value": fill,
                  "historical_operational_availability_known": False}


def rainviewer(payload: bytes):
    obj = json.loads(payload)
    if obj["host"] != "https://tilecache.rainviewer.com":
        raise ValueError("Unexpected RainViewer tile host")
    rows = []
    for frame in obj["radar"]["past"]:
        if not re.fullmatch(r"/v2/radar/[A-Za-z0-9_-]+", frame["path"]):
            raise ValueError("Unexpected radar tile path")
        generated = datetime.fromtimestamp(frame["time"], timezone.utc).isoformat().replace("+00:00", "Z")
        rows.append({"frame_generated_at_utc": generated, "individual_radar_observed_at_utc": None,
                     "path": frame["path"], "tile_url_template": obj["host"] + frame["path"] + "/256/{z}/{x}/{y}/2/0_0.png",
                     "max_zoom": 7, "ncr_coverage": "unverified", "label_eligible": False})
    return rows, {"future_frames_supported": False, "returned_future_frame_count": len(obj["radar"].get("nowcast", [])),
                  "numeric_dbz_available": False, "coverage_is_current_scan_evidence": False,
                  "attribution_url": "https://www.rainviewer.com/", "individual_scan_freshness": "unknown"}


def imerg(payload: bytes):
    entries = json.loads(payload)["feed"]["entry"]
    rows = []
    for item in entries:
        rows.append({"granule_id": item["id"], "title": item["title"],
                     "interval_start_utc": iso(item["time_start"]), "interval_end_utc": iso(item["time_end"]),
                     "links": [{"href": link["href"], "rel": link.get("rel"), "type": link.get("type")}
                               for link in item.get("links", []) if link.get("href", "").startswith("https://")],
                     "scientific_payload_downloaded": False, "label_eligible": False})
    return rows, {"scientific_payload_downloaded": False, "native_resolution_degrees": 0.1,
                  "collection": "GPM_3IMERGHHE", "version": "07", "run": "Early",
                  "download_requires": "NASA Earthdata account with GES DISC authorization",
                  "catalogue_is_rainfall_data": False, "bounded_discovery_not_complete_archive": True}


def plan(source: str, start: str, end: str):
    first, last = interval(start, end)
    if source == "open_meteo":
        return query("https://api.open-meteo.com/v1/forecast", {
            **POINT, "hourly": ",".join(VARIABLES), "wind_speed_unit": "ms", "timezone": "UTC",
            "forecast_days": 2, "models": "gfs_global"}), open_meteo
    if source == "iem":
        return query("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py", {
            "station": ["VIDP", "VIDD"], "data": "all", "sts": start + "T00:00:00Z", "ets": end + "T00:00:00Z",
            "tz": "UTC", "format": "onlycomma", "missing": "M", "trace": "T", "latlon": "yes"}), iem
    if source == "meteostat":
        if first.year != (last - timedelta(days=1)).year:
            raise ValueError("Collect Meteostat one calendar year per request")
        return f"https://data.meteostat.net/hourly/{first.year}/42181.csv.gz", lambda body: meteostat(body, start, end)
    if source == "power":
        return query("https://power.larc.nasa.gov/api/temporal/hourly/point", {
            **POINT, "parameters": "T2M,RH2M,PS,WS10M,WD10M,PRECTOTCORR", "community": "AG",
            "start": first.strftime("%Y%m%d"), "end": (last - timedelta(days=1)).strftime("%Y%m%d"),
            "format": "JSON", "time-standard": "UTC"}), power
    if source == "rainviewer":
        return "https://api.rainviewer.com/public/weather-maps.json", rainviewer
    if source == "imerg":
        return query("https://cmr.earthdata.nasa.gov/search/granules.json", {
            "short_name": "GPM_3IMERGHHE", "version": "07", "bounding_box": ",".join(map(str, BBOX)),
            "temporal": start + "T00:00:00Z," + (datetime.combine(last, datetime.min.time(), timezone.utc) - timedelta(milliseconds=1)).isoformat().replace("+00:00", "Z"),
            "page_size": 48, "sort_key": "-start_date"}), imerg
    raise ValueError("Unknown supplemental source")


def sha(body: bytes):
    return hashlib.sha256(body).hexdigest()


def validate_rows(source, rows, start, end, retrieved):
    received = instant(retrieved)
    first, last = instant(start + "T00:00:00Z"), instant(end + "T00:00:00Z")
    keys = {"iem": "observed_at_utc", "meteostat": "observed_or_modelled_at_utc", "power": "valid_at_utc"}
    for row in rows:
        if source in keys:
            timestamp = instant(row[keys[source]])
            if not first <= timestamp < last or timestamp > received:
                raise ValueError("Historical record lies outside the requested or already observed time window")
        elif source == "open_meteo":
            if not received - timedelta(days=1) <= instant(row["valid_at_utc"]) <= received + timedelta(days=2):
                raise ValueError("Open-Meteo forecast is outside the current two-day collection window")
        elif source == "rainviewer":
            if instant(row["frame_generated_at_utc"]) > received:
                raise ValueError("RainViewer returned a future frame as past radar")
        elif source == "imerg":
            begin, finish = instant(row["interval_start_utc"]), instant(row["interval_end_utc"])
            if not first <= begin < finish < last or finish > received:
                raise ValueError("IMERG granule lies outside the observed/requested interval")
        if source == "iem":
            lat, lon = row["latitude"], row["longitude"]
            if lat is None or lon is None or not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
                raise ValueError("IEM returned a station position outside the pilot region")


def manifest_at(root: Path, source: str, identity: str):
    if source not in CATALOG or not re.fullmatch(r"[0-9a-f]{64}", identity):
        raise ValueError("Invalid snapshot identity")
    directory = root / source / identity
    body = (directory / "manifest.json").read_bytes()
    if (directory / "manifest.sha256").read_text().strip() != sha(body):
        raise ValueError("Supplemental manifest failed integrity verification")
    manifest = json.loads(body)
    expected = sha(encode({"source": source, "request": manifest["request"],
                           "raw_sha256": manifest["files"]["raw.bin"]}))
    if (manifest["source"] != source or manifest["id"] != identity or expected != identity
            or manifest["role"] != CATALOG[source]["role"]
            or set(manifest["files"]) != {"raw.bin", "rows.json"}):
        raise ValueError("Supplemental manifest identity, role or file set mismatch")
    if instant(manifest["retrieved_at_utc"]) > datetime.now(timezone.utc) + timedelta(seconds=5):
        raise ValueError("Supplemental receipt cannot be in the future")
    return manifest


def checked(root: Path, manifest: dict, filename: str) -> bytes:
    if manifest_at(root, manifest["source"], manifest["id"]) != manifest:
        raise ValueError("Supplied manifest differs from the saved verified receipt")
    if filename not in {"raw.bin", "rows.json"}:
        raise ValueError("Unexpected snapshot file")
    payload = (root / manifest["source"] / manifest["id"] / filename).read_bytes()
    if sha(payload) != manifest["files"][filename]:
        raise ValueError("Supplemental evidence failed integrity verification")
    return payload


def collect(source: str, root: Path, start: str, end: str, getter=fetch):
    root = Path(root).resolve()
    if source not in CATALOG:
        raise ValueError("Unknown supplemental source")
    url, parse = plan(source, start, end)
    body = getter(url)
    rows, metadata = parse(body)
    retrieved = utc_now()
    validate_rows(source, rows, start, end, retrieved)
    # Identity includes the normalizer version and filtered interval; identical retries reuse the first retrieval.
    request = {"url": url, "start_inclusive": start, "end_exclusive": end, "normalizer_version": VERSION}
    identity = sha(encode({"source": source, "request": request, "raw_sha256": sha(body)}))
    destination = root / source / identity
    if destination.exists():
        manifest = manifest_at(root, source, identity)
        for name in ("raw.bin", "rows.json"):
            checked(root, manifest, name)
        return manifest
    encoded_rows = encode(rows)
    manifest = {"id": identity, "source": source, **CATALOG[source], "request": request,
                "retrieved_at_utc": retrieved, "row_count": len(rows), "metadata": metadata,
                "files": {"raw.bin": sha(body), "rows.json": sha(encoded_rows)},
                "status": "collected" if rows else "empty", "training_ready_30_minutes": False}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".pending-", dir=destination.parent))
    try:
        manifest_body = encode(manifest)
        for name, payload in (("raw.bin", body), ("rows.json", encoded_rows), ("manifest.json", manifest_body),
                              ("manifest.sha256", (sha(manifest_body) + "\n").encode())):
            with (temporary / name).open("wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        try:
            temporary.rename(destination)
        except OSError:
            if not destination.exists():
                raise
            manifest = manifest_at(root, source, identity)
            for name in ("raw.bin", "rows.json"):
                checked(root, manifest, name)
    finally:
        if temporary.exists():
            if temporary.resolve().parent != destination.parent.resolve():
                raise ValueError("Temporary cleanup path escaped the collection directory")
            shutil.rmtree(temporary)
    return manifest


def latest(root: Path, source: str):
    if source not in CATALOG:
        raise ValueError("Unknown supplemental source")
    candidates = [path for path in (root / source).glob("*/manifest.json")
                  if re.fullmatch(r"[0-9a-f]{64}", path.parent.name)]
    snapshots = [manifest_at(root, source, path.parent.name) for path in candidates]
    return max(snapshots, key=lambda item: instant(item["retrieved_at_utc"]), default=None)


def read_rows(root: Path, manifest: dict):
    checked(root, manifest, "raw.bin")
    rows = json.loads(checked(root, manifest, "rows.json"))
    if len(rows) != manifest["row_count"]:
        raise ValueError("Supplemental row count differs from the receipt")
    return rows


def imerg_half_hour_amount(rate_mm_h, *, duration_minutes, quality_usable: bool):
    """Convert a validated native IMERG rate; callers must check HDF units, fill and quality first."""
    rate = number(rate_mm_h)
    if rate is None or rate < 0 or duration_minutes != 30 or quality_usable is not True:
        return None
    return rate * 0.5


def provider_cards(root: Path):
    names = {"open_meteo": "Open-Meteo NCR forecast context", "iem": "IEM Delhi airport reports",
             "meteostat": "Meteostat Delhi station archive", "power": "NASA POWER Delhi environment",
             "rainviewer": "RainViewer past radar maps", "imerg": "NASA IMERG NCR file catalogue"}
    cards = []
    for source, definition in CATALOG.items():
        status, count = "not_collected", 0
        try:
            manifest = latest(root, source)
            if manifest:
                read_rows(root, manifest)
                status, count = "saved_research_sample", 2
        except (OSError, ValueError, KeyError, TypeError):
            status = "invalid_local_evidence"
        cards.append({"id": "ncr_" + source, "name": names[source], "provider": definition["credit"],
                      "access": definition["access"].replace("_", " "), "status": status,
                      "format": "Saved provider payload and normalized JSON", "source_url": definition["url"],
                      "api_url": "/api/ncr/supplemental/" + source, "local_file_count": count,
                      "notes": definition["note"] + " Collection runs separately; this is not an automatically refreshed feed."})
    return cards

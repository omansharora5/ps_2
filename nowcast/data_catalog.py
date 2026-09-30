"""Manifest-backed files and opt-in, fixed-snapshot local collection jobs."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Lock
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/government"
COLLECTIONS = {"india": ("Indian observations and NASA context", "collect_india_data.py"),
               "noaa": ("NOAA satellite, lightning and radar samples", "collect_noaa_data.py"),
               "gfs": ("NOAA GFS environmental forecast subset", "collect_gfs_data.py")}
JOBS = {}
LOCK = Lock()
EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fixed-data-collection")


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def enabled():
    return os.environ.get("VAJRA_ENABLE_COLLECTIONS") == "1"


def manifest_entries(collection_id):
    if collection_id not in COLLECTIONS:
        raise KeyError("Unknown collection")
    path = BASE / collection_id / "manifest.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8-sig")).get("files", [])


def safe_path(entry):
    path = (ROOT / entry["path"]).resolve()
    if not path.is_relative_to(BASE.resolve()) or not path.is_file():
        raise FileNotFoundError("Manifest-listed data file is unavailable")
    return path


def file_record(collection_id, entry):
    file_id = collection_id + "--" + entry["id"]
    try:
        path = safe_path(entry)
        local = "present_size_matches" if path.stat().st_size == entry["bytes"] else "size_mismatch"
    except FileNotFoundError:
        local = "missing"
    times = entry.get("observed_time_range")
    if times is None and entry.get("observation_time_start_utc"):
        times = {"observation_start": entry["observation_time_start_utc"], "observation_end": entry.get("observation_time_end_utc"),
                 "historical_available_at": entry.get("historical_available_at_utc")}
    if times is None and entry.get("valid_time_utc"):
        times = {"model_reference_time": entry.get("model_reference_time_utc"), "valid_time": entry["valid_time_utc"],
                 "forecast_lead_hours": entry.get("forecast_lead_hours"), "historical_available_at": entry.get("historical_available_at_utc")}
    units = entry.get("units") or {field["variable"] + " / " + field.get("level", ""): field["units"] for field in entry.get("fields", []) if "units" in field}
    return {"id": file_id, "name": Path(entry["path"]).name,
            "provider": entry.get("provider", collection_id.upper()), "source_url": entry.get("source_url"),
            "download_url": "/api/data/files/" + file_id, "bytes": entry["bytes"], "local_status": local,
            "format": entry.get("format", entry.get("media_type", "unknown")), "units": units,
            "observed_time_range": times, "timezone": entry.get("timezone") or ("UTC" if times and collection_id in ("gfs", "noaa") else None),
            "retrieved_at_utc": entry.get("retrieved_at_utc"), "geography": entry.get("geography"), "data_role": entry.get("data_role"),
            "not_training_ready_reason": entry.get("not_training_ready_reason"), "sha256": entry["sha256"],
            "inspection": entry.get("inspection", {}), "licence_terms_url": entry.get("licence_terms_url")}


def catalog():
    collections = []
    for key, (name, _) in COLLECTIONS.items():
        files = [file_record(key, entry) for entry in manifest_entries(key)]
        present = sum(f["local_status"] == "present_size_matches" for f in files)
        collections.append({"id": key, "name": name, "status": "available" if files and present == len(files) else "partial" if present else "missing",
                            "file_count": len(files), "local_file_count": present, "bytes": sum(f["bytes"] for f in files),
                            "collect_url": f"/api/data/collections/{key}", "files": files})
    by_id = {c["id"]: c for c in collections}
    sources = [
        {"id": "imd_synop", "name": "IMD WIS2 surface observations", "provider": "India Meteorological Department",
         "access": "Public WIS2 core dataset", "status": by_id["india"]["status"], "format": "GeoJSON",
         "source_url": "https://wis2box.imd.gov.in/", "api_url": "https://wis2box.imd.gov.in/oapi/collections",
         "local_file_count": sum(f["name"].startswith("imd_") and f["local_status"] == "present_size_matches" for f in by_id["india"]["files"]),
         "notes": "Sparse station data with declared units and intervals; not a radar grid or lightning labels."},
        {"id": "nasa_power", "name": "NASA POWER Patna environmental context", "provider": "NASA Langley POWER / MERRA-2",
         "access": "Public documented API", "status": by_id["india"]["status"], "format": "JSON",
         "source_url": "https://power.larc.nasa.gov/", "api_url": "https://power.larc.nasa.gov/api/temporal/hourly/point",
         "local_file_count": sum(f["name"].startswith("nasa_") and f["local_status"] == "present_size_matches" for f in by_id["india"]["files"]),
         "notes": "Historical grid-box context, one location and seven days; not rapid operational observations."},
        {"id": "noaa_reference", "name": "NOAA GOES / GLM / NEXRAD reference data", "provider": "NOAA / NCEI",
         "access": "Public archive samples", "status": by_id["noaa"]["status"], "format": "NetCDF and NEXRAD binary",
         "source_url": "https://www.ncei.noaa.gov/", "api_url": "https://noaa-goes16.s3.amazonaws.com/",
         "local_file_count": by_id["noaa"]["local_file_count"], "notes": "US/Americas data for parser experiments; not observations over India."},
        {"id": "gfs", "name": "GFS environmental forecast fields", "provider": "NOAA",
         "access": "Public bounded byte-range archive download", "status": by_id["gfs"]["status"], "format": "GRIB2",
         "source_url": "https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast",
         "api_url": "https://noaa-gfs-bdp-pds.s3.amazonaws.com/", "local_file_count": by_id["gfs"]["local_file_count"],
         "notes": "One historical forecast cycle/subset; historical service readiness remains unknown."},
        {"id": "imd_radar", "name": "Indian numeric radar sequences", "provider": "India Meteorological Department",
         "access": "Exact products and archive/live terms require confirmation", "status": "access_pending", "format": "Provider-specific numeric radar",
         "source_url": "https://mausam.imd.gov.in/", "api_url": "https://api.imd.gov.in/public/index.php", "local_file_count": 0,
         "notes": "Public radar pictures are not a machine-readable multi-event training archive."},
        {"id": "insat", "name": "INSAT thermal channels and quality", "provider": "ISRO SAC / MOSDAC",
         "access": "Approved account and product-specific terms", "status": "access_pending", "format": "Product-dependent HDF/NetCDF",
         "source_url": "https://www.mosdac.gov.in/", "api_url": "https://www.mosdac.gov.in/downloadapi-manual", "local_file_count": 0,
         "notes": "No credentials configured; near-real-time privileges and reuse rights must be checked per product."},
        {"id": "india_lightning", "name": "Indian lightning events and coverage labels", "provider": "IITM / authorized observation partner",
         "access": "Event-level archive and quality/coverage agreement needed", "status": "access_pending", "format": "Unconfirmed event schema",
         "source_url": "https://www.tropmet.res.in/28-Thunderstorm%20Dynamics-project", "api_url": None, "local_file_count": 0,
         "notes": "Damini information does not establish access to training labels. No lightning labels collected for India."},
    ]
    return {"schema_version": 1, "training_ready": False, "scope": "Historical, unmatched starter samples; not an Indian storm training corpus",
            "collection_enabled": enabled(), "collection_policy": "Opt-in, direct loopback, JSON requests and trusted origin only; one fixed job at a time",
            "integrity_note": "Catalog checks local size; file downloads verify SHA-256 before serving", "collections": collections, "sources": sources}


def resolve_file(file_id):
    for collection_id in COLLECTIONS:
        for entry in manifest_entries(collection_id):
            if collection_id + "--" + entry["id"] == file_id:
                path = safe_path(entry)
                if path.stat().st_size != entry["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                    raise ValueError("File failed manifest integrity check")
                return path
    raise KeyError("Unknown manifest file ID")


def run_collection(identifier):
    with LOCK:
        job = JOBS[identifier]
        job.update(status="running", started_at=now())
        script = COLLECTIONS[job["collection_id"]][1]
    python = ROOT / ".venv-data" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    executable = str(python) if python.exists() else sys.executable
    try:
        result = subprocess.run([executable, str(ROOT / "scripts" / script)], cwd=ROOT, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=240, shell=False)
        with LOCK:
            job.update(status="succeeded" if result.returncode == 0 else "failed", finished_at=now(),
                       log=(result.stdout + "\n" + result.stderr)[-6000:],
                       error=None if result.returncode == 0 else f"Collector exited with code {result.returncode}")
    except (OSError, subprocess.TimeoutExpired) as exc:
        with LOCK:
            job.update(status="failed", finished_at=now(), error=str(exc), log="Collection failed; inspect the fixed collector locally.")


def start_collection(collection_id):
    if collection_id not in COLLECTIONS:
        raise KeyError("Unknown fixed collection")
    with LOCK:
        for job in JOBS.values():
            if job["status"] in ("queued", "running"):
                if job["collection_id"] == collection_id:
                    return dict(job)
                raise RuntimeError("Another collection is running; retry after it completes")
        while len(JOBS) >= 20:
            del JOBS[next(iter(JOBS))]
        identifier = uuid4().hex
        job = {"id": identifier, "collection_id": collection_id, "status": "queued", "created_at": now(),
               "started_at": None, "finished_at": None, "log": "", "error": None}
        JOBS[identifier] = job
        EXECUTOR.submit(run_collection, identifier)
        return dict(job)


def jobs():
    with LOCK:
        return [dict(job) for job in reversed(list(JOBS.values()))]


def get_job(identifier):
    with LOCK:
        if identifier not in JOBS:
            raise KeyError("Unknown job; job status is local to this server process")
        return dict(JOBS[identifier])

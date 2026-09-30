"""Read-only NCR evidence API. Collection and inference run outside HTTP requests."""
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from .ncr_data import DEFAULT_ROOT, REGION, instant, latest, read_rows
from . import supplemental_data

router = APIRouter(prefix="/api/ncr", tags=["NCR observations"])
SOURCES = [
    {"id": "imd_surface", "access": "public_no_key", "connected": True,
     "url": "https://wis2box.imd.gov.in/oapi/collections?f=json",
     "parameters": ["station temperature", "dew point", "wind", "pressure", "interval precipitation"],
     "note": "Bounded CLI collector; live freshness is reported separately, not a continuously running feed."},
    {"id": "imd_satellite_winds", "access": "public_no_key", "connected": True,
     "url": "https://wis2box.imd.gov.in/oapi/collections/messages/items?f=json&limit=10&metadata_id=urn:wmo:md:in-imd:satellite&sortby=-pubtime",
     "parameters": ["satellite-derived wind BUFR, full spatial decoding pending"],
     "note": "Separate tested collector; this is not imagery. NCR coverage remains unverified."},
    {"id": "insat_imagery", "access": "approved_mosdac_account", "connected": False,
     "url": "https://www.mosdac.gov.in/downloadapi-manual",
     "parameters": ["calibrated infrared and water-vapour channels", "cloud motion"],
     "note": "No authenticated scientific image collector is connected. WIS2 satellite-derived winds are not imagery."},
    {"id": "imd_radar", "access": "provider_approval_required", "connected": False,
     "url": "https://radarapi.imd.gov.in/dsp/frontend/login",
     "parameters": ["reflectivity dBZ", "radial velocity", "coverage and quality"],
     "note": "Request Delhi/Palam numeric scans and historical sequences. Display images are not numeric volumes."},
    {"id": "iitm_lightning", "access": "provider_event_data_access_unverified", "connected": False,
     "url": "https://incois.gov.in/essdp/ViewMetadata?fileid=05f2bab9-054f-45cf-b77d-1eaf089252ff",
     "parameters": ["event time", "position", "event type", "sensor coverage"],
     "note": "No raw NCR event feed or outage history has been obtained."},
    {"id": "ncmrwf_context", "access": "registered_data_service", "connected": False,
     "url": "https://rds.ncmrwf.gov.in/", "parameters": ["moisture", "CAPE/CIN", "wind profiles"],
     "note": "IMDAA is historical reanalysis; a live forecast requires a separately verified issue-time feed."},
]
BLOCKERS = ["No aligned recent NCR radar and calibrated satellite image sequence is registered.",
            "No NCR model checkpoint has passed independent validation.",
            "Station accumulation intervals cannot be split into invented 30-minute labels.",
            "Lightning predictions additionally require observed lightning labels and network coverage."]


def data_root():
    return Path(os.environ.get("VAJRA_NCR_ROOT", DEFAULT_ROOT)).resolve()


def saved():
    try:
        return latest(data_root())
    except (OSError, ValueError, KeyError):
        raise HTTPException(503, "NCR collection metadata is unavailable or invalid") from None


@router.get("/status")
def status():
    manifest = saved()
    result = {"region": REGION, "sources": SOURCES, "collection": None,
              "model": {"horizon_minutes": 30, "status": "not_ready", "blockers": BLOCKERS},
              "mode": "observed_surface_research", "automatic_collection_running": False}
    if manifest:
        result["collection"] = {key: manifest[key] for key in (
            "id", "status", "attempted_at_utc", "completed_at_utc", "latest_observed_at_utc",
            "earliest_observed_at_utc", "counts", "training_ready_30_minutes", "limitations")}
        observed = manifest["latest_observed_at_utc"]
        age = (datetime.now(timezone.utc) - instant(observed)).total_seconds() / 60 if observed else None
        result["collection"]["latest_observation_age_minutes"] = round(age, 1) if age is not None else None
        result["collection"]["fresh_for_30_minute_nowcast"] = age is not None and 0 <= age <= 15
    return result


@router.get("/observations")
def observations(kind: Literal["observations", "precipitation", "present_weather"] = "precipitation",
                 state: Literal["wet", "reported_zero", "unknown"] | None = None,
                 offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500)):
    manifest = saved()
    if not manifest:
        return {"collection_id": None, "total": 0, "items": []}
    if state is not None and kind != "precipitation":
        raise HTTPException(422, "State filtering applies to precipitation records")
    try:
        rows = read_rows(data_root(), manifest, kind)
    except (OSError, ValueError, KeyError, StopIteration):
        raise HTTPException(503, "NCR observations failed the local integrity check") from None
    if state:
        rows = [row for row in rows if row["state"] == state]
    return {"collection_id": manifest["id"], "total": len(rows), "offset": offset, "limit": limit,
            "next_offset": offset + limit if offset + limit < len(rows) else None,
            "items": rows[offset:offset + limit]}


@router.get("/forecast")
def forecast():
    return {"status": "unavailable", "horizon_minutes": 30, "prediction": None,
            "reason": "A current NCR model forecast cannot be issued from the collected station sample alone.",
            "blockers": BLOCKERS, "model_endpoint_connected": False,
            "next_step": "Use predict_images.py for a validated compatible checkpoint and causal image episode; it does not auto-publish public warnings."}


def supplemental_root():
    return Path(os.environ.get("VAJRA_SUPPLEMENTAL_ROOT", supplemental_data.DEFAULT_ROOT)).resolve()


@router.get("/supplemental")
def supplemental_status():
    sources = []
    for source, definition in supplemental_data.CATALOG.items():
        item = {"id": source, **definition, "collection": None}
        try:
            manifest = supplemental_data.latest(supplemental_root(), source)
            if manifest:
                supplemental_data.read_rows(supplemental_root(), manifest)
                age = (datetime.now(timezone.utc) - instant(manifest["retrieved_at_utc"])).total_seconds() / 60
                item["collection"] = {key: manifest[key] for key in
                                      ("id", "status", "row_count", "retrieved_at_utc", "metadata")}
                item["collection"]["retrieval_age_minutes"] = round(age, 1)
                item["collection"]["retrieval_age_is_observation_age"] = False
        except (OSError, ValueError, KeyError, TypeError):
            item["collection"] = {"status": "invalid", "reason": "Local integrity check failed"}
        sources.append(item)
    return {"region": REGION, "sources": sources, "automatic_collection_running": False,
            "training_ready_30_minutes": False, "model_context_fusion_connected": False}


@router.get("/supplemental/{source}")
def supplemental_rows(source: str, offset: int = Query(default=0, ge=0),
                      limit: int = Query(default=100, ge=1, le=500)):
    if source not in supplemental_data.CATALOG:
        raise HTTPException(404, "Unknown supplemental source")
    try:
        manifest = supplemental_data.latest(supplemental_root(), source)
        rows = supplemental_data.read_rows(supplemental_root(), manifest) if manifest else []
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "Supplemental evidence failed the local integrity check") from None
    return {"source": source, "role": supplemental_data.CATALOG[source]["role"],
            "collection_id": manifest["id"] if manifest else None,
            "first_retrieved_at_utc": manifest["retrieved_at_utc"] if manifest else None,
            "total": len(rows), "offset": offset, "limit": limit,
            "next_offset": offset + limit if offset + limit < len(rows) else None,
            "items": rows[offset:offset + limit]}


@router.get("/gfs")
def gfs_rows(offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500)):
    from scripts import collect_ncr_gfs as gfs
    root = Path(os.environ.get("VAJRA_NCR_GFS_ROOT", gfs.ROOT / "data/ncr/gfs"))
    try:
        manifest = gfs.read_latest(root)
        rows = []
        if manifest:
            spec = manifest["forecast"]
            payload = (root / spec["snapshot_id"] / "ncr.csv").read_bytes()
            for values in gfs.validate_csv(payload, spec):
                rows.append({"model_initialized_at_utc": spec["model_reference_time_utc"],
                             "valid_at_utc": spec["valid_time_utc"], "variable": values[2], "level": values[3],
                             "longitude": float(values[4]), "latitude": float(values[5]), "value": float(values[6]),
                             "units": gfs.UNITS[values[2]], "label_eligible": False})
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "GFS evidence failed the local integrity check") from None
    return {"source": "noaa_gfs", "role": "nwp_context", "collection": manifest,
            "automatic_collection_running": False, "total": len(rows), "offset": offset, "limit": limit,
            "next_offset": offset + limit if offset + limit < len(rows) else None,
            "items": rows[offset:offset + limit]}

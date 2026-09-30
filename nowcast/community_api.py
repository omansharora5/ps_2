"""Citizen evidence and transparent research results, with no operational alert dispatch."""
from collections import deque
from datetime import datetime
import hashlib
import os
from pathlib import Path
from threading import Lock
import time
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from .community_store import CELLS, CELL_IDS, Capacity, CommunityStore, Conflict, now, timestamp, utc, window
from .ncr_data import ROOT, DEFAULT_ROOT, latest as latest_surface, verify as verify_surface
from .operations_api import trusted_origins
from . import public_verification

router = APIRouter(prefix="/api/community", tags=["Citizen evidence and public verification"])
_rate_lock = Lock()
_rate_buckets = {}


def root():
    return Path(os.environ.get("VAJRA_COMMUNITY_ROOT", ROOT / "data/community")).resolve()


def store():
    return CommunityStore(root() / "reports.sqlite")


def enabled():
    return os.environ.get("VAJRA_ENABLE_FEEDBACK") == "1"


def public_aggregate(aggregate):
    closed = aggregate["window_closed"]
    status = "reviewed" if closed and aggregate["review_status"] in {"approve", "reject"} else (
        "candidate_review" if closed and aggregate["consensus"] in {"rain_support", "dry_support"} else "collecting")
    return {"cell_id": aggregate["cell_id"], "window_start_utc": aggregate["window_start_utc"],
            "window_end_utc": aggregate["window_end_utc"], "public_status": status, "counts_withheld": True,
            "independent_people_verified": False, "automatic_training": False}


def guard(request, *, local=False, writing=True):
    if not enabled():
        raise HTTPException(403, "Citizen research reporting requires VAJRA_ENABLE_FEEDBACK=1 on the server.")
    if local and (not request.client or request.client.host not in {"127.0.0.1", "::1"}
                  or request.url.hostname not in {"127.0.0.1", "localhost", "::1"}):
        raise HTTPException(403, "Review and export require the local research operator connection.")
    origin = request.headers.get("origin")
    same_origin = str(request.base_url).rstrip("/")
    if origin and origin not in {*trusted_origins(), same_origin}:
        raise HTTPException(403, "This browser origin is not allowed to submit research reports.")
    if writing and request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "Use an application/json request.")
    if writing:
        key = hashlib.sha256((request.client.host if request.client else "unknown").encode()).hexdigest()
        clock = time.monotonic()
        with _rate_lock:
            expired = [k for k, values in _rate_buckets.items() if not values or values[-1] <= clock - 60]
            for old in expired:
                del _rate_buckets[old]
            if key not in _rate_buckets and len(_rate_buckets) >= 256:
                raise HTTPException(429, "Research reporting is busy; retry in a minute.")
            bucket = _rate_buckets.setdefault(key, deque())
            while bucket and bucket[0] <= clock - 60:
                bucket.popleft()
            if len(bucket) >= 60:
                raise HTTPException(429, "Too many research submissions; retry in a minute.")
            bucket.append(clock)


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=36, max_length=36)
    installation_id: str = Field(min_length=36, max_length=36)
    cell_id: str = Field(max_length=40)
    answer: Literal["yes", "no", "unsure"]
    observed_at_utc: str = Field(max_length=40)
    consent_training: StrictBool


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cell_id: str = Field(max_length=40)
    window_start_utc: str = Field(max_length=40)
    expected_revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["approve", "reject"]
    reason: str = Field(min_length=10, max_length=1000)
    evidence_url: str = Field(default="", max_length=1000)


def evidence_card():
    sensors = [
        {"id": "radar", "name": "Indian numeric radar", "observed_at_utc": None, "age_minutes": None,
         "status": "missing", "note": "No calibrated NCR scan sequence is registered; map tiles do not replace it."},
        {"id": "satellite", "name": "INSAT image sequence", "observed_at_utc": None, "age_minutes": None,
         "status": "missing", "note": "Scientific imagery still requires acquisition and alignment."},
        {"id": "lightning", "name": "Lightning detections and coverage", "observed_at_utc": None, "age_minutes": None,
         "status": "missing", "note": "A catalogue or zero detections cannot establish a covered no-lightning interval."},
    ]
    try:
        surface_root = Path(os.environ.get("VAJRA_NCR_ROOT", DEFAULT_ROOT))
        manifest = latest_surface(surface_root)
        if manifest:
            verify_surface(surface_root, manifest)
        observed = manifest.get("latest_observed_at_utc") if manifest else None
        age = (now() - timestamp(observed)).total_seconds() / 60 if observed else None
        sensors.append({"id": "surface", "name": "IMD regional station sample", "observed_at_utc": observed,
                        "age_minutes": round(age, 1) if age is not None and age >= 0 else None,
                        "status": "historical" if observed else "missing",
                        "note": "Regional station time does not establish coverage of the selected pilot cell."})
    except (ValueError, KeyError, OSError, TypeError):
        sensors.append({"id": "surface", "name": "IMD regional stations", "observed_at_utc": None,
                        "age_minutes": None, "status": "missing", "note": "Saved station evidence could not be verified."})
    return {"status": "unavailable", "rain_probability": None, "lightning_probability": None,
            "onset_interval": None, "heavy_rain_end": None, "confidence": "unvalidated", "sensors": sensors,
            "tracks": [], "radar_loop": None, "monsoon_phase": "unknown",
            "reasons": ["No validated NCR forecast is registered.", "Lightning needs covered strike labels and observed quiet history for first-strike forecasts.",
                        "Warm cloud tops do not rule out monsoon rain; dust requires separate corroborating observations."],
            "explanation_method": "Source/time/coverage rules; no LLM or causal explanation model required",
            "official_warning_url": "https://sachet.ndma.gov.in/"}


def month_value(value):
    if value is None:
        return now().strftime("%Y-%m")
    try:
        parsed = datetime.strptime(value, "%Y-%m")
        if parsed.strftime("%Y-%m") != value:
            raise ValueError
        return value
    except ValueError:
        raise HTTPException(422, "Use a month formatted YYYY-MM.") from None


@router.get("/scorecard")
def scorecard(month: str | None = Query(default=None, max_length=7)):
    try:
        return public_verification.read_scorecard(root() / "publications", month_value(month))
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "Published scorecard failed integrity verification.") from None


@router.get("/benchmark")
def benchmark():
    try:
        return public_verification.read_benchmark(root() / "publications/benchmark.json")
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "Benchmark manifest failed integrity verification.") from None


@router.get("/state")
def state(cell_id: str = Query(default="delhi-central", max_length=40), month: str | None = Query(default=None, max_length=7)):
    if cell_id not in CELL_IDS:
        raise HTTPException(422, "Select a listed NCR pilot cell.")
    start, end = window(now())
    return {"enabled": enabled(), "cells": CELLS, "geometry_version": "ncr-pilot-cells-v1",
            "geography_note": "Pilot research cells; not official block boundaries or validated prediction resolution.",
            "selected_cell": cell_id, "prompt": {"question": "Is it raining where you are now?", "forecast_status": "unavailable",
                                                     "window_start_utc": start, "window_end_utc": end,
                                                     "sampling": "Neutral voluntary reporting; no model answer shown before the report."},
            "aggregate": public_aggregate(store().aggregate(cell_id, start)), "evidence_card": evidence_card(),
            "scorecard": scorecard(month), "benchmark": benchmark(),
            "automatic_training": False, "identity_assurance": "Unverified installation, not verified person",
            "privacy": "Only the selected coarse cell, answer, times, consent and hashed installation identity are stored."}


@router.post("/reports")
def submit_report(body: ReportRequest, request: Request):
    guard(request)
    try:
        result = store().submit(body.model_dump())
        result["aggregate"] = public_aggregate(result["aggregate"])
        return result
    except Conflict as error:
        raise HTTPException(409, str(error)) from None
    except Capacity as error:
        raise HTTPException(429, str(error)) from None
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422, "Invalid report. Check the pilot cell, UUIDs, explicit UTC time and last-15-minute observation window.") from None


@router.post("/review")
def review_report(body: ReviewRequest, request: Request):
    guard(request, local=True)
    try:
        return store().review(body.cell_id, body.window_start_utc, body.expected_revision, body.decision,
                              body.reason, body.evidence_url)
    except Conflict as error:
        raise HTTPException(409, str(error)) from None
    except ValueError as error:
        raise HTTPException(422, str(error)) from None


@router.get("/review-queue")
def review_queue(request: Request):
    guard(request, local=True, writing=False)
    return {"windows": store().recent_windows(), "automatic_training": False}


@router.get("/export")
def export_reports(request: Request):
    guard(request, local=True, writing=False)
    try:
        return store().reviewed_export()
    except Capacity as error:
        raise HTTPException(413, str(error)) from None

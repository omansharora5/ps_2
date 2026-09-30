import hashlib
import json
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .forecast import load_model, model_digest, predict, targets
from .numerics import components
from .observations import CELL_KM, SOURCES, snapshot, synthetic_event
from .real_data import replay
from .verification import verify
from . import data_catalog
from .image_processing import METHODS, PREPROCESSING, image_run
from .decision_policy import POLICY_VERSION, ResearchPolicy, assess_research_decision


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "receipts.sqlite"
CODE_SHA = hashlib.sha256(b"".join(path.read_bytes() for path in sorted((ROOT / "nowcast").glob("*.py")))).hexdigest()
app = FastAPI(title="VAJRA research workbench", version="0.1.0")
CORS_ORIGINS = [origin.strip() for origin in os.environ.get("VAJRA_CORS_ORIGINS", "").split(",") if origin.strip()]
if not CORS_ORIGINS:
    CORS_ORIGINS = [f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in (8000, 8081, 8082, 5173, 4173)]
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type"], allow_credentials=False)
Source = Literal["radar", "satellite", "lightning", "nwp"]


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["simulation", "observed"] = "simulation"
    seed: int = Field(default=62, ge=60, le=65)
    step: int = Field(default=8, ge=2, le=16)
    horizon: int = 30
    hazard: Literal["lightning", "storm"] = "lightning"
    disabled: list[Source] = Field(default_factory=list, max_length=4)
    stale: list[Source] = Field(default_factory=list, max_length=4)


class ReceiptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str = Field(pattern=r"^[a-f0-9]{20}$")
    preparation_minutes: int = Field(default=20, ge=0, le=120)
    threshold: float = Field(default=0.5, ge=0.05, le=0.95)
    site_id: Literal["patna", "gaya", "nalanda"] = "patna"
    min_recent_spatial_sources: int = Field(default=2, ge=1, le=3)
    max_source_age_minutes: int = Field(default=10, ge=0, le=120)


class ImageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["persistence", "global_translation", "dense_optical_flow"] = "global_translation"
    preprocessing: Literal["raw", "despeckle", "smooth"] = "smooth"
    horizon: Literal[5, 10, 15, 20] = 10


class CollectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


def encode_grid(grid):
    return [[round(float(value), 4) if np.isfinite(value) else None for value in row] for row in grid]


def connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
    return db


def persist(table, record):
    if table not in ("runs", "receipts"):
        raise ValueError("Unknown record type")
    with closing(connection()) as db, db:
        db.execute(f"INSERT OR IGNORE INTO {table} (id,payload) VALUES (?,?)", (record["id"], json.dumps(record, allow_nan=False)))
        return json.loads(db.execute(f"SELECT payload FROM {table} WHERE id=?", (record["id"],)).fetchone()[0])


def lookup(table, identifier):
    if table not in ("runs", "receipts"):
        raise ValueError("Unknown record type")
    with closing(connection()) as db:
        row = db.execute(f"SELECT payload FROM {table} WHERE id=?", (identifier,)).fetchone()
    if not row:
        raise HTTPException(404, "Saved record not found")
    return json.loads(row[0])


def compare(models, truth):
    available = [p for p in models.values() if np.isfinite(p).any()]
    common = np.isfinite(truth)
    for p in available:
        common &= np.isfinite(p)
    return {name: verify(p, truth, mask=common) for name, p in models.items()}


def simulated_run(request):
    event = synthetic_event(request.seed)
    obs = snapshot(event, request.step, request.disabled, request.stale)
    artifact = load_model()
    forecast = predict(obs, request.horizon, artifact)
    truth = targets(event, request.step, request.horizon)[request.hazard]
    models = {name: forecast[name][request.hazard] for name in ("fusion", "advection", "persistence")}
    dy, dx = forecast["velocity"]
    tracks = []
    if obs.available["radar"]:
        for index, cell in enumerate(components(obs.fields["radar"][-1], 35)):
            tracks.append({**cell, "id": f"C{index+1:02d}", "end_x": cell["x"] + dx * request.horizon / 5,
                           "end_y": cell["y"] + dy * request.horizon / 5,
                           "speed_kmh": round(np.hypot(dx, dy) * CELL_KM * 12, 1)})
    degraded = any(not value for value in obs.available.values())
    sites = []
    for site_id, name, lat, lon in [("patna", "Patna demo site", 25.594, 85.138),
                                   ("gaya", "Gaya demo site", 24.796, 85.000),
                                   ("nalanda", "Nalanda demo site", 25.136, 85.444)]:
        x = round((lon - 84.45) * 111.0 * np.cos(np.deg2rad(25.5)) / CELL_KM)
        y = round((lat - 24.6) * 111.0 / CELL_KM)
        p = models["fusion"][y, x]
        sites.append({"id": site_id, "name": name, "lat": lat, "lon": lon, "x": x, "y": y,
                      "probability": float(p) if np.isfinite(p) else None})
    return {"mode": "simulation", "label": "Bihar study area · synthetic event", "scope": artifact["scope"],
            "issued_at": obs.issued_at, "valid_at": event.timestamps[request.step + request.horizon // 5],
            "time_note": "Synthetic UTC timestamps; no observed Indian weather",
            "grid": {"width": 48, "height": 48, "cell_km": 4, "west": 84.45,
                     "east": 84.45 + 47 * 4 / (111 * np.cos(np.deg2rad(25.5))), "south": 24.6,
                     "north": 24.6 + 47 * 4 / 111, "row_direction": "north", "crs": "Local equirectangular approximation"},
            "status": "unavailable" if forecast["abstained"] else "degraded" if degraded else "simulation",
            "status_reason": "No recent spatial observations; forecast withheld" if forecast["abstained"] else
                "Source removal experiment. Outage probabilities have no separate calibration." if degraded else
                "Fitted and calibrated on synthetic events only",
            "sources": obs.status, "layers": {**{name: encode_grid(p) for name, p in models.items()},
                                               "truth": encode_grid(truth)},
            "metrics": compare(models, truth), "tracks": tracks, "sites": sites,
            "target": artifact["target_definitions"][request.hazard],
            "calibration": artifact["calibration"], "model_version": artifact["version"],
            "model_sha256": model_digest(artifact), "data_provenance": {"generator": "synthetic-event-v1", "seed": request.seed},
            "evidence": [{"name": "Multi-radar composite", "value": f"{np.nanmax(obs.fields['radar'][-1]):.1f} dBZ peak" if obs.available["radar"] else "Unavailable"},
                         {"name": "Cloud-top temperature", "value": f"{np.nanmin(obs.fields['satellite'][-1]):.1f} K minimum" if obs.available["satellite"] else "Unavailable"},
                         {"name": "Recent lightning", "value": f"{int(obs.fields['lightning'].sum())} simulated flashes / 15 min" if obs.available["lightning"] else "Unavailable"},
                         {"name": "Environmental context", "value": f"{np.nanmean(obs.fields['nwp'][-1]):.0f} J/kg mean CAPE" if obs.available["nwp"] else "Unavailable"}]}


def observed_run(request):
    if request.hazard != "storm" or request.disabled or request.stale:
        raise ValueError("Observed sample supports radar-echo replay only; use simulation for source removal")
    data = replay(request.horizon)
    models = {name: data[name] for name in ("advection", "persistence")}
    lat, lon = data["lat"], data["lon"]
    return {"mode": "observed", "label": "Southeast France · observed radar", "scope": "Six historical radar frames; not Indian lightning validation",
            "issued_at": data["issued_at"], "valid_at": data["valid_at"],
            "time_note": "Times exactly as archived; timezone not independently verified",
            "grid": {"width": lon.shape[1], "height": lat.shape[0], "cell_km": None,
                     "west": float(lon.min()), "east": float(lon.max()), "south": float(lat.min()), "north": float(lat.max()),
                     "row_direction": "south" if lat[0, 0] > lat[-1, 0] else "north", "crs": "EPSG:4326, every third source pixel"},
            "status": "observed", "status_reason": "Real radar input and held-out future echoes; no lightning observations",
            "sources": [{"source": source, "state": "available" if source == "radar" else "missing", "age_minutes": 0 if source == "radar" else None,
                         "provenance": "Météo-France historical composite" if source == "radar" else "Not in sample"} for source in SOURCES],
            "layers": {**{name: encode_grid(p) for name, p in models.items()}, "truth": encode_grid(data["truth"])},
            "metrics": compare(models, data["truth"]), "tracks": [], "sites": [],
            "target": "Radar echo >=20 dBZ at valid time. Not a thunderstorm or lightning label.",
            "calibration": "Deterministic echo forecasts; 0/1 are predictions, not calibrated probabilities",
            "model_version": "global-translation-v1", "model_sha256": None,
            "data_provenance": data["manifest"], "evidence": [{"name": "Provider", "value": "Météo-France / MétéoNet"},
                         {"name": "Data sequence", "value": "19 Dec 2018 · 10:10–10:35"},
                         {"name": "Inputs", "value": "Two radar frames, five minutes apart"},
                         {"name": "Reuse", "value": "Etalab Open Licence 2.0"}]}


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "research", "model_ready": (ROOT / "data" / "model.json").exists()}


@app.post("/api/runs")
def run(request: RunRequest):
    started = time.perf_counter()
    try:
        result = simulated_run(request) if request.mode == "simulation" else observed_run(request)
    except (ValueError, RuntimeError, FileNotFoundError) as error:
        raise HTTPException(422, str(error)) from error
    request_data = request.model_dump()
    if request.mode == "observed":
        request_data = {"mode": "observed", "horizon": request.horizon, "hazard": "storm"}
    identity = json.dumps({"request": request_data, "version": result["model_version"], "model_sha": result["model_sha256"],
                           "code_sha256": CODE_SHA, "provenance": result["data_provenance"]}, sort_keys=True)
    result.update({"id": hashlib.sha256(identity.encode()).hexdigest()[:20], "request": request_data, "code_sha256": CODE_SHA,
                   "horizon": request.horizon, "latency_ms": round((time.perf_counter() - started) * 1000, 1)})
    return persist("runs", result)


@app.get("/api/runs/{identifier}")
def get_run(identifier: str):
    return lookup("runs", identifier)


@app.get("/api/evaluation")
def evaluation():
    path = ROOT / "data" / "evaluation.json"
    if not path.exists():
        raise HTTPException(404, "Train the simulator baseline to generate evaluation")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/image-methods")
def image_methods():
    return {"methods": METHODS, "preprocessing": PREPROCESSING, "horizons": [5, 10, 15, 20]}


@app.post("/api/image-runs")
def run_images(request: ImageRequest):
    try:
        return JSONResponse(image_run(request.method, request.preprocessing, request.horizon))
    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(422, str(error)) from error


@app.get("/api/data/catalog")
def get_data_catalog():
    return data_catalog.catalog()


@app.get("/api/data/files/{file_id}")
def data_file(file_id: str):
    try:
        path = data_catalog.resolve_file(file_id)
    except (KeyError, FileNotFoundError) as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return FileResponse(path, media_type="application/octet-stream", filename=path.name,
                        headers={"X-Content-Type-Options": "nosniff"})


@app.post("/api/data/collections/{collection_id}", status_code=202)
def collect_data(collection_id: str, body: CollectionRequest, request: Request):
    if not data_catalog.enabled():
        raise HTTPException(403, "Collection is disabled; set VAJRA_ENABLE_COLLECTIONS=1 on the local server")
    hostname = urlsplit("http://" + request.headers.get("host", "")).hostname
    if not request.client or request.client.host not in ("127.0.0.1", "::1") or hostname not in ("localhost", "127.0.0.1", "::1"):
        raise HTTPException(403, "Collection requires a direct loopback connection and local Host")
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "Collection requires application/json")
    origin = request.headers.get("origin")
    if origin and origin not in CORS_ORIGINS:
        raise HTTPException(403, "Untrusted collection origin")
    try:
        return data_catalog.start_collection(collection_id)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    except RuntimeError as error:
        raise HTTPException(409, str(error)) from error


@app.get("/api/data/jobs")
def collection_jobs():
    return {"jobs": data_catalog.jobs()}


@app.get("/api/data/jobs/{identifier}")
def collection_job(identifier: str):
    try:
        return data_catalog.get_job(identifier)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error


@app.post("/api/receipts")
def save_receipt(request: ReceiptRequest):
    result = lookup("runs", request.run_id)
    if result["mode"] != "simulation":
        raise HTTPException(422, "The observed radar sample has no verified site lightning target")
    site = next(site for site in result["sites"] if site["id"] == request.site_id)
    assessment = assess_research_decision(result, site, ResearchPolicy(
        request.threshold, request.preparation_minutes, request.min_recent_spatial_sources, request.max_source_age_minutes))
    identity = json.dumps({**request.model_dump(), "policy_version": POLICY_VERSION}, sort_keys=True)
    record = {"id": hashlib.sha256(identity.encode()).hexdigest()[:20], "run_id": result["id"],
              "type": "Simulation decision receipt", "site": site, "status": assessment["status"],
              "preparation_minutes": request.preparation_minutes, "threshold": request.threshold,
              "decision_deadline_minutes": assessment["decision_deadline_minutes"], "assessment": assessment,
              "decision_basis": "Forecast window start minus preparation time. Not a strike ETA or all-clear.",
              "issued_at": result["issued_at"], "valid_at": result["valid_at"], "model_version": result["model_version"],
              "model_sha256": result["model_sha256"], "sources": result["sources"], "target": result["target"],
              "calibration": result["calibration"], "code_sha256": result["code_sha256"],
              "data_provenance": result["data_provenance"], "request": result["request"],
              "dispatch": "Not sent; local review record only", "policy_version": POLICY_VERSION}
    return persist("receipts", record)


@app.get("/api/receipts/{identifier}")
def get_receipt(identifier: str):
    return lookup("receipts", identifier)


@app.get("/api/receipts")
def receipts():
    with closing(connection()) as db:
        rows = db.execute("SELECT payload FROM receipts ORDER BY rowid DESC LIMIT 100").fetchall()
    return [json.loads(row[0]) for row in rows]


@app.get("/research/{document}")
def research_document(document: str):
    allowed = {"SIH26072_RESEARCH_AND_BLUEPRINT.md": ROOT / "SIH26072_RESEARCH_AND_BLUEPRINT.md",
               "DATA_SOURCES.md": ROOT / "research" / "DATA_SOURCES.md",
               "MODEL_RESEARCH.md": ROOT / "research" / "MODEL_RESEARCH.md",
               "PROBLEM_EVIDENCE.md": ROOT / "research" / "PROBLEM_EVIDENCE.md",
               "PRODUCT_FLOW_AND_ALGORITHMS.md": ROOT / "PRODUCT_FLOW_AND_ALGORITHMS.md",
               "JEV_ASSESSMENT.md": ROOT / "research" / "JEV_ASSESSMENT.md",
               "FRIEND_NOTES_REVIEW.md": ROOT / "research" / "FRIEND_NOTES_REVIEW.md",
               "DETAILED_TECHNICAL_ARCHITECTURE.md": ROOT / "DETAILED_TECHNICAL_ARCHITECTURE.md",
               "TRAINING_GUIDE.md": ROOT / "docs" / "TRAINING_GUIDE.md",
               "MOBILE_GUIDE.md": ROOT / "docs" / "MOBILE_GUIDE.md"}
    if document not in allowed or not allowed[document].exists():
        raise HTTPException(404, "Research document not found")
    return FileResponse(allowed[document], media_type="text/markdown", filename=document)


if (ROOT / "dist").exists():
    app.mount("/", StaticFiles(directory=ROOT / "dist", html=True), name="app")

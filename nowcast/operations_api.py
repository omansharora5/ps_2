"""HTTP boundary for local research jobs and shared, read-only client evidence."""

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from .operation_store import OperationsStore
from .operation_recipes import prepare_demo_dataset, submit_recipe

ROOT = Path(__file__).resolve().parents[1]
router = APIRouter(prefix="/api/operations", tags=["Research operations"])
KINDS = (
    {"id": "starter_audit", "title": "Check government source files", "requires_dataset": False,
     "description": "Verify the downloaded manifests and bytes. These separate samples are not a training corpus."},
    {"id": "radar_replay", "title": "Evaluate observed radar motion", "requires_dataset": False,
     "description": "Compare a +10-minute optical-flow forecast with persistence on the historical French sample."},
    {"id": "train_candidate", "title": "Train and evaluate a candidate", "requires_dataset": True,
     "description": "Fit the compact ConvLSTM, calibrate on separate events and compare frozen results with a baseline."},
)
RESEARCH = (
    {"title": "Connected architecture and recovery", "url": "/research/OPERATIONS_GUIDE.md"},
    {"title": "Training data and preparation", "url": "/research/TRAINING_GUIDE.md"},
    {"title": "Calibration and verification", "url": "/research/CALIBRATION_AND_VERIFICATION.md"},
    {"title": "Regional decisions and continuous forecasts", "url": "/research/REGIONAL_DECISIONS_AND_CONTINUOUS_FORECASTS.md"},
)


def store():
    return OperationsStore(Path(os.environ.get("VAJRA_OPERATIONS_ROOT", ROOT / "data/operations")).resolve())


def trusted_origins():
    configured = [x.strip() for x in os.environ.get("VAJRA_CORS_ORIGINS", "").split(",") if x.strip()]
    return configured or [f"http://{host}:{port}" for host in ("localhost", "127.0.0.1")
                          for port in (8000, 8081, 8082, 5173, 4173)]


def local_request(request):
    try:
        hostname = urlsplit("http://" + request.headers.get("host", "")).hostname
    except ValueError:
        return False
    return bool(request.client and request.client.host in ("127.0.0.1", "::1")
                and hostname in ("localhost", "127.0.0.1", "::1")
                and request.headers.get("origin", trusted_origins()[0]) in trusted_origins())


def authorize_write(request):
    if os.environ.get("VAJRA_ENABLE_OPERATIONS") != "1" or not local_request(request):
        raise HTTPException(403, "Research operations require local access and VAJRA_ENABLE_OPERATIONS=1.")
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "Research operations require application/json.")


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["starter_audit", "radar_replay", "train_candidate"]
    dataset_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class EmptyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RetryRequest(EmptyRequest):
    expected_attempt: int = Field(ge=0, le=3)


class LearningRequest(EmptyRequest):
    enabled: bool


def public_job(job):
    fields = ("id", "kind", "status", "stage", "scope", "dataset_id", "attempt", "created_at",
              "updated_at", "started_at", "finished_at", "error", "summary")
    result = {key: job.get(key) for key in fields}
    result["artifacts"] = [{"id": a["id"], "name": a["name"], "bytes": a["bytes"], "sha256": a["sha256"],
                            "download_url": f"/api/operations/jobs/{job['id']}/artifacts/{a['id']}"}
                           for a in job.get("artifacts", [])]
    return result


def public_dataset(dataset):
    return {key: dataset[key] for key in ("id", "name", "scope", "learning_eligible", "readiness_reasons", "target")} | {
        "event_count": len(dataset["event_ids"])}


def public_learning(learning):
    return {"enabled": learning["enabled"], "status": learning["status"], "note": learning["note"],
            "last_checked_at": learning.get("checked_at"), "last_job_id": learning.get("job_id")}


def domain_call(action):
    try:
        return action()
    except KeyError as error:
        raise HTTPException(404, "The registered research record was not found.") from error
    except (ValueError, RuntimeError) as error:
        raise HTTPException(409, str(error)) from error
    except OSError as error:
        raise HTTPException(503, "The local research store is unavailable. Inspect the server log.") from error


@router.get("/state")
def state(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    def read():
        ledger = store()
        heartbeat = ledger.worker()
        last = heartbeat.get("heartbeat_at")
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(last.replace("Z", "+00:00"))).total_seconds() if last else None
        return {"schema_version": 1, "scope": "research_only",
                "writes_enabled": os.environ.get("VAJRA_ENABLE_OPERATIONS") == "1" and local_request(request),
                "worker": {"available": age is not None and 0 <= age <= 30, "last_seen_at": last,
                           "current_job_id": heartbeat.get("job_id")},
                "learning": public_learning(ledger.learning()),
                "datasets": [public_dataset(d) for d in ledger.datasets()],
                "jobs": [public_job(j) for j in ledger.jobs()],
                "recipes": list(KINDS), "research": list(RESEARCH)}
    return domain_call(read)


@router.post("/datasets/demo", status_code=201)
def prepare_example(body: EmptyRequest, request: Request):
    authorize_write(request)
    def prepare():
        ledger = store()
        return public_dataset(ledger.register_dataset(prepare_demo_dataset(ledger.root)))
    return domain_call(prepare)


@router.post("/jobs", status_code=202)
def create_job(body: JobRequest, request: Request):
    authorize_write(request)
    return domain_call(lambda: public_job(submit_recipe(store(), body.kind, body.dataset_id)))


@router.get("/jobs/{identifier}")
def job_detail(identifier: str):
    return domain_call(lambda: public_job(store().get(identifier)))


@router.post("/jobs/{identifier}/retry", status_code=202)
def retry_job(identifier: str, body: RetryRequest, request: Request):
    authorize_write(request)
    return domain_call(lambda: public_job(store().retry(identifier, body.expected_attempt)))


@router.post("/jobs/{identifier}/cancel")
def cancel_job(identifier: str, body: EmptyRequest, request: Request):
    authorize_write(request)
    return domain_call(lambda: public_job(store().cancel(identifier)))


@router.post("/learning")
def learning_policy(body: LearningRequest, request: Request):
    authorize_write(request)
    return domain_call(lambda: public_learning(store().set_learning(body.enabled)))


@router.get("/jobs/{identifier}/artifacts/{artifact_id}")
def artifact(identifier: str, artifact_id: str):
    def resolve():
        ledger = store()
        job = ledger.get(identifier)
        if job["status"] != "succeeded":
            raise KeyError("No committed artifacts")
        entry = next((a for a in job["artifacts"] if a["id"] == artifact_id), None)
        if entry is None:
            raise KeyError("Unknown artifact")
        path = (ledger.root / entry["relative_path"]).resolve()
        attempt_root = (ledger.root / "attempts" / identifier).resolve()
        if not attempt_root.is_relative_to(ledger.root.resolve()) or not path.is_relative_to(attempt_root) or not path.is_file():
            raise ValueError("The artifact is outside its registered attempt.")
        if path.stat().st_size != entry["bytes"] or entry["bytes"] > 128 * 1024 * 1024:
            raise ValueError("The artifact has an unexpected or unsupported size.")
        content = path.read_bytes()
        if len(content) != entry["bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise ValueError("The artifact failed its recorded integrity check.")
        return Response(content, media_type="application/octet-stream",
                        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store",
                                 "Content-Disposition": "attachment; filename*=UTF-8''" + quote(entry["name"], safe="")})
    return domain_call(resolve)

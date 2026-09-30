"""Exercise the running local API and numerical worker; retain compact evidence."""

import hashlib
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen
from datetime import datetime, timezone

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[1]


def call(path, body=None):
    request = Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                      headers={"Content-Type": "application/json", "Origin": BASE})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    started = time.monotonic()
    state = call("/api/operations/state")
    assert state["writes_enabled"] and state["worker"]["available"], "Start the enabled API and worker first"
    dataset = call("/api/operations/datasets/demo", {})
    assert dataset["learning_eligible"] is False
    assert call("/api/operations/datasets/demo", {})["id"] == dataset["id"]
    results = []
    for kind in ("starter_audit", "radar_replay", "train_candidate"):
        payload = {"kind": kind}
        if kind == "train_candidate":
            payload["dataset_id"] = dataset["id"]
        job = call("/api/operations/jobs", payload)
        deadline = time.monotonic() + 180
        while job["status"] in ("queued", "running") and time.monotonic() < deadline:
            time.sleep(1)
            job = call("/api/operations/jobs/" + job["id"])
        assert job["status"] == "succeeded", job
        repeat = call("/api/operations/jobs", payload)
        assert (repeat["id"], repeat["attempt"], repeat["finished_at"]) == (job["id"], job["attempt"], job["finished_at"])
        checked = []
        for artifact in job["artifacts"]:
            with urlopen(BASE + artifact["download_url"], timeout=30) as response:
                content = response.read()
            assert len(content) == artifact["bytes"]
            assert hashlib.sha256(content).hexdigest() == artifact["sha256"]
            checked.append({key: artifact[key] for key in ("name", "bytes", "sha256")})
        results.append({"kind": kind, "id": job["id"], "attempt": job["attempt"], "status": job["status"],
                        "duplicate_reused": True, "summary": job["summary"], "artifacts_verified": checked})
        print(json.dumps({"kind": kind, "status": job["status"], "attempt": job["attempt"]}), flush=True)
    previous = call("/api/operations/state")["learning"]["enabled"]
    try:
        call("/api/operations/learning", {"enabled": True})
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            state = call("/api/operations/state")
            if state["learning"]["last_checked_at"]:
                break
            time.sleep(1)
        assert state["learning"]["status"] == "waiting_for_labels", "This check expects a demo-only store"
        learning = state["learning"]
    finally:
        call("/api/operations/learning", {"enabled": previous})
    for reference in state["research"]:
        with urlopen(BASE + reference["url"], timeout=15) as response:
            assert response.status == 200 and len(response.read()) > 100
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "status": "passed",
              "elapsed_seconds": round(time.monotonic() - started, 2), "dataset_id": dataset["id"],
              "scope": "Local API and actual CPU worker; generated training examples and historical radar only",
              "jobs": results, "synthetic_excluded_from_daily_learning": learning,
              "research_links_checked": len(state["research"]), "public_dispatch": False}
    (ROOT / "artifacts/operations-workflow-check.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Operations API/worker workflow passed", flush=True)


if __name__ == "__main__":
    main()

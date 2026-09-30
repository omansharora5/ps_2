"""Boundary and real process-lifetime checks for the connected research runtime."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from nowcast import operations_api
from nowcast.operation_store import OperationsStore
from scripts import run_operations


NOW = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
PROJECT = Path(__file__).resolve().parents[1]


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def observed_metadata(version="one", *, available_at=None):
    """Scheduler-only fixture; no claim that its pretend file bytes exist."""
    roles = ("train", "validation", "calibration", "test")
    events = ["fixture-" + role for role in roles]
    return {
        "id": sha(version), "name": "Scheduler metadata fixture", "scope": "observed_research",
        "series": "scheduler-contract-fixture", "event_ids": events,
        "splits": {role: [event] for role, event in zip(roles, events)},
        "split_hashes": {role: sha(role) for role in roles}, "corpus_sha256": sha("corpus-" + version),
        "files": [{"name": event + ".npz", "event_id": event, "sha256": sha(event), "bytes": 12} for event in events],
        "learning_eligible": True, "labels_available_at": available_at or (NOW - timedelta(days=1)).isoformat(),
        "coverage_evidence": "Unit test metadata; no scientific observations represented",
        "created_at": NOW.isoformat(), "readiness_reasons": [], "target": "Unit-test scheduling contract",
    }


class OperationsRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "operations"
        self.env = patch.dict(os.environ, {"VAJRA_OPERATIONS_ROOT": str(self.root),
                                          "VAJRA_ENABLE_OPERATIONS": "1", "VAJRA_CORS_ORIGINS": ""})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.store = OperationsStore(self.root)
        self.app = FastAPI()
        self.app.include_router(operations_api.router)
        self.client = TestClient(self.app, base_url="http://localhost:8000", client=("127.0.0.1", 41000))
        self.addCleanup(self.client.close)

    def queue(self, identity="one"):
        return self.store.enqueue("starter_audit", {"recipe": "runtime-test", "input": identity}, {}, "research_only")

    def completed_artifact(self, *, outside=False):
        job = self.queue("outside" if outside else "inside")
        running = self.store.claim()
        self.assertEqual(running["id"], job["id"])
        relative = "unregistered/report.json" if outside else f"attempts/{job['id']}/{running['attempt_token']}/report.json"
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        content = b'{"scope":"research_only"}\n'
        path.write_bytes(content)
        artifact = {"id": "report", "name": "report.json", "relative_path": relative,
                    "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
        self.store.finish(job["id"], running["attempt_token"],
                          {"summary": {"scope": "research_only", "promoted": False}, "artifacts": [artifact]})
        return job["id"], path, content

    def test_api_write_requires_opt_in_loopback_host_origin_and_json(self):
        endpoint = "/api/operations/jobs"
        body = {"kind": "starter_audit"}
        with patch.dict(os.environ, {"VAJRA_ENABLE_OPERATIONS": "0"}):
            self.assertEqual(self.client.post(endpoint, json=body).status_code, 403)
        with TestClient(self.app, base_url="http://localhost:8000", client=("192.0.2.4", 42000)) as remote:
            self.assertEqual(remote.post(endpoint, json=body).status_code, 403)
            self.assertFalse(remote.get("/api/operations/state").json()["writes_enabled"])
        for headers in ({"Host": "attacker.example"}, {"Origin": "https://attacker.example"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.client.post(endpoint, json=body, headers=headers).status_code, 403)
        response = self.client.post(endpoint, content=json.dumps(body))
        # The framework may reject the missing media type before the endpoint.
        self.assertIn(response.status_code, (415, 422), response.text)
        response = self.client.post(endpoint, json={**body, "command": "arbitrary.exe"})
        self.assertEqual(response.status_code, 422)
        response = self.client.post(endpoint, json={"kind": "train_candidate", "dataset_id": "../../outside"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.store.jobs(), [])

    def test_repeated_api_submission_and_remote_monitor_share_safe_projection(self):
        response = self.client.post("/api/operations/jobs", json={"kind": "starter_audit"})
        self.assertEqual(response.status_code, 202, response.text)
        first = response.json()
        second = self.client.post("/api/operations/jobs", json={"kind": "starter_audit"}).json()
        self.assertEqual(first, second)
        self.assertEqual(len(self.store.jobs()), 1)
        running = self.store.claim()
        with TestClient(self.app, base_url="https://research.example", client=("192.0.2.4", 42000)) as mobile:
            detail = mobile.get(f"/api/operations/jobs/{first['id']}")
            state = mobile.get("/api/operations/state")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["status"], "running")
        self.assertFalse(state.json()["writes_enabled"])
        self.assertEqual(state.json()["jobs"][0], detail.json())
        for field in ("attempt_token", "identity", "parameters"):
            self.assertNotIn(field, detail.json())
        self.assertNotIn(running["attempt_token"], detail.text)
        self.assertNotIn(str(self.root), state.text)
        self.assertEqual(state.json()["schema_version"], 1)

    def test_api_can_retry_cancelled_unstarted_job_with_attempt_zero(self):
        job = self.client.post("/api/operations/jobs", json={"kind": "starter_audit"}).json()
        cancelled = self.client.post(f"/api/operations/jobs/{job['id']}/cancel", json={})
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["attempt"], 0)
        retried = self.client.post(f"/api/operations/jobs/{job['id']}/retry", json={"expected_attempt": 0})
        self.assertEqual(retried.status_code, 202, retried.text)
        duplicate = self.client.post(f"/api/operations/jobs/{job['id']}/retry", json={"expected_attempt": 0})
        self.assertEqual(retried.json(), duplicate.json())
        self.store.claim()
        stale = self.client.post(f"/api/operations/jobs/{job['id']}/retry", json={"expected_attempt": 0})
        self.assertEqual(stale.status_code, 409)

    def test_artifact_download_checks_hash_and_own_job_containment(self):
        identifier, path, content = self.completed_artifact()
        endpoint = f"/api/operations/jobs/{identifier}/artifacts/report"
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.content, content)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        detail = self.client.get(f"/api/operations/jobs/{identifier}").json()
        self.assertNotIn("relative_path", detail["artifacts"][0])
        self.assertEqual(detail["artifacts"][0]["download_url"], endpoint)
        path.write_bytes(b"x" * len(content))
        tampered = self.client.get(endpoint)
        self.assertEqual(tampered.status_code, 409)
        self.assertNotIn(str(path), tampered.text)
        outside_id, _, _ = self.completed_artifact(outside=True)
        outside = self.client.get(f"/api/operations/jobs/{outside_id}/artifacts/report")
        self.assertEqual(outside.status_code, 409)
        self.assertEqual(self.client.get(f"/api/operations/jobs/{identifier}/artifacts/unknown").status_code, 404)

    def test_artifact_response_uses_the_verified_snapshot_when_file_changes(self):
        identifier, path, content = self.completed_artifact()
        original = Path.read_bytes

        def replace_after_read(candidate):
            value = original(candidate)
            if candidate == path:
                candidate.write_bytes(b"x" * len(value))
            return value

        with patch.object(Path, "read_bytes", replace_after_read):
            response = self.client.get(f"/api/operations/jobs/{identifier}/artifacts/report")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, content, "The response must contain the bytes whose hash was checked")

    def test_real_process_lock_blocks_overlap_and_releases_after_abrupt_death(self):
        job = self.queue()
        script = """
import json, sys
from pathlib import Path
from nowcast.operation_store import OperationsStore
from scripts.run_operations import WorkerLock
root = Path(sys.argv[1])
with WorkerLock(root):
    store = OperationsStore(root)
    claimed = store.claim()
    print(json.dumps({'id': claimed['id'], 'attempt_token': claimed['attempt_token']}), flush=True)
    sys.stdin.read()
"""
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        process = subprocess.Popen([sys.executable, "-u", "-c", script, str(self.root)], cwd=PROJECT,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding="utf-8", **kwargs)
        try:
            with ThreadPoolExecutor(max_workers=1) as reader:
                future = reader.submit(process.stdout.readline)
                try:
                    line = future.result(timeout=15)
                except BaseException:
                    process.kill()
                    process.wait(timeout=10)
                    raise
            self.assertTrue(line, process.stderr.read() if process.poll() is not None else "Child did not claim a job")
            claimed = json.loads(line)
            self.assertEqual(claimed["id"], job["id"])
            with self.assertRaises(RuntimeError):
                with run_operations.WorkerLock(self.root):
                    self.fail("Concurrent process acquired an already owned lifetime lock")
            self.assertEqual(self.store.get(job["id"])["status"], "running")
            process.kill()
            process.wait(timeout=10)
            with run_operations.WorkerLock(self.root):
                self.assertEqual(self.store.recover_interrupted(), 1)
            self.assertEqual(self.store.get(job["id"])["stage"], "interrupted")
            self.assertFalse(self.store.finish(job["id"], claimed["attempt_token"], {"summary": {}, "artifacts": []}))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()

    def test_worker_records_attempt_directory_failure_instead_of_leaving_running(self):
        job = self.queue()
        original = Path.mkdir

        def unavailable_attempt(candidate, *args, **kwargs):
            if "attempts" in candidate.parts:
                raise OSError("Attempt directory is unavailable")
            return original(candidate, *args, **kwargs)

        with redirect_stderr(io.StringIO()), patch.object(Path, "mkdir", unavailable_attempt), patch("scripts.run_operations.execute_recipe") as execute:
            result = run_operations.work_once(self.store)
        execute.assert_not_called()
        self.assertEqual(result["id"], job["id"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("OSError", result["error"])

    def test_worker_recipe_failure_is_bounded_and_removes_local_paths(self):
        job = self.queue()
        error = ValueError(f"Cannot read {PROJECT}/private and {self.root}/private " + "x" * 2000)
        with redirect_stderr(io.StringIO()), patch("scripts.run_operations.execute_recipe", side_effect=error):
            failed = run_operations.work_once(self.store)
        self.assertEqual(failed["id"], job["id"])
        self.assertEqual(failed["status"], "failed")
        self.assertNotIn(str(PROJECT), failed["error"])
        self.assertNotIn(str(self.root), failed["error"])
        self.assertLess(len(failed["error"]), 800)
        self.assertEqual(failed["artifacts"], [])

    def test_demo_registration_is_repeatable_but_synthetic_data_never_autotrains(self):
        response = self.client.post("/api/operations/datasets/demo", json={})
        self.assertEqual(response.status_code, 201, response.text)
        repeated = self.client.post("/api/operations/datasets/demo", json={})
        self.assertEqual(response.json(), repeated.json())
        self.assertEqual(len(self.store.datasets()), 1)
        self.assertFalse(response.json()["learning_eligible"])
        self.assertEqual(response.json()["scope"], "synthetic_smoke_only")
        self.store.set_learning(True)
        decision = run_operations.learning_tick(self.store, now=NOW, force=True)
        self.assertEqual(decision["status"], "waiting_for_labels")
        self.assertEqual(self.store.jobs(), [])

    def test_daily_learning_deduplicates_unchanged_eligible_inputs_and_waits_after_success(self):
        frozen = self.store.register_dataset(observed_metadata())
        self.store.register_dataset(observed_metadata("future", available_at=(NOW + timedelta(days=2)).isoformat()))
        self.store.set_learning(True)
        first = run_operations.learning_tick(self.store, now=NOW, force=True)
        second = run_operations.learning_tick(self.store, now=NOW, force=True)
        self.assertEqual(first["job_id"], second["job_id"])
        self.assertEqual(len(self.store.jobs()), 1)
        self.assertEqual(run_operations.learning_tick(self.store, now=NOW + timedelta(hours=1)), second)
        running = self.store.claim()
        self.assertEqual(running["dataset_id"], frozen["id"])
        self.store.finish(running["id"], running["attempt_token"], {"summary": {"promoted": False}, "artifacts": []})
        third = run_operations.learning_tick(self.store, now=NOW + timedelta(days=1), force=True)
        self.assertEqual(third["status"], "waiting_for_new_events")
        self.assertEqual(len(self.store.jobs()), 1)
        self.assertEqual(self.store.get(running["id"])["summary"], {"promoted": False})
        disabled = self.store.set_learning(False)
        self.assertEqual(run_operations.learning_tick(self.store, now=NOW + timedelta(days=3), force=True), disabled)

    def test_failed_learning_candidate_does_not_consume_events_or_retry_automatically(self):
        self.store.register_dataset(observed_metadata())
        self.store.set_learning(True)
        first = run_operations.learning_tick(self.store, now=NOW, force=True)
        running = self.store.claim()
        self.store.fail(running["id"], running["attempt_token"], "Candidate evaluation failed")
        next_day = run_operations.learning_tick(self.store, now=NOW + timedelta(days=1), force=True)
        self.assertEqual(next_day["status"], "needs_review")
        self.assertEqual(next_day["job_id"], first["job_id"])
        self.assertEqual(len(self.store.jobs()), 1)
        self.assertEqual(self.store.get(running["id"])["attempt"], 1)
        self.assertEqual(self.store.get(running["id"])["status"], "failed")

    def test_scheduler_capacity_pressure_does_not_stop_worker_from_draining_queue(self):
        self.store.register_dataset(observed_metadata(available_at="2024-01-01T00:00:00Z"))
        self.store.set_learning(True)
        queued = self.queue()
        with patch("nowcast.operation_store.MAX_PENDING", 1), patch("scripts.run_operations.execute_recipe", return_value={"summary": {}, "artifacts": []}):
            result = run_operations.run_worker(self.store, once=True)
        self.assertEqual(result["id"], queued["id"])
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(len(self.store.jobs()), 1)
        self.assertTrue(self.store.learning()["enabled"])
        self.assertNotEqual(self.store.learning()["status"], "candidate_queued")
        self.assertEqual(run_operations.learning_tick(self.store, now=NOW, force=True)["status"], "candidate_queued")

    def test_failed_and_cancelled_series_do_not_block_other_independent_candidates(self):
        datasets = {}
        for index, name in enumerate(("failed", "cancelled", "eligible", "later")):
            record = observed_metadata(name)
            record["series"] = "scheduler-series-" + name
            record["created_at"] = (NOW - timedelta(minutes=index)).isoformat()
            datasets[name] = self.store.register_dataset(record)
        failed = run_operations.submit_recipe(self.store, "train_candidate", datasets["failed"]["id"])
        running = self.store.claim()
        self.store.fail(failed["id"], running["attempt_token"], "Candidate needs review")
        cancelled = run_operations.submit_recipe(self.store, "train_candidate", datasets["cancelled"]["id"])
        self.store.cancel(cancelled["id"])
        held_records = {job["id"]: self.store.get(job["id"]) for job in (failed, cancelled)}
        self.store.set_learning(True)

        first = run_operations.learning_tick(self.store, now=NOW, force=True)
        self.assertEqual(first["status"], "candidate_queued")
        self.assertIn("2 other series need review", first["note"])
        queued = [job for job in self.store.jobs() if job["status"] == "queued"]
        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0]["dataset_id"], datasets["eligible"]["id"])
        self.assertEqual(len(self.store.jobs()), 3)
        first_run = self.store.claim()
        self.store.finish(first_run["id"], first_run["attempt_token"], {"summary": {"promoted": False}, "artifacts": []})

        second = run_operations.learning_tick(self.store, now=NOW, force=True)
        self.assertEqual(second["status"], "candidate_queued")
        queued = [job for job in self.store.jobs() if job["status"] == "queued"]
        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0]["dataset_id"], datasets["later"]["id"])
        second_run = self.store.claim()
        self.store.finish(second_run["id"], second_run["attempt_token"], {"summary": {"promoted": False}, "artifacts": []})

        exhausted = run_operations.learning_tick(self.store, now=NOW, force=True)
        self.assertEqual(exhausted["status"], "needs_review")
        self.assertEqual(exhausted["job_id"], failed["id"])
        self.assertEqual(len(self.store.jobs()), 4)
        for identifier, record in held_records.items():
            self.assertEqual(self.store.get(identifier), record)


if __name__ == "__main__":
    unittest.main()

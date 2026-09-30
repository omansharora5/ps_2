from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nowcast.operation_store import OperationsStore


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def dataset(version="one", series="observed-series"):
    events = ["event-train", "event-validation", "event-calibration", "event-test"]
    return {
        "id": digest(version), "name": "Observed episodes", "scope": "observed_research", "series": series,
        "event_ids": events, "splits": {role: [event] for role, event in zip(("train", "validation", "calibration", "test"), events)},
        "files": [{"name": event + ".npz", "event_id": event, "sha256": digest(event), "bytes": 100} for event in events],
        "learning_eligible": True, "labels_available_at": "2026-09-28T01:00:00Z",
        "coverage_evidence": {"description": "Recorded label coverage for these fixture identities"},
        "created_at": "2026-09-30T00:00:00Z",
    }


def result(marker="complete"):
    return {"summary": {"scope": "synthetic_smoke_only", "message": marker}, "artifacts": [
        {"id": "report", "name": "report.json", "relative_path": "attempts/fixed/report.json", "sha256": digest(marker), "bytes": 42}
    ]}


class OperationsStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "operations"
        self.store = OperationsStore(self.root)

    def enqueue(self, marker="one", store=None):
        return (store or self.store).enqueue("starter_audit", {"recipe": "audit-v1", "input": marker}, {}, "starter_sample_integrity")

    def test_submission_survives_restart_and_duplicate_response_loss(self):
        first = self.enqueue()
        again = self.enqueue(store=OperationsStore(self.root))
        self.assertEqual(first, again)
        self.assertEqual(len(first["id"]), 64)
        self.assertEqual(first["attempt"], 0)
        claimed = self.store.claim()
        self.assertTrue(self.store.finish(first["id"], claimed["attempt_token"], result()))
        final = self.store.get(first["id"])
        self.assertEqual(self.enqueue(store=OperationsStore(self.root)), final)
        self.assertEqual(final["summary"]["message"], "complete")
        self.assertEqual(final["status"], "succeeded")
        self.assertEqual(len(self.store.jobs()), 1)

    def test_canonical_inputs_ignore_dictionary_order_but_include_parameters(self):
        first = self.store.enqueue("radar_replay", {"recipe": "v1", "input": "fixed"}, {"method": "persistence", "horizon": 10}, "observed_research")
        second = self.store.enqueue("radar_replay", {"input": "fixed", "recipe": "v1"}, {"horizon": 10, "method": "persistence"}, "observed_research")
        different = self.store.enqueue("radar_replay", {"input": "fixed", "recipe": "v1"}, {"horizon": 5, "method": "persistence"}, "observed_research")
        self.assertEqual(first, second)
        self.assertNotEqual(first["id"], different["id"])
        with self.assertRaises(ValueError):
            self.store.enqueue("radar_replay", {"input": "fixed", "recipe": "v1"}, {"horizon": 10, "method": "persistence"}, "different scope")

    def test_concurrent_duplicate_submission_and_claim_have_one_winner(self):
        stores = [OperationsStore(self.root) for _ in range(8)]
        with ThreadPoolExecutor(max_workers=8) as executor:
            submissions = list(executor.map(lambda store: self.enqueue(store=store), stores))
        self.assertEqual(len({item["id"] for item in submissions}), 1)
        self.enqueue("second")
        with ThreadPoolExecutor(max_workers=8) as executor:
            claims = list(executor.map(lambda store: store.claim(), stores))
        winners = [item for item in claims if item]
        self.assertEqual(len(winners), 1)
        self.assertEqual(winners[0]["attempt"], 1)
        self.assertIsNone(self.store.claim())
        self.store.finish(winners[0]["id"], winners[0]["attempt_token"], result())
        next_job = self.store.claim()
        self.assertNotEqual(next_job["id"], winners[0]["id"])

    def test_worker_restart_needs_explicit_recovery_and_retry(self):
        job = self.enqueue()
        first = self.store.claim()
        reopened = OperationsStore(self.root)
        self.assertEqual(reopened.get(job["id"])["status"], "running")
        self.assertIsNone(reopened.claim())
        self.assertEqual(reopened.recover_interrupted(), 1)
        interrupted = reopened.get(job["id"])
        self.assertEqual(interrupted["stage"], "interrupted")
        self.assertEqual(interrupted["status"], "failed")
        self.assertEqual(reopened.recover_interrupted(), 0)
        self.assertEqual(interrupted, reopened.get(job["id"]))
        self.assertFalse(reopened.finish(job["id"], first["attempt_token"], result("stale")))
        self.assertIsNone(reopened.claim())
        reopened.retry(job["id"], expected_attempt=1)
        second = reopened.claim()
        self.assertEqual(second["attempt"], 2)
        self.assertNotEqual(second["attempt_token"], first["attempt_token"])
        self.assertFalse(reopened.stage(job["id"], first["attempt_token"], "stale-stage"))
        self.assertFalse(reopened.fail(job["id"], first["attempt_token"], "stale failure"))
        self.assertFalse(reopened.finish(job["id"], first["attempt_token"], result("stale")))
        self.assertTrue(reopened.finish(job["id"], second["attempt_token"], result("current")))
        self.assertEqual(reopened.get(job["id"])["summary"]["message"], "current")

    def test_cancel_fences_running_publication_and_repeated_cancel_converges(self):
        job = self.enqueue()
        running = self.store.claim()
        cancelled = self.store.cancel(job["id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(self.store.cancel(job["id"]), cancelled)
        self.assertFalse(self.store.finish(job["id"], running["attempt_token"], result()))
        self.assertFalse(self.store.fail(job["id"], running["attempt_token"], "late error"))
        self.assertFalse(self.store.stage(job["id"], running["attempt_token"], "late-stage"))
        self.assertIsNone(self.store.get(job["id"])["summary"])
        self.assertEqual(self.store.get(job["id"])["artifacts"], [])
        self.store.retry(job["id"], expected_attempt=1)
        self.assertEqual(self.store.claim()["attempt"], 2)

    def test_cancel_queued_job_does_not_create_an_attempt(self):
        job = self.enqueue()
        cancelled = self.store.cancel(job["id"])
        self.assertEqual(cancelled["attempt"], 0)
        self.assertIsNone(self.store.claim())
        self.store.retry(job["id"], expected_attempt=0)
        self.assertEqual(self.store.claim()["attempt"], 1)

    def test_retry_duplicate_and_stale_precondition_do_not_start_later_attempt(self):
        job = self.enqueue()
        first = self.store.claim()
        self.store.fail(job["id"], first["attempt_token"], "First attempt failed")
        queued = self.store.retry(job["id"], expected_attempt=1)
        self.assertEqual(self.store.retry(job["id"], expected_attempt=1), queued)
        second = self.store.claim()
        with self.assertRaises(ValueError):
            self.store.retry(job["id"], expected_attempt=1)
        self.store.fail(job["id"], second["attempt_token"], "Second attempt failed")
        with self.assertRaises(ValueError):
            self.store.retry(job["id"], expected_attempt=1)
        self.assertEqual(self.store.get(job["id"])["status"], "failed")
        self.store.retry(job["id"], expected_attempt=2)
        third = self.store.claim()
        self.store.fail(job["id"], third["attempt_token"], "Third attempt failed")
        with self.assertRaises(ValueError):
            self.store.retry(job["id"], expected_attempt=3)

    def test_success_is_immutable_against_all_late_terminal_mutations(self):
        job = self.enqueue()
        running = self.store.claim()
        self.assertTrue(self.store.stage(job["id"], running["attempt_token"], "verifying"))
        self.assertEqual(self.store.get(job["id"])["stage"], "verifying")
        self.store.finish(job["id"], running["attempt_token"], result())
        expected = self.store.get(job["id"])
        self.assertFalse(self.store.finish(job["id"], running["attempt_token"], result("different")))
        self.assertFalse(self.store.fail(job["id"], running["attempt_token"], "late"))
        self.assertFalse(self.store.stage(job["id"], running["attempt_token"], "late"))
        self.assertEqual(self.store.cancel(job["id"]), expected)
        with self.assertRaises(ValueError):
            self.store.retry(job["id"], expected_attempt=1)
        self.assertEqual(self.store.get(job["id"]), expected)

    def test_competing_cancel_and_finish_cannot_publish_cancelled_artifacts(self):
        job = self.enqueue()
        running = self.store.claim()
        peer = OperationsStore(self.root)
        with ThreadPoolExecutor(max_workers=2) as executor:
            finished = executor.submit(self.store.finish, job["id"], running["attempt_token"], result())
            cancelled = executor.submit(peer.cancel, job["id"])
            did_finish = finished.result()
            cancelled.result()
        current = self.store.get(job["id"])
        self.assertEqual(current["status"], "succeeded" if did_finish else "cancelled")
        self.assertEqual(bool(current["artifacts"]), did_finish)

    def test_invalid_result_leaves_running_job_and_artifacts_uncommitted(self):
        job = self.enqueue()
        running = self.store.claim()
        malformed = result()
        malformed["artifacts"][0]["relative_path"] = "../secret"
        with self.assertRaises(ValueError):
            self.store.finish(job["id"], running["attempt_token"], malformed)
        self.assertEqual(self.store.get(job["id"]), running)
        malformed = result()
        malformed["summary"]["score"] = float("nan")
        with self.assertRaises(ValueError):
            self.store.finish(job["id"], running["attempt_token"], malformed)
        self.assertEqual(self.store.get(job["id"])["artifacts"], [])

    def test_pending_and_total_bounds_do_not_block_idempotent_reads(self):
        with patch("nowcast.operation_store.MAX_PENDING", 2), patch("nowcast.operation_store.MAX_JOBS", 3):
            first = self.enqueue()
            self.enqueue("second")
            with self.assertRaises(RuntimeError):
                self.enqueue("third")
            self.assertEqual(self.enqueue(), first)
            running = self.store.claim()
            self.store.finish(running["id"], running["attempt_token"], result())
            third = self.enqueue("third")
            self.store.cancel(third["id"])
            with self.assertRaises(RuntimeError):
                self.enqueue("fourth")
            self.assertEqual(len(self.store.jobs(limit=3)), 3)

    def test_retry_cannot_exceed_pending_capacity(self):
        with patch("nowcast.operation_store.MAX_PENDING", 1):
            first = self.enqueue()
            running = self.store.claim()
            self.store.fail(first["id"], running["attempt_token"], "retryable failure")
            second = self.enqueue("second")
            with self.assertRaises(RuntimeError):
                self.store.retry(first["id"], expected_attempt=1)
            self.assertEqual(self.store.get(first["id"])["status"], "failed")
            self.store.cancel(second["id"])
            self.assertEqual(self.store.retry(first["id"], expected_attempt=1)["status"], "queued")

    def test_dataset_registration_repeats_after_restart_without_rewriting_timestamp(self):
        original = dataset()
        registered = self.store.register_dataset(original)
        original["name"] = "mutated caller object"
        replacement = dataset()
        replacement["created_at"] = "2026-10-01T00:00:00Z"
        reopened = OperationsStore(self.root)
        self.assertEqual(reopened.register_dataset(replacement), registered)
        self.assertEqual(reopened.dataset(registered["id"]), registered)
        self.assertEqual(reopened.datasets(), [registered])
        job = reopened.enqueue("train_candidate", {"recipe": "v1"}, {"dataset_id": registered["id"]}, registered["scope"])
        self.assertEqual(job["dataset_id"], registered["id"])
        with self.assertRaises(ValueError):
            reopened.enqueue("train_candidate", {"recipe": "v2"}, {"dataset_id": registered["id"]}, "invented operational validation")
        replacement["name"] = "changed immutable metadata"
        with self.assertRaises(ValueError):
            reopened.register_dataset(replacement)

    def test_event_roles_and_bytes_are_immutable_within_the_series(self):
        original = self.store.register_dataset(dataset())
        for role in ("validation", "calibration", "test"):
            changed = dataset(role)
            moved = changed["splits"][role].pop()
            changed["splits"]["train"].append(moved)
            with self.subTest(role=role), self.assertRaises(ValueError):
                self.store.register_dataset(changed)
        changed = dataset("changed-content")
        changed["files"][0]["sha256"] = digest("altered observation")
        with self.assertRaises(ValueError):
            self.store.register_dataset(changed)
        self.assertEqual(self.store.datasets(), [original])
        compatible = dataset("next-version")
        compatible["event_ids"].append("new-training-event")
        compatible["splits"]["train"].append("new-training-event")
        compatible["files"].append({"name": "new.npz", "sha256": digest("new"), "bytes": 100, "event_id": "new-training-event"})
        self.assertEqual(self.store.register_dataset(compatible), compatible)

    def test_dataset_capacity_keeps_exact_duplicate_registration_available(self):
        with patch("nowcast.operation_store.MAX_DATASETS", 2):
            first = self.store.register_dataset(dataset("first"))
            self.store.register_dataset(dataset("second"))
            with self.assertRaises(RuntimeError):
                self.store.register_dataset(dataset("third"))
            repeated = dataset("first")
            repeated["created_at"] = "2026-10-01T00:00:00Z"
            self.assertEqual(self.store.register_dataset(repeated), first)
            self.assertEqual(len(self.store.datasets()), 2)
            self.assertEqual(OperationsStore(self.root).dataset(first["id"]), first)

    def test_role_guard_transaction_rolls_back_earlier_insertions_on_later_conflict(self):
        self.store.register_dataset(dataset())
        invalid = dataset("invalid")
        invalid["event_ids"].append("new-event")
        invalid["splits"]["train"].insert(0, "new-event")
        invalid["files"].append({"name": "new.npz", "sha256": digest("new"), "bytes": 100, "event_id": "new-event"})
        invalid["splits"]["train"].append(invalid["splits"]["test"].pop())
        with self.assertRaises(ValueError):
            self.store.register_dataset(invalid)
        valid = dataset("valid-after-rollback")
        valid["event_ids"].append("new-event")
        valid["splits"]["test"].append("new-event")
        valid["files"].append({"name": "new.npz", "sha256": digest("new"), "bytes": 100, "event_id": "new-event"})
        self.assertEqual(self.store.register_dataset(valid), valid)

    def test_invalid_dataset_partitions_and_file_identity_are_rejected(self):
        bad = dataset()
        bad["splits"]["train"].append("event-test")
        with self.assertRaises(ValueError): self.store.register_dataset(bad)
        bad = dataset()
        bad["files"][0]["event_id"] = "unknown"
        with self.assertRaises(ValueError): self.store.register_dataset(bad)
        bad = dataset()
        bad["files"][0]["name"] = "../input.npz"
        with self.assertRaises(ValueError): self.store.register_dataset(bad)
        bad = dataset()
        bad["labels_available_at"] = "2026-09-30T00:00:00"
        with self.assertRaises(ValueError): self.store.register_dataset(bad)
        self.assertEqual(self.store.datasets(), [])

    def test_learning_policy_persists_and_disable_wins_over_scheduler_result(self):
        initial = self.store.learning()
        self.assertFalse(initial["enabled"])
        self.assertEqual(self.store.set_learning(False), initial)
        enabled = self.store.set_learning(True)
        self.assertEqual(self.store.set_learning(True), enabled)
        self.assertEqual(OperationsStore(self.root).learning(), enabled)
        job = self.enqueue()
        recorded = self.store.record_learning("queued", "New covered episodes registered", job["id"], "2026-09-30T00:00:00Z")
        self.assertEqual(recorded["job_id"], job["id"])
        disabled = self.store.set_learning(False)
        self.assertEqual(self.store.record_learning("queued", "Stale scheduler result", job["id"]), disabled)
        self.assertEqual(OperationsStore(self.root).learning(), disabled)

    def test_heartbeat_never_authorizes_recovery_or_changes_job_status(self):
        self.assertIsNone(self.store.worker()["worker_id"])
        job = self.enqueue()
        running = self.store.claim()
        self.store.heartbeat("worker-one", job["id"])
        peer = OperationsStore(self.root)
        self.assertEqual(peer.worker()["job_id"], job["id"])
        peer.heartbeat("worker-two")
        self.assertEqual(peer.get(job["id"]), running)
        self.assertIsNone(peer.claim())
        self.assertEqual(peer.worker()["worker_id"], "worker-two")

    def test_reenabling_learning_resets_daily_check_only_on_enable_transition(self):
        self.store.set_learning(True)
        checked = self.store.record_learning("waiting_for_labels", "No new labels", checked_at="2026-09-30T10:00:00Z")
        self.assertEqual(self.store.set_learning(True), checked)
        disabled = self.store.set_learning(False)
        self.assertEqual(disabled["checked_at"], checked["checked_at"])
        self.assertEqual(self.store.set_learning(False), disabled)
        enabled = self.store.set_learning(True)
        self.assertIsNone(enabled["checked_at"])
        self.assertEqual(enabled["status"], "waiting_for_worker")
        self.assertEqual(self.store.set_learning(True), enabled)
        self.assertEqual(OperationsStore(self.root).learning(), enabled)

    def test_boundary_errors_are_domain_exceptions(self):
        with self.assertRaises(KeyError): self.store.get("a" * 64)
        with self.assertRaises(KeyError): self.store.dataset("a" * 64)
        with self.assertRaises(ValueError): self.store.get("../bad")
        with self.assertRaises(ValueError): self.store.jobs(0)
        with self.assertRaises(ValueError): self.store.jobs(True)
        with self.assertRaises(ValueError): self.store.enqueue("shell", {}, {}, "unsafe")
        with self.assertRaises(ValueError): self.store.enqueue("starter_audit", {"score": float("inf")}, {}, "invalid")
        with self.assertRaises(ValueError): self.store.enqueue("starter_audit", {1: "not a string key"}, {}, "invalid")
        with self.assertRaises(ValueError): self.store.enqueue("train_candidate", {}, {}, "missing dataset")
        with self.assertRaises(KeyError): self.store.enqueue("train_candidate", {}, {"dataset_id": "a" * 64}, "missing dataset")
        with self.assertRaises(ValueError): self.store.set_learning(1)
        with self.assertRaises(ValueError): self.store.record_learning("ok", "note", checked_at="not-time")
        self.assertEqual(self.store.jobs(), [])


if __name__ == "__main__":
    unittest.main()

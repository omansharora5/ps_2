from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from nowcast import community_store as data
from nowcast import community_api
from nowcast.service import app

NOW = data.timestamp("2026-09-30T16:22:00Z")
START = "2026-09-30T16:15:00Z"


def report(answer="yes", consent=True, **kwargs):
    return {"request_id": str(uuid4()), "installation_id": str(uuid4()), "cell_id": "delhi-central",
            "answer": answer, "observed_at_utc": data.utc(NOW), "consent_training": consent, **kwargs}


class CitizenEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = data.CommunityStore(Path(self.temp.name) / "reports.sqlite")
        self.clock = patch.object(data, "now", return_value=NOW)
        self.clock.start()

    def tearDown(self):
        self.clock.stop()
        self.temp.cleanup()

    def test_identical_retry_works_after_time_window_but_conflicting_or_repeat_votes_fail(self):
        body = report()
        first = self.store.submit(body)
        with patch.object(data, "now", return_value=NOW + timedelta(days=1)):
            second = self.store.submit(body)
        self.assertEqual(first["report_id"], second["report_id"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(second["aggregate"]["yes"], 1)
        with self.assertRaises(data.Conflict):
            self.store.submit(dict(body, answer="no"))
        with self.assertRaises(data.Conflict):
            self.store.submit(dict(body, request_id=str(uuid4())))
        with self.assertRaises(data.Conflict):
            self.store.submit(dict(body, request_id=str(uuid4()), cell_id="noida"))

    def test_concurrent_identical_requests_record_exactly_one_report(self):
        body = report()
        with ThreadPoolExecutor(max_workers=4) as workers:
            receipts = list(workers.map(lambda _: self.store.submit(body), range(4)))
        self.assertEqual(len({r["report_id"] for r in receipts}), 1)
        self.assertEqual(sum(not r["duplicate"] for r in receipts), 1)
        self.assertEqual(self.store.aggregate("delhi-central", START)["yes"], 1)

    def test_future_old_unknown_location_and_nonboolean_consent_are_rejected(self):
        for changes in ({"observed_at_utc": data.utc(NOW + timedelta(seconds=1))},
                        {"observed_at_utc": data.utc(NOW - timedelta(minutes=16))},
                        {"observed_at_utc": "2026-09-30T16:22:00"}, {"cell_id": "unknown"},
                        {"consent_training": "true"}, {"answer": "probably"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.store.submit(report(**changes))
        self.assertEqual(self.store.aggregate("delhi-central", START)["yes"], 0)

    def test_majority_is_not_truth_and_nonconsent_uncertainty_do_not_authorize_training(self):
        for _ in range(5):
            self.store.submit(report(consent=False))
        for _ in range(5):
            self.store.submit(report(answer="unsure"))
        aggregate = self.store.aggregate("delhi-central", START)
        self.assertEqual(aggregate["yes"], 5)
        self.assertEqual(aggregate["consensus"], "insufficient")
        self.assertFalse(aggregate["training_eligible"])
        with self.assertRaises(ValueError):
            self.store.review("delhi-central", START, aggregate["revision"], "approve", "Checked an independent record", "https://mausam.imd.gov.in/")
        self.assertEqual(self.store.reviewed_export()["items"], [])

    def test_review_waits_for_closed_window_and_export_is_versioned_weak_and_private(self):
        for _ in range(5):
            self.store.submit(report())
        aggregate = self.store.aggregate("delhi-central", START)
        self.assertEqual(aggregate["consensus"], "rain_support")
        self.assertFalse(aggregate["training_eligible"])
        args = ("delhi-central", START, aggregate["revision"], "approve", "Checked matching independent station evidence", "https://mausam.imd.gov.in/")
        with self.assertRaisesRegex(ValueError, "late submissions"):
            self.store.review(*args)
        self.assertEqual(self.store.reviewed_export()["items"], [])
        self.assertEqual(aggregate["reviewable_after_utc"], "2026-09-30T16:45:00Z")
        self.store.submit(report(answer="no"))
        with patch.object(data, "now", return_value=data.timestamp("2026-09-30T16:45:00Z")):
            with self.assertRaises(data.Conflict):
                self.store.review(*args)
            aggregate = self.store.aggregate("delhi-central", START)
            args = (*args[:2], aggregate["revision"], *args[3:])
            review = self.store.review(*args)
            self.assertEqual(self.store.review(*args), review)
            exported = self.store.reviewed_export()
            with self.assertRaises(ValueError):
                self.store.submit(report())
        self.assertEqual(len(exported["items"]), 1)
        item = exported["items"][0]
        self.assertEqual(item["label_class"], "reviewed_weak_evidence")
        self.assertFalse(item["ground_truth"])
        self.assertFalse(item["eligible_for_lightning"])
        self.assertNotIn("installation", json.dumps(exported))
        # A premature legacy approval is never exported while the window is open.
        self.assertEqual(self.store.reviewed_export()["items"], [])

    def test_approval_requires_corroboration_not_an_agreement_percentage(self):
        for _ in range(5):
            self.store.submit(report(answer="no"))
        aggregate = self.store.aggregate("delhi-central", START)
        for url in ("", "http://example.com", "https://example.com/?token=secret", "https://example.com/#token=secret", "https://user:pass@example.com"):
            with self.assertRaises(ValueError):
                self.store.review("delhi-central", START, aggregate["revision"], "approve", "An independent observation was checked", url)
        self.assertFalse(self.store.aggregate("delhi-central", START)["training_eligible"])


class CommunityApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict("os.environ", {"VAJRA_COMMUNITY_ROOT": self.temp.name, "VAJRA_NCR_ROOT": self.temp.name,
                                             "VAJRA_ENABLE_FEEDBACK": "1"})
        self.env.start()
        self.clock = patch.object(data, "now", return_value=NOW)
        self.clock.start()
        community_api._rate_buckets.clear()
        self.client = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 41000))

    def tearDown(self):
        self.client.close()
        self.clock.stop()
        self.env.stop()
        self.temp.cleanup()

    def test_state_has_no_invented_forecast_or_scores(self):
        response = self.client.get("/api/community/state")
        self.assertEqual(response.status_code, 200, response.text)
        obj = response.json()
        self.assertIsNone(obj["evidence_card"]["lightning_probability"])
        self.assertIsNone(obj["evidence_card"]["onset_interval"])
        self.assertEqual(obj["scorecard"]["status"], "unavailable")
        self.assertFalse(obj["benchmark"]["raw_release_allowed"])
        self.assertEqual(self.client.get("/api/community/state?cell_id=outside").status_code, 422)
        self.assertEqual(self.client.get("/api/community/scorecard?month=bad").status_code, 422)

    def test_enabled_reporting_requires_json_trusted_browser_and_boolean_consent(self):
        body = report()
        self.assertEqual(self.client.post("/api/community/reports", json=body, headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.post("/api/community/reports", json=dict(body, consent_training="true")).status_code, 422)
        with patch.dict("os.environ", {"VAJRA_ENABLE_FEEDBACK": "0"}):
            self.assertEqual(self.client.post("/api/community/reports", json=body).status_code, 403)
        first = self.client.post("/api/community/reports", json=body)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertTrue(self.client.post("/api/community/reports", json=body).json()["duplicate"])
        self.assertEqual(self.client.post("/api/community/reports", json=dict(body, answer="no")).status_code, 409)
        for aggregate in (first.json()["aggregate"], self.client.get("/api/community/state").json()["aggregate"]):
            self.assertTrue(aggregate["counts_withheld"])
            self.assertFalse(set(aggregate) & {"yes", "no", "unsure", "consenting_reports", "revision", "agreement_fraction"})
        queue = self.client.get("/api/community/review-queue").json()
        self.assertEqual(queue["windows"][0]["yes"], 1)
        self.assertIn("reviewable_after_utc", queue["windows"][0])

    def test_remote_person_cannot_review_or_export_and_rate_limit_is_bounded(self):
        with TestClient(app, base_url="http://127.0.0.1:8000", client=("192.0.2.10", 41000)) as remote:
            self.assertEqual(remote.get("/api/community/export").status_code, 403)
            self.assertEqual(remote.get("/api/community/review-queue").status_code, 403)
        body = report()
        for _ in range(60):
            self.assertEqual(self.client.post("/api/community/reports", json=body).status_code, 200)
        self.assertEqual(self.client.post("/api/community/reports", json=body).status_code, 429)
        self.assertLessEqual(len(community_api._rate_buckets), 256)


if __name__ == "__main__":
    unittest.main()

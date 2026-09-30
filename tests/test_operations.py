from dataclasses import replace
from datetime import datetime, timedelta, timezone
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from nowcast.decision_policy import ResearchPolicy, assess_research_decision
from nowcast.forecast_updates import ForecastTicket, LatestForecastQueue
from nowcast.service import app


NOW = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)


def run_context():
    return {"mode": "simulation", "issued_at": NOW.isoformat(), "horizon": 30,
            "request": {"hazard": "lightning"}, "sources": [
                {"source": name, "state": "available", "valid_at": NOW.isoformat(), "available_at": NOW.isoformat()}
                for name in ("radar", "satellite", "lightning", "nwp")]}


class DecisionPolicyTests(unittest.TestCase):
    def test_high_probability_does_not_bypass_evidence_or_dispatch_gates(self):
        run = run_context()
        for source in run["sources"][:2]: source["state"] = "missing"
        result = assess_research_decision(run, {"probability": .99}, ResearchPolicy())
        self.assertTrue(result["threshold_met"])
        self.assertFalse(result["evidence_support_met"])
        self.assertEqual(result["usable_spatial_sources"], ["lightning"])
        self.assertEqual(result["status"], "hold_for_evidence")
        self.assertIsNone(result["decision_deadline_minutes"])
        self.assertFalse(result["public_dispatch_eligible"])

    def test_freshness_is_recomputed_from_causal_timestamps(self):
        run = run_context()
        run["sources"][0].update(valid_at=(NOW-timedelta(minutes=11)).isoformat(), age_minutes=0)
        run["sources"][1]["available_at"] = (NOW+timedelta(seconds=1)).isoformat()
        result = assess_research_decision(run, {"probability": .9}, ResearchPolicy())
        self.assertEqual([item["reason"] for item in result["source_checks"]], ["over_age_limit", "not_available_at_issue", "usable"])
        self.assertEqual(result["status"], "hold_for_evidence")

    def test_exact_threshold_and_negative_preparation_deadline_remain_visible(self):
        result = assess_research_decision(run_context(), {"probability": .7}, ResearchPolicy(threshold=.7))
        self.assertEqual(result["status"], "review")
        self.assertEqual(result["decision_deadline_minutes"], -5)
        self.assertFalse(result["public_dispatch_eligible"])
        self.assertTrue(any("not an exact strike ETA" in text for text in result["reasons"]))

    def test_unavailable_below_threshold_and_invalid_inputs(self):
        self.assertEqual(assess_research_decision(run_context(), {"probability": None}, ResearchPolicy())["status"], "unavailable")
        self.assertEqual(assess_research_decision(run_context(), {"probability": .1}, ResearchPolicy())["status"], "below_demo_threshold")
        with self.assertRaises(ValueError): ResearchPolicy(threshold=float('nan'))
        with self.assertRaises(ValueError): ResearchPolicy(min_recent_spatial_sources=4)
        with self.assertRaises(ValueError): assess_research_decision({**run_context(), "mode": "observed"}, {"probability": .9}, ResearchPolicy())
        with self.assertRaises(ValueError): assess_research_decision(run_context(), {"probability": float('nan')}, ResearchPolicy())

    def test_api_controls_persist_reasons_without_authorizing_dispatch(self):
        with tempfile.TemporaryDirectory() as directory, patch("nowcast.service.DB_PATH", Path(directory)/"test.sqlite"), TestClient(app) as client:
            run = client.post('/api/runs', json={"disabled": ["radar", "satellite"]}).json()
            body = {"run_id": run["id"], "threshold": .05, "min_recent_spatial_sources": 2, "max_source_age_minutes": 10}
            response = client.post('/api/receipts', json=body)
            self.assertEqual(response.status_code, 200, response.text)
            record = response.json()
            self.assertEqual(record["status"], "hold_for_evidence")
            self.assertFalse(record["assessment"]["public_dispatch_eligible"])
            self.assertEqual(record, client.post('/api/receipts', json=body).json())
            self.assertNotEqual(record["id"], client.post('/api/receipts', json={**body, "min_recent_spatial_sources": 1}).json()["id"])
            self.assertEqual(client.post('/api/receipts', json={**body, "max_source_age_minutes": -1}).status_code, 422)


def ticket(region="north", revision=0):
    return ForecastTicket(region, NOW, revision, "a"*64, "research-v1", NOW+timedelta(minutes=30))


class ForecastUpdateTests(unittest.TestCase):
    def test_duplicate_and_conflicting_manifest_are_different_cases(self):
        queue = LatestForecastQueue(["north"])
        self.assertTrue(queue.submit(ticket(), now=NOW))
        self.assertFalse(queue.submit(ticket(), now=NOW))
        with self.assertRaises(ValueError): queue.submit(replace(ticket(), input_sha256="b"*64), now=NOW)
        self.assertEqual(queue.counts()["pending"], 1)

    def test_new_input_during_inference_prevents_old_completion_from_publishing(self):
        queue = LatestForecastQueue(["north"])
        queue.submit(ticket(), now=NOW)
        running = queue.take(now=NOW)
        for revision in range(1, 1001): queue.submit(ticket(revision=revision), now=NOW)
        self.assertEqual(queue.counts(), {"configured_regions": 1, "pending": 1, "running": 1, "watermarks": 1, "max_running": 1})
        self.assertIsNone(queue.take(now=NOW))
        self.assertFalse(queue.complete(running, now=NOW))
        latest = queue.take(now=NOW)
        self.assertEqual(latest.revision, 1000)
        self.assertTrue(queue.complete(latest, now=NOW))
        self.assertFalse(queue.complete(latest, now=NOW))

    def test_regions_share_a_bounded_worker_without_duplicate_regional_work(self):
        queue = LatestForecastQueue(["north", "south"], max_running=2)
        queue.submit(ticket(), now=NOW)
        queue.take(now=NOW)
        queue.submit(ticket(revision=1), now=NOW)
        queue.submit(ticket("south"), now=NOW)
        self.assertEqual(queue.take(now=NOW).region, "south")
        self.assertIsNone(queue.take(now=NOW))
        with self.assertRaises(ValueError): queue.submit(ticket("unknown"), now=NOW)

    def test_expiry_failure_old_revisions_and_new_issue_order(self):
        queue = LatestForecastQueue(["north"])
        queue.submit(ticket(revision=10), now=NOW)
        self.assertFalse(queue.submit(ticket(revision=9), now=NOW))
        running = queue.take(now=NOW)
        self.assertFalse(queue.complete(running, now=NOW, succeeded=False))
        later = replace(ticket(), issued_at=NOW+timedelta(minutes=1))
        with self.assertRaises(ValueError): queue.submit(later, now=NOW)
        self.assertTrue(queue.submit(later, now=NOW+timedelta(minutes=1)))
        running = queue.take(now=NOW+timedelta(minutes=1))
        self.assertFalse(queue.complete(running, now=NOW+timedelta(minutes=30)))
        self.assertFalse(queue.submit(ticket(revision=11), now=NOW+timedelta(minutes=30)))

    def test_expired_waiting_work_and_invalid_configuration(self):
        queue = LatestForecastQueue(["north"])
        queue.submit(ticket(), now=NOW)
        self.assertIsNone(queue.take(now=NOW+timedelta(minutes=30)))
        self.assertEqual(queue.counts()["pending"], 0)
        with self.assertRaises(ValueError): LatestForecastQueue(["north", "north"])
        with self.assertRaises(ValueError): LatestForecastQueue(["north"], max_running=2)
        with self.assertRaises(ValueError): replace(ticket(), issued_at=NOW.replace(tzinfo=None))
        with self.assertRaises(ValueError): replace(ticket(), input_sha256="not-a-hash")


if __name__ == '__main__': unittest.main()

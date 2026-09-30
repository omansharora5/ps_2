import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from nowcast.service import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = patch("nowcast.service.DB_PATH", Path(self.directory.name) / "test.sqlite")
        self.db.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close(); self.db.stop(); self.directory.cleanup()

    def test_synthetic_run_and_receipt_are_idempotent_and_persisted(self):
        response = self.client.post("/api/runs", json={})
        self.assertEqual(response.status_code, 200, response.text)
        run = response.json()
        self.assertEqual(run["mode"], "simulation")
        again = self.client.post("/api/runs", json={}).json()
        self.assertEqual(run, again)
        receipt = self.client.post("/api/receipts", json={"run_id": run["id"], "threshold": 0.05}).json()
        self.assertEqual(receipt, self.client.post("/api/receipts", json={"run_id": run["id"], "threshold": 0.05}).json())
        self.assertEqual(len(self.client.get("/api/receipts").json()), 1)
        self.assertEqual(self.client.get(f"/api/receipts/{receipt['id']}").json(), receipt)
        self.assertEqual(receipt["dispatch"], "Not sent; local review record only")

    def test_bad_requests_fail_at_boundary(self):
        for body in [{"horizon": 999}, {"disabled": ["unknown"]}, {"step": -1}, {"mode": "live"}]:
            self.assertEqual(self.client.post("/api/runs", json=body).status_code, 422)

    def test_real_data_cannot_be_called_lightning(self):
        self.assertEqual(self.client.post("/api/runs", json={"mode": "observed", "horizon": 15, "hazard": "lightning"}).status_code, 422)
        run = self.client.post("/api/runs", json={"mode": "observed", "horizon": 15, "hazard": "storm"})
        self.assertEqual(run.status_code, 200, run.text)
        result = run.json()
        self.assertNotIn("fusion", result["layers"])
        self.assertGreater(result["metrics"]["advection"]["samples"], 0)
        self.assertEqual(result["metrics"]["advection"]["samples"], result["metrics"]["persistence"]["samples"])
        self.assertEqual(self.client.post("/api/receipts", json={"run_id": result["id"]}).status_code, 422)

    def test_all_sensors_missing_yields_null_not_zero(self):
        run = self.client.post("/api/runs", json={"disabled": ["radar", "satellite", "lightning", "nwp"]}).json()
        self.assertEqual(run["status"], "unavailable")
        self.assertIsNone(run["layers"]["fusion"][0][0])
        self.assertIsNone(run["sites"][0]["probability"])
        self.assertIsNone(run["metrics"]["fusion"]["brier"])

    def test_decision_uses_window_start_and_abstention_never_gives_all_clear(self):
        run = self.client.post("/api/runs", json={}).json()
        result = self.client.post("/api/receipts", json={"run_id": run["id"], "site_id": "nalanda", "threshold": 0.1, "preparation_minutes": 20}).json()
        self.assertEqual(result["status"], "review")
        self.assertEqual(result["decision_deadline_minutes"], -5)
        run = self.client.post("/api/runs", json={"disabled": ["radar", "satellite", "lightning", "nwp"]}).json()
        result = self.client.post("/api/receipts", json={"run_id": run["id"]}).json()
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["decision_deadline_minutes"])


if __name__ == "__main__": unittest.main()

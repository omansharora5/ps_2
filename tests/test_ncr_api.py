import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from nowcast import ncr_data
from nowcast.service import app
from tests.test_ncr_data import EVIDENCE, RETRIEVED, feature, page


def weather(description):
    item = feature(identifier="weather-1", value=None)
    item["properties"].update(name="present_weather", units="CODE TABLE", description=description,
                              phenomenonTime=item["properties"]["reportTime"])
    return item


class NcrApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict("os.environ", {"VAJRA_NCR_ROOT": str(self.root)})
        self.env.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env.stop()
        self.temp.cleanup()

    def collect(self):
        payload = ncr_data.encode(page([feature(value=0), weather("RAIN (NOT FREEZING)")]))
        return ncr_data.collect(self.root, "2026-09-29", "2026-09-29", getter=lambda _: payload)

    def test_empty_store_abstains_without_any_network_request(self):
        with patch("requests.get", side_effect=AssertionError("Read API must never fetch upstream")):
            response = self.client.get("/api/ncr/status")
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.json()["collection"])
            self.assertFalse(response.json()["automatic_collection_running"])
            result = self.client.get("/api/ncr/forecast").json()
            self.assertIsNone(result["prediction"])
            self.assertEqual(result["status"], "unavailable")

    def test_actual_local_collection_and_typed_pagination(self):
        manifest = self.collect()
        result = self.client.get("/api/ncr/observations?kind=observations&limit=1").json()
        self.assertEqual(result["collection_id"], manifest["id"])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["next_offset"], 1)
        labels = self.client.get("/api/ncr/observations?kind=present_weather").json()
        self.assertEqual(labels["items"][0]["category"], "rain")
        self.assertFalse(labels["items"][0]["eligible_as_exact_30_minute_label"])
        self.assertEqual(self.client.get("/api/ncr/observations?kind=observations&state=wet").status_code, 422)
        self.assertEqual(self.client.get("/api/ncr/observations?limit=501").status_code, 422)
        self.assertFalse(self.client.get("/api/ncr/status").json()["collection"]["training_ready_30_minutes"])

    def test_corrupted_derived_observations_are_not_served(self):
        manifest = self.collect()
        entry = next(e for e in manifest["derivatives"] if e["path"].endswith("precipitation_labels.json"))
        (self.root / entry["path"]).write_text("[]")
        self.assertEqual(self.client.get("/api/ncr/observations").status_code, 503)

    def test_omitted_weather_and_no_precipitation_are_not_misread_as_rain(self):
        cases = {"RAIN (NOT FREEZING)": "rain", "DRIZZLE, NOT FREEZING, CONTINUOUS": "drizzle",
                 "THUNDERSTORM, BUT NO PRECIPITATION AT THE TIME OF OBSERVATION": "explicit_no_precipitation",
                 "NO SIGNIFICANT PHENOMENON TO REPORT, PRESENT AND PAST WEATHER OMITTED": "unknown",
                 "HAZE": "unknown", "NO OBSERVATION, DATA NOT AVAILABLE, PRESENT AND PAST WEATHER OMITTED": "unknown"}
        for description, expected in cases.items():
            with self.subTest(description=description):
                row = ncr_data.normalize(weather(description), EVIDENCE["sha256"], RETRIEVED)
                self.assertEqual(ncr_data.present_weather_label(row)["category"], expected)
        first = page([weather("RAIN (NOT FREEZING)")])
        second = page([weather("THUNDERSTORM, BUT NO PRECIPITATION AT THE TIME OF OBSERVATION")])
        records, _, conflicts = ncr_data.normalize_pages([(first, EVIDENCE), (second, EVIDENCE)])
        self.assertTrue(conflicts)
        self.assertEqual(ncr_data.present_weather_label(records[0])["category"], "unknown")


if __name__ == "__main__":
    unittest.main()

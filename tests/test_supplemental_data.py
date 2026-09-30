import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from nowcast import supplemental_data as data
from nowcast.service import app


def forecast_payload():
    return data.encode({"utc_offset_seconds": 0, "latitude": 28.64, "longitude": 77.22,
                        "generationtime_ms": 0.12, "hourly_units": data.VARIABLES,
                        "hourly": {"time": ["2026-09-30T12:00"],
                                   **{key: [0] for key in data.VARIABLES}}})


class SourceInterpretationTests(unittest.TestCase):
    def test_model_zero_and_computation_time_are_not_observation_or_issue_time(self):
        rows, metadata = data.open_meteo(forecast_payload())
        self.assertFalse(rows[0]["label_eligible"])
        self.assertIsNone(rows[0]["model_initialized_at_utc"])
        self.assertEqual(rows[0]["precipitation_interval_start_utc"], "2026-09-30T11:00:00Z")
        self.assertFalse(metadata["generationtime_ms_is_model_issue_time"])
        invalid = json.loads(forecast_payload())
        invalid["hourly_units"]["wind_speed_10m"] = "km/h"
        with self.assertRaises(ValueError):
            data.open_meteo(data.encode(invalid))

    def test_iem_indian_zero_precipitation_is_rejected_but_rain_codes_are_preserved(self):
        body = b"station,valid,metar,wxcodes,p01i,tmpf,dwpf,sknt\nVIDP,2026-09-29 01:00,VIDP REPORT,-RA,0.00,86,68,10\n"
        rows, metadata = data.iem(body)
        self.assertIsNone(rows[0]["precipitation_mm"])
        self.assertEqual(rows[0]["present_weather_evidence"], "reported_rain_or_drizzle")
        self.assertAlmostEqual(rows[0]["temperature_c"], 30)
        self.assertAlmostEqual(rows[0]["wind_speed_m_s"], 5.14444444)
        self.assertFalse(rows[0]["label_eligible"])
        self.assertFalse(metadata["precipitation_amounts_supported_for_india"])
        for code in ("M", "", "HZ", "VCRA", "RERA", "TS", "SN"):
            self.assertEqual(data.raining_code(code), "unknown")
        for code in ("-RA", "+TSRA", "SHRA", "FZDZ", "BR -RASN"):
            self.assertEqual(data.raining_code(code), "reported_rain_or_drizzle")

    def test_meteostat_model_fill_retains_provenance_and_cannot_be_a_label(self):
        body = gzip.compress(b"year,month,day,hour,temp,temp_source,prcp,prcp_source\n2026,9,29,0,24,metar,0,dwd_mosmix\n2026,9,30,0,24,metar,1,dwd_mosmix\n")
        rows, _ = data.meteostat(body, "2026-09-29", "2026-09-30")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["variable_sources"]["prcp"], "dwd_mosmix")
        self.assertFalse(rows[0]["label_eligible"])

    def test_power_fill_is_missing_while_valid_model_zero_remains_zero(self):
        body = data.encode({"header": {"fill_value": -999, "time_standard": "UTC"},
                            "properties": {"parameter": {"PRECTOTCORR": {"2026092900": -999, "2026092901": 0}}},
                            "parameters": {"PRECTOTCORR": {"units": "mm/hour"}}})
        rows, _ = data.power(body)
        self.assertIsNone(rows[0]["values"]["PRECTOTCORR"])
        self.assertEqual(rows[1]["values"]["PRECTOTCORR"], 0)
        self.assertTrue(all(not row["label_eligible"] for row in rows))

    def test_rainviewer_hex_paths_work_but_coverage_and_scan_time_remain_unknown(self):
        obj = {"host": "https://tilecache.rainviewer.com", "radar": {"past": [
            {"time": 1790782800, "path": "/v2/radar/8601e435cee1"}], "nowcast": []}}
        rows, metadata = data.rainviewer(data.encode(obj))
        self.assertFalse(metadata["future_frames_supported"])
        self.assertIsNone(rows[0]["individual_radar_observed_at_utc"])
        self.assertEqual(rows[0]["ncr_coverage"], "unverified")
        self.assertIn("/2/0_0.png", rows[0]["tile_url_template"])
        obj["radar"]["past"][0]["path"] = "/v2/radar/../../private"
        with self.assertRaises(ValueError):
            data.rainviewer(data.encode(obj))
        obj["host"] = "http://127.0.0.1"
        with self.assertRaises(ValueError):
            data.rainviewer(data.encode(obj))

    def test_imerg_catalogue_has_no_rain_values_and_half_hour_conversion_is_explicit(self):
        body = data.encode({"feed": {"entry": [{"id": "G1", "title": "IMERG", "time_start": "2026-09-29T00:00:00Z",
                                               "time_end": "2026-09-29T00:29:59.999Z", "links": []}]}})
        rows, meta = data.imerg(body)
        self.assertFalse(rows[0]["scientific_payload_downloaded"])
        self.assertFalse(meta["catalogue_is_rainfall_data"])
        self.assertEqual(data.imerg_half_hour_amount(6, duration_minutes=30, quality_usable=True), 3)
        for value in (-9999, None, float("nan")):
            self.assertIsNone(data.imerg_half_hour_amount(value, duration_minutes=30, quality_usable=True))
        self.assertIsNone(data.imerg_half_hour_amount(6, duration_minutes=60, quality_usable=True))
        self.assertIsNone(data.imerg_half_hour_amount(6, duration_minutes=30, quality_usable=False))

    def test_requests_are_bounded_and_power_end_is_inclusive_only_upstream(self):
        url, _ = data.plan("power", "2026-09-23", "2026-09-30")
        self.assertIn("end=20260929", url)
        for start, end in (("2026-09-30", "2026-09-30"), ("2026-01-01", "2026-09-30")):
            with self.assertRaises(ValueError):
                data.plan("iem", start, end)
        with self.assertRaises(ValueError):
            data.plan("meteostat", "2025-12-31", "2026-01-02")
        with self.assertRaises(ValueError):
            data.fetch("https://example.com/private")


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def collect(self):
        with patch.object(data, "utc_now", return_value="2026-09-30T12:00:00Z"):
            return data.collect("open_meteo", self.root, "2026-09-23", "2026-09-30", getter=lambda _: forecast_payload())

    def test_duplicate_retry_reuses_snapshot_and_corruption_is_detected(self):
        first, second = self.collect(), self.collect()
        self.assertEqual(first, second)
        self.assertEqual(len(list(self.root.glob("open_meteo/*/manifest.json"))), 1)
        (self.root / "open_meteo" / first["id"] / "rows.json").write_text("[]")
        with self.assertRaises(ValueError):
            self.collect()

    def test_failed_publication_is_not_visible_and_retry_recovers(self):
        with patch.object(Path, "rename", side_effect=OSError("interrupted")), self.assertRaises(OSError):
            self.collect()
        self.assertIsNone(data.latest(self.root, "open_meteo"))
        manifest = self.collect()
        self.assertEqual(len(data.read_rows(self.root, manifest)), 1)
        pending = self.root / "open_meteo/.pending-leftover"
        pending.mkdir()
        (pending / "manifest.json").write_text("broken")
        self.assertEqual(data.latest(self.root, "open_meteo"), manifest)

    def test_corrupt_receipt_or_raw_file_fails_closed(self):
        manifest = self.collect()
        path = self.root / "open_meteo" / manifest["id"] / "manifest.json"
        body = path.read_bytes()
        edited = dict(manifest, retrieved_at_utc="2020-01-01T00:00:00Z")
        path.write_bytes(data.encode(edited))
        with self.assertRaises(ValueError):
            data.latest(self.root, "open_meteo")
        path.write_bytes(body)
        (path.parent / "raw.bin").write_bytes(b"broken")
        with self.assertRaises(ValueError):
            data.read_rows(self.root, manifest)

    def test_source_times_and_positions_are_checked_before_publication(self):
        rows = [{"observed_at_utc": "2099-01-01T00:00:00Z", "latitude": 28.56, "longitude": 77.1}]
        with self.assertRaises(ValueError):
            data.validate_rows("iem", rows, "2026-09-23", "2026-09-30", "2026-09-30T12:00:00Z")
        payload = json.loads(forecast_payload())
        for change in ({"latitude": 0}, {"hourly": {**payload["hourly"], "time": ["2026-09-30T12:30"]}}):
            with self.assertRaises(ValueError):
                data.open_meteo(data.encode({**payload, **change}))
        for quality in ("false", "true", 1, 0, None):
            self.assertIsNone(data.imerg_half_hour_amount(6, duration_minutes=30, quality_usable=quality))

    def test_read_api_uses_local_evidence_and_rejects_corruption(self):
        manifest = self.collect()
        with patch.dict("os.environ", {"VAJRA_SUPPLEMENTAL_ROOT": str(self.root)}), TestClient(app) as client:
            with patch("requests.get", side_effect=AssertionError("No upstream calls in read API")):
                status = client.get("/api/ncr/supplemental").json()
                self.assertFalse(status["model_context_fusion_connected"])
                rows = client.get("/api/ncr/supplemental/open_meteo?limit=1").json()
                self.assertEqual(rows["total"], 1)
                self.assertEqual(rows["collection_id"], manifest["id"])
                self.assertEqual(client.get("/api/ncr/supplemental/unknown").status_code, 404)
                self.assertEqual(client.get("/api/ncr/supplemental/iem?limit=501").status_code, 422)
                (self.root / "open_meteo" / manifest["id"] / "rows.json").write_text("[]")
                self.assertEqual(client.get("/api/ncr/supplemental/open_meteo").status_code, 503)


if __name__ == "__main__":
    unittest.main()

import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import collect_satellite_observations as satellite


def fake_payload():
    section1 = bytearray(22)
    section1[:3] = (22).to_bytes(3, "big")
    section1[10] = 5
    section1[13] = 31
    section1[15:17] = (2026).to_bytes(2, "big")
    section1[17:22] = bytes([9, 30, 13, 30, 0])
    section3 = (9).to_bytes(3, "big") + bytes([0, 0, 1, 192, 202, 77])
    section4 = (4).to_bytes(3, "big") + bytes([0])
    rest = bytes(section1) + section3 + section4 + b"7777"
    return b"IUCN46 DEMS 301330\r\n" + b"BUFR" + (8 + len(rest)).to_bytes(3, "big") + bytes([4]) + rest


def notification(payload):
    return {
        "id": "example",
        "properties": {
            "metadata_id": satellite.DATASET,
            "datetime": "2026-09-30T00:00:00Z",
            "pubtime": "2026-09-30T15:10:01Z",
            "integrity": {"method": "sha512", "value": base64.b64encode(hashlib.sha512(payload).digest()).decode()},
        },
        "links": [{"rel": "canonical", "href": "https://wis2box.imd.gov.in/data/example.b", "length": len(payload)}],
    }


class SatelliteObservationTests(unittest.TestCase):
    def test_header_keeps_typical_time_distinct_from_notification_date(self):
        header = satellite.validate_payload(fake_payload(), notification(fake_payload()))
        self.assertEqual(header["typical_at_utc"], "2026-09-30T13:30:00+00:00")
        self.assertEqual(header["unexpanded_descriptors"], [310077])
        self.assertEqual(header["data_category"], 5)

    def test_rejects_checksum_failure_and_fake_or_truncated_bufr(self):
        raw = fake_payload()
        with self.assertRaisesRegex(ValueError, "checksum"):
            satellite.validate_payload(raw[:-1] + b"x", notification(raw))
        for payload in [b"<html>login</html>", raw[:-4], b"BUFR\x00\x00\x08\x04"]:
            with self.subTest(payload=payload[:8]), self.assertRaises(ValueError):
                satellite.bufr_header(payload)

    def test_foreign_payload_host_rejected_before_download(self):
        raw = fake_payload()
        item = notification(raw)
        item["links"][0]["href"] = "https://example.com/data/stolen.b"
        calls = []
        def fetch(url, budget):
            calls.append(url)
            return json.dumps({"features": [item]}).encode()
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ValueError, "IMD"):
            satellite.collect(Path(folder), fetch)
        self.assertEqual(calls, [satellite.NOTIFICATIONS_URL])

    def test_url_and_redirect_guards(self):
        for url in ["http://wis2box.imd.gov.in/data/a", "https://wis2box.imd.gov.in.evil.test/data/a", "https://user@wis2box.imd.gov.in/data/a", "https://wis2box.imd.gov.in/data/../a", "https://wis2box.imd.gov.in/data/%2e%2e/a", "https://wis2box.imd.gov.in:8000/data/a"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                satellite.validate_download_url(url)
        with self.assertRaisesRegex(ValueError, "redirect"):
            satellite.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com")

    def test_budget_checked_before_payload_fetch(self):
        raw = fake_payload()
        item = notification(raw)
        item["links"][0]["length"] = satellite.MAX_TOTAL_BYTES + 1
        calls = []
        def fetch(url, budget):
            calls.append(url)
            return json.dumps({"features": [item]}).encode()
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ValueError, "budget"):
            satellite.collect(Path(folder), fetch)
        self.assertEqual(len(calls), 1)

    def test_snapshot_is_idempotent_and_verify_is_offline_and_detects_damage(self):
        raw = fake_payload()
        item = notification(raw)
        def fetch(url, budget):
            return json.dumps({"features": [item]}).encode() if url == satellite.NOTIFICATIONS_URL else raw
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = satellite.collect(root, fetch)
            second = satellite.collect(root, fetch)
            self.assertEqual(first, second)
            self.assertEqual(len(list((root / "snapshots").iterdir())), 1)
            self.assertFalse(second["training_ready"])
            self.assertFalse(second["imagery"])
            self.assertEqual(second["ncr_coverage"], "unknown_pending_decode")
            with patch.object(satellite, "BoundedFetcher", side_effect=AssertionError("HTTP forbidden")), patch("builtins.print"):
                self.assertEqual(satellite.main(["--output", folder, "--verify-only"]), 0)
            payload = root / "snapshots" / first["sha256"] / "payload.bufr"
            payload.write_bytes(raw + b"damaged")
            with self.assertRaisesRegex(ValueError, "checksum"):
                satellite.verify(root)


if __name__ == "__main__":
    unittest.main()

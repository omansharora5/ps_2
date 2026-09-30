import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from scripts import query_mosdac as mosdac


def response():
    return {"updated": "2026-09-30T20:53:19Z", "totalResults": 30, "totalSizeMB": 12972, "entries": [{"identifier": "3SIMG_30SEP2026_1430_L1B_STD_V01R00.h5", "id": "18512116", "dcDate": "2026-09-30T14:30:00Z/2026-09-30T15:00:00Z"}]}


class MosdacCatalogueTests(unittest.TestCase):
    def test_boundaries_reject_unbounded_or_invalid_queries(self):
        for count in [0, 11, -1, True]:
            with self.subTest(count=count), self.assertRaises(ValueError):
                mosdac.parameters("2026-09-30", count, mosdac.DEFAULT_BBOX)
        for bbox in ["0,0,100,90", "78,28,76,29", "NaN,28,78,29", "76,28,78"]:
            with self.subTest(bbox=bbox), self.assertRaises(ValueError):
                mosdac.parameters("2026-09-30", 2, bbox)

    def test_records_one_day_public_request_and_keeps_full_response(self):
        calls = []
        raw = json.dumps(response()).encode()
        def fetch(url):
            calls.append(url)
            return raw
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = mosdac.query(root, "2026-09-30", fetch=fetch)
            second = mosdac.query(root, "2026-09-30", fetch=fetch)
            self.assertEqual(first, second)
            params = parse_qs(urlsplit(calls[0]).query)
            self.assertEqual(params["startTime"], ["2026-09-30"])
            self.assertEqual(params["endTime"], ["2026-09-30"])
            self.assertEqual(params["count"], ["2"])
            self.assertEqual(urlsplit(calls[0]).hostname, "mosdac.gov.in")
            self.assertFalse(first["credentials_used"])
            self.assertFalse(first["training_ready"])
            self.assertEqual(first["scientific_payloads_downloaded"], 0)
            self.assertEqual(first["observation_intervals"], ["2026-09-30T14:30:00Z/2026-09-30T15:00:00Z"])
            self.assertEqual((root / "previews" / first["id"] / "response.json").read_bytes(), raw)

    def test_invalid_or_oversized_response_is_rejected(self):
        for raw in [b"{}", b"<html>login</html>", b"x" * (mosdac.MAX_RESPONSE_BYTES + 1)]:
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                mosdac.validate_response(raw, 2)
        data = response()
        data["entries"] = data["entries"] * 3
        with self.assertRaisesRegex(ValueError, "count"):
            mosdac.validate_response(json.dumps(data).encode(), 2)

    def test_config_matches_actual_official_sdk_and_has_no_credentials(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / "config/mosdac.ncr.example.json").read_text())
        self.assertEqual(config["user_credentials"], {"username/email": "", "password": ""})
        self.assertFalse(config["download_settings"]["skip_user_input"])
        self.assertEqual(config["search_parameters"]["count"], "2")
        self.assertEqual(config["search_parameters"]["startTime"], config["search_parameters"]["endTime"])

    def test_redirect_is_not_followed(self):
        with self.assertRaisesRegex(ValueError, "redirect"):
            mosdac.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com")


if __name__ == "__main__":
    unittest.main()

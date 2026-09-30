import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from nowcast import ncr_data as data


RETRIEVED = "2026-09-30T12:00:00Z"
REPORT = "2026-09-29T06:00:00Z"
INTERVAL = "2026-09-29T05:30:00Z/2026-09-29T06:00:00Z"
EVIDENCE = {"sha256": "a" * 64, "retrieved_at_utc": RETRIEVED}


def feature(identifier="rain-1", value=1.2, *, interval=INTERVAL, units="kg m-2"):
    return {"type": "Feature", "id": identifier,
            "geometry": {"type": "Point", "coordinates": [77.2, 28.6]},
            "properties": {"reportId": "station-report-1", "reportTime": REPORT,
                           "wigos_station_identifier": "0-20000-0-42182",
                           "name": data.PRECIP, "units": units, "value": value,
                           "phenomenonTime": interval}}


def page(features, *, matched=None, next_link=None):
    result = {"type": "FeatureCollection", "features": features,
              "numberMatched": len(features) if matched is None else matched}
    if next_link:
        result["links"] = [{"rel": "next", "href": next_link}]
    return result


def label(item):
    return data.precipitation_label(data.normalize(item, EVIDENCE["sha256"], RETRIEVED))


class PrecipitationEvidenceTests(unittest.TestCase):
    def test_positive_and_explicit_zero_keep_their_exact_interval(self):
        wet, zero = label(feature()), label(feature(value=0))
        self.assertEqual((wet["state"], wet["amount_mm"]), ("wet", 1.2))
        self.assertEqual((zero["state"], zero["amount_mm"]), ("reported_zero", 0.0))
        for result in (wet, zero):
            self.assertEqual(result["duration_minutes"], 30)
            self.assertTrue(result["eligible_as_exact_30_minute_label"])
            self.assertEqual(result["interval_start_utc"], INTERVAL.split("/")[0])

    def test_hourly_accumulation_cannot_label_either_half_hour(self):
        result = label(feature(interval="2026-09-29T05:00:00Z/2026-09-29T06:00:00Z"))
        self.assertEqual(result["state"], "wet")
        self.assertEqual(result["duration_minutes"], 60)
        self.assertFalse(result["eligible_as_exact_30_minute_label"])

    def test_missing_nonfinite_coded_or_unrecognised_values_remain_unknown(self):
        for value in (None, -1, -0.1, "0", True, float("nan"), float("inf")):
            with self.subTest(value=value):
                result = label(feature(value=value))
                self.assertEqual(result["state"], "unknown")
                self.assertFalse(result["eligible_as_exact_30_minute_label"])
        self.assertEqual(label(feature(units="inches"))["state"], "unknown")

    def test_invalid_or_ambiguous_interval_never_produces_a_dry_label(self):
        for interval in (None, REPORT, "invalid", "2026-09-29T06:00:00Z/2026-09-29T05:00:00Z",
                         "2026-09-29T06:00:00Z/2026-09-29T06:00:00Z",
                         "2026-09-29T05:30:00Z/2026-09-29T06:30:00Z",
                         "2026-09-29T05:30:00/2026-09-29T06:00:00"):
            with self.subTest(interval=interval):
                self.assertEqual(label(feature(value=0, interval=interval))["state"], "unknown")

    def test_no_precipitation_observation_is_not_a_zero_observation(self):
        item = feature(value=0)
        item["properties"]["name"] = "air_temperature"
        rows, labels, conflicts = data.normalize_pages([(page([item]), EVIDENCE)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(labels, [])
        self.assertEqual(conflicts, [])

    def test_identical_duplicates_deduplicate_but_conflicting_versions_are_unknown(self):
        first = feature(value=0)
        rows, labels, conflicts = data.normalize_pages([(page([first, copy.deepcopy(first)]), EVIDENCE)])
        self.assertEqual((len(rows), len(labels), conflicts), (1, 1, []))
        rows, labels, conflicts = data.normalize_pages([(page([first, feature(value=3)]), EVIDENCE)])
        self.assertEqual(conflicts, ["rain-1"])
        self.assertIsNone(rows[0]["value"])
        self.assertEqual(labels[0]["state"], "unknown")

    def test_outside_region_and_future_reports_are_rejected(self):
        for coordinates in ([76.49, 28.6], [77.2, 29.31], [float("nan"), 28.6]):
            item = feature()
            item["geometry"]["coordinates"] = coordinates
            with self.subTest(coordinates=coordinates), self.assertRaises(ValueError):
                data.normalize(item, EVIDENCE["sha256"], RETRIEVED)
        item = feature()
        item["properties"]["reportTime"] = "2026-10-01T00:00:00Z"
        with self.assertRaises(ValueError):
            data.normalize(item, EVIDENCE["sha256"], RETRIEVED)


class CollectionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def collect(self, getter, **kwargs):
        return data.collect(self.root, "2026-09-29", "2026-09-29", getter=getter, **kwargs)

    def test_repeated_complete_request_does_not_make_another_http_call(self):
        getter = Mock(return_value=data.encode(page([feature(), feature("rain-2", 0)])))
        first = self.collect(getter)
        second = self.collect(getter)
        self.assertEqual(first["status"], "complete")
        self.assertEqual(first, second)
        getter.assert_called_once()
        self.assertFalse(first["training_ready_30_minutes"])
        self.assertEqual(first["counts"]["precipitation_states"], {"wet": 1, "reported_zero": 1})

    def test_reuse_detects_corrupted_raw_and_derived_artifacts(self):
        for kind in ("files", "derivatives"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                getter = Mock(return_value=data.encode(page([feature()])))
                first = data.collect(directory, "2026-09-29", "2026-09-29", getter=getter)
                path = Path(directory) / first[kind][0]["path"]
                path.write_bytes(b"corruption")
                with self.assertRaisesRegex(ValueError, "integrity"):
                    data.collect(directory, "2026-09-29", "2026-09-29", getter=getter)
                getter.assert_called_once()

    def test_next_page_failure_retains_evidence_but_cannot_claim_complete(self):
        url = data.request_url("2026-09-29", "2026-09-29") + "&offset=1"
        getter = Mock(side_effect=[data.encode(page([feature()], matched=2, next_link=url)), TimeoutError()])
        result = self.collect(getter)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["counts"]["variable_records"], 1)
        self.assertEqual(result["failures"][0]["error_type"], "TimeoutError")
        self.assertEqual(getter.call_count, 2)
        data.verify(self.root, result)

    def test_number_matched_gap_is_partial_even_without_an_http_failure(self):
        result = self.collect(Mock(return_value=data.encode(page([feature()], matched=20))))
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["failures"], [])

    def test_unavailable_provider_does_not_create_zero_rain_records(self):
        result = self.collect(Mock(side_effect=TimeoutError()))
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["counts"]["precipitation_states"], {})
        self.assertEqual(data.read_rows(self.root, result, "precipitation"), [])

    def test_untrusted_pagination_is_rejected_before_requesting_it(self):
        for url in ("https://example.com/items", data.BASE + "/another/items",
                    data.request_url("2026-09-29", "2026-09-29").replace("https:", "http:")):
            with self.subTest(url=url):
                getter = Mock(return_value=data.encode(page([feature()], matched=2, next_link=url)))
                result = self.collect(getter, refresh=True)
                self.assertEqual(result["status"], "partial")
                getter.assert_called_once()
                self.assertEqual(result["failures"][0]["error_type"], "ValueError")

    def test_repeated_pagination_stops_without_an_infinite_collection(self):
        url = data.request_url("2026-09-29", "2026-09-29")
        getter = Mock(return_value=data.encode(page([feature()], matched=2, next_link=url)))
        result = self.collect(getter)
        self.assertEqual(result["status"], "partial")
        getter.assert_called_once()

    def test_page_and_total_download_budgets_are_enforced(self):
        with patch.object(data, "PAGE_BYTES", 20):
            result = self.collect(Mock(return_value=b" " * 21))
            self.assertEqual(result["status"], "unavailable")
            self.assertEqual(result["files"], [])
        body = data.encode(page([feature()], matched=2,
                               next_link=data.request_url("2026-09-29", "2026-09-29") + "&offset=1"))
        getter = Mock(side_effect=[body, body])
        with patch.object(data, "TOTAL_BYTES", len(body) + 1):
            result = self.collect(getter, refresh=True)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["files"]), 1)

    def test_provider_records_outside_requested_dates_are_not_accepted(self):
        item = feature()
        item["properties"]["reportTime"] = "2026-09-28T06:00:00Z"
        result = self.collect(Mock(return_value=data.encode(page([item]))))
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["counts"]["variable_records"], 0)


class HttpContractTests(unittest.TestCase):
    def test_fetch_bounds_stream_and_disallows_redirects(self):
        response = Mock(status_code=200)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.iter_content.return_value = iter([b"1234", b"5678"])
        with patch("requests.get", return_value=response) as request, patch.object(data, "PAGE_BYTES", 6):
            with self.assertRaisesRegex(ValueError, "bounded download"):
                data.fetch("https://wis2box.imd.gov.in/known")
        self.assertFalse(request.call_args.kwargs["allow_redirects"])
        self.assertEqual(request.call_args.kwargs["timeout"], (10, 30))
        self.assertTrue(request.call_args.kwargs["stream"])


if __name__ == "__main__":
    unittest.main()

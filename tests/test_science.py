import unittest
from dataclasses import replace
from datetime import datetime, timezone

import numpy as np

from nowcast.forecast import load_model, predict, targets
from nowcast.numerics import motion, translate
from nowcast.observations import mosaic_dbz, select_as_of, snapshot, synthetic_event
from nowcast.real_data import check_sequence, load_sample, replay
from nowcast.verification import verify


class ForecastScienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = load_model()

    def test_contingency_metrics_have_correct_denominators(self):
        p = np.array([[0.9, 0.8], [0.2, 0.1]])
        y = np.array([[1, 0], [1, 0]])
        result = verify(p, y)
        self.assertEqual((result["hits"], result["misses"], result["false_alarms"], result["correct_negatives"]), (1, 1, 1, 1))
        self.assertAlmostEqual(result["csi"], 1 / 3)
        self.assertEqual(result["pod"], 0.5)
        self.assertEqual(result["far"], 0.5)
        self.assertAlmostEqual(result["brier"], 0.325)

    def test_no_events_and_no_data_are_not_perfect_scores(self):
        result = verify(np.zeros((5, 5)), np.zeros((5, 5)))
        self.assertIsNone(result["csi"])
        self.assertIsNone(result["far"])
        self.assertIsNone(result["pod"])
        result = verify(np.full((5, 5), np.nan), np.zeros((5, 5)))
        self.assertEqual(result["samples"], 0)
        self.assertIsNone(result["brier"])

    def test_translation_does_not_wrap(self):
        field = np.zeros((8, 8)); field[3, 7] = 1
        shifted = translate(field, 0, 2)
        self.assertEqual(np.nansum(shifted), 0)
        self.assertTrue(np.isnan(shifted[:, :2]).all())

    def test_motion_recovers_known_translation(self):
        y, x = np.mgrid[:24, :24]
        before = np.exp(-((x - 10) ** 2 + (y - 11) ** 2) / 8)
        after = translate(before, 1, 2, fill=0)
        dy, dx = motion(before, after)
        self.assertEqual((dy, dx), (1, 2))

    def test_radar_blending_is_linear_z_and_missing_stays_missing(self):
        fields = np.array([[[10.0, np.nan]], [[30.0, np.nan]]])
        output = mosaic_dbz(fields, np.ones_like(fields))
        self.assertAlmostEqual(output[0, 0], 10 * np.log10(505))
        self.assertTrue(np.isnan(output[0, 1]))

    def test_future_truth_cannot_change_forecast(self):
        event = synthetic_event(62)
        before = predict(snapshot(event, 8), 30, self.model)
        changes = {}
        for name in ("radar", "satellite", "lightning", "nwp"):
            array = getattr(event, name).copy(); array[9:] = 999
            changes[name] = array
        after = predict(snapshot(replace(event, **changes), 8), 30, self.model)
        np.testing.assert_array_equal(before["fusion"]["lightning"], after["fusion"]["lightning"])

    def test_future_received_and_old_data_rejected(self):
        issue = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        records = [{"valid_at": "2026-01-01T11:55:00+00:00", "available_at": "2026-01-01T12:01:00+00:00"},
                   {"valid_at": "2026-01-01T12:05:00+00:00", "available_at": "2026-01-01T12:00:00+00:00"},
                   {"valid_at": "2026-01-01T11:00:00+00:00", "available_at": "2026-01-01T11:01:00+00:00"}]
        self.assertIsNone(select_as_of(records, issue, 10))
        good = {"valid_at": "2026-01-01T17:25:00+05:30", "available_at": "2026-01-01T17:27:00+05:30"}
        self.assertEqual(select_as_of([good, *records], issue, 10), good)

    def test_all_missing_or_only_nwp_abstains(self):
        event = synthetic_event(62)
        for disabled in [("radar", "satellite", "lightning", "nwp"), ("radar", "satellite", "lightning")]:
            result = predict(snapshot(event, 8, disabled), 30, self.model)
            self.assertTrue(result["abstained"])
            self.assertTrue(np.isnan(result["fusion"]["lightning"]).all())

    def test_stale_radar_is_excluded_from_forecast(self):
        event = synthetic_event(62)
        missing = predict(snapshot(event, 8, disabled=("radar",)), 30, self.model)
        stale = predict(snapshot(event, 8, stale=("radar",)), 30, self.model)
        np.testing.assert_array_equal(missing["fusion"]["lightning"], stale["fusion"]["lightning"])
        self.assertTrue(np.isnan(stale["persistence"]["storm"]).all())

    def test_lightning_window_excludes_issue_time(self):
        event = synthetic_event(62)
        lightning = np.zeros_like(event.lightning); lightning[8, 20, 20] = 1
        event = replace(event, lightning=lightning)
        self.assertEqual(targets(event, 8, 15)["lightning"].sum(), 0)
        lightning[9, 20, 20] = 1
        truth = targets(event, 8, 15)["lightning"]
        self.assertEqual(truth[20, 22], 1)
        self.assertEqual(truth[20, 23], 0)

    def test_splits_do_not_overlap(self):
        splits = [set(ids) for ids in self.model["splits"].values()]
        for i, one in enumerate(splits):
            for other in splits[i + 1:]: self.assertFalse(one & other)

    def test_real_sample_hashes_and_short_horizon(self):
        fields, dates, lat, lon, manifest = load_sample()
        self.assertEqual(fields.shape[0], 6)
        check_sequence(dates)
        self.assertEqual(lat.shape, fields.shape[1:])
        self.assertEqual(replay(20)["valid_at"], "2018-12-19 10:35:00")
        with self.assertRaises(ValueError): replay(60)
        with self.assertRaises(ValueError): check_sequence(["2018-12-19 10:10:00", "2018-12-19 10:20:00"])


if __name__ == "__main__": unittest.main()

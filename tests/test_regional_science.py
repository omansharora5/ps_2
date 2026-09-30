import unittest

import numpy as np

from nowcast.probability_evaluation import EventPredictions
from nowcast.regional_science import (PhaseEvent, apply_phase_calibration, evaluate_seasonal_zr,
    eligible_onset_distribution, fit_phase_calibration, fit_seasonal_zr, hazard_distribution, onset_summary, quality_diagnostics, survival_nll)


class RegionalScienceTests(unittest.TestCase):
    def test_survival_event_censoring_and_missingness_have_distinct_likelihoods(self):
        logits = np.zeros((3, 3))
        # Event in bin 1: survive bin 0 then event. Censor after bin 0: one survival term.
        loss = survival_nll(logits, [1, -1, 999], [3, 1, 999], [1, 1, 0])
        self.assertAlmostEqual(loss, 1.5 * np.log(2))
        with self.assertRaisesRegex(ValueError, "inside"):
            survival_nll(logits[:1], [2], [2], [1])
        with self.assertRaisesRegex(ValueError, "No covered"):
            survival_nll(logits[:1], [-1], [0], [0])

    def test_distribution_retains_no_event_mass_and_is_numerically_stable(self):
        output = hazard_distribution([0., 0., 0.], (10, 20, 30))
        np.testing.assert_allclose(output["event_mass"], [.5, .25, .125])
        self.assertAlmostEqual(float(output["no_event_probability"]), .125)
        for logits in ([1000., -1000.], [-1000., -1000.]):
            output = hazard_distribution(logits, (15, 30))
            self.assertAlmostEqual(float(output["event_mass"].sum() + output["no_event_probability"]), 1)
        with self.assertRaises(ValueError):
            hazard_distribution([0., 0.], (30, 10))

    def test_onset_interval_is_binned_conditional_and_does_not_invent_end(self):
        output = onset_summary([-100., 100., -100.], (10, 20, 30))
        self.assertEqual(output["conditional_onset_interval_minutes"], [10., 20.])
        self.assertIsNone(output["heavy_rain_end"])
        self.assertEqual(output["status"], "research_uncalibrated")
        self.assertIsNone(onset_summary([-1000., -1000.], (15, 30))["conditional_onset_interval_minutes"])

    def test_onset_distribution_masks_unknown_or_ongoing_event_pixels(self):
        result = eligible_onset_distribution(np.zeros((2, 3)), (10, 20, 30), [True, False])
        np.testing.assert_array_equal(result["eligible"], [True, False])
        self.assertTrue(np.isfinite(result["event_mass"][0]).all())
        self.assertTrue(np.isnan(result["event_mass"][1]).all())
        self.assertTrue(np.isnan(result["event_cdf"][1]).all())
        self.assertTrue(np.isnan(result["no_event_probability"][1]))
        for invalid in ([True], [1, 2], [True, None]):
            with self.assertRaisesRegex(ValueError, "eligibility"):
                eligible_onset_distribution(np.zeros((2, 3)), (10, 20, 30), invalid)

    def phase(self, name, phase="active", role="calibration"):
        predictions = EventPredictions(name, np.array([-4., -4., 4., 4.]), np.array([0., 1., 0., 1.]), np.ones(4))
        return PhaseEvent(predictions, phase, "2026-06-10T12:00:00Z", "2026-06-10T11:00:00Z", role)

    def test_phase_calibration_pools_sparse_and_unknown_strata(self):
        model = fit_phase_calibration([self.phase("a"), self.phase("b"), self.phase("c", "break")], min_events=2, min_each_class=2)
        self.assertEqual(model["phases"]["active"]["source"], "phase")
        self.assertEqual(model["phases"]["break"]["source"], "pooled_fallback")
        self.assertEqual(model["phases"]["unknown"]["source"], "pooled_fallback")
        result = apply_phase_calibration([4.], "unknown", model, issue_time="2026-06-10T12:00:00Z", phase_available_at="2026-06-10T11:00:00Z")
        self.assertLess(float(result["probabilities"][0]), .99)
        with self.assertRaisesRegex(ValueError, "available"):
            apply_phase_calibration([4.], "active", model, issue_time="2026-06-10T12:00:00Z", phase_available_at="2026-06-10T13:00:00Z")

    def test_calibration_refuses_test_data_duplicate_events_and_retrospective_phase(self):
        with self.assertRaisesRegex(ValueError, "Only calibration"):
            fit_phase_calibration([self.phase("a", role="test")])
        with self.assertRaisesRegex(ValueError, "unique"):
            fit_phase_calibration([self.phase("a"), self.phase("a")])
        with self.assertRaisesRegex(ValueError, "available"):
            PhaseEvent(self.phase("a").predictions, "active", "2026-06-10T12:00:00Z", "2026-06-10T13:00:00Z")

    def pairs(self, role="train", a=300., b=1.3):
        return [{"role": role, "event_id": f"{role}-{i // 3}", "season": "monsoon", "dbz": float(10 * np.log10(a * rain ** b)),
                 "rain_mm_h": rain, "rain_unit": "mm/h", "reflectivity_unit": "dBZ", "quality_passed": True,
                 "matched_support": "gauge-radar-paired-5min", "time_delta_seconds": 0.}
                for i, rain in enumerate([1., 2., 4., 2., 4., 8., 3., 6., 12.])]

    def test_seasonal_zr_recovers_known_relation_and_scores_only_held_out_events(self):
        model = fit_seasonal_zr(self.pairs())
        self.assertAlmostEqual(model["pooled"]["a"], 300.)
        self.assertAlmostEqual(model["pooled"]["b"], 1.3)
        score = evaluate_seasonal_zr(self.pairs("test"), model)
        self.assertLess(score["fitted"]["rmse_mm_h"], 1e-10)
        self.assertGreater(score["baseline"]["rmse_mm_h"], .1)
        leaking = self.pairs("test")
        leaking[0]["event_id"] = "train-0"
        with self.assertRaisesRegex(ValueError, "overlap"):
            evaluate_seasonal_zr(leaking, model)

    def test_zr_zero_is_excluded_from_log_fit_but_negative_or_wrong_units_reject(self):
        pairs = self.pairs()
        zero = dict(pairs[0], rain_mm_h=0.)
        model = fit_seasonal_zr(pairs + [zero])
        self.assertEqual(model["excluded_zero_rain_pairs"], 1)
        for bad in (dict(zero, rain_mm_h=-1), dict(zero, rain_unit="mm"), dict(zero, time_delta_seconds=301), dict(zero, role="test")):
            with self.assertRaises(ValueError):
                fit_seasonal_zr(pairs + [bad])
        sparse = dict(pairs[0], season="pre-monsoon", event_id="pre")
        self.assertEqual(fit_seasonal_zr(pairs + [sparse])["seasons"]["pre-monsoon"]["source"], "pooled_fallback")

    def test_diagnostics_are_descriptive_not_trained_detectors(self):
        result = quality_diagnostics(cloud_top_k=280., rain_observed=True, dust_reported=True)
        self.assertIn("radar_coverage_missing", result["flags"])
        self.assertIn("rain_reported_with_above_freezing_cloud_top", result["flags"])
        self.assertFalse(result["validated_warm_rain_detector"])
        self.assertFalse(result["validated_dust_detector"])


if __name__ == "__main__":
    unittest.main()

import json
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np

from nowcast.probability_evaluation import EventPredictions, evaluate_events, fit_temperature, probability_metrics
from scripts.train_images import corpus, evaluate, examples, make_model, make_smoke, normalizer, train


class ProbabilityEvaluationTests(unittest.TestCase):
    def test_hand_computed_scores_and_reliability_include_probability_one(self):
        result = probability_metrics(np.array([0., .2, .8, 1.]), np.array([0., 1., 0., 1.]), .5, bins=2)
        self.assertAlmostEqual(result["brier"], .32)
        self.assertAlmostEqual(result["average_precision"], 5 / 6)
        self.assertAlmostEqual(result["log_loss"], -np.log(.2) / 2, places=6)
        self.assertAlmostEqual(result["training_climatology_brier"], .25)
        self.assertAlmostEqual(result["brier_skill"], -.28)
        self.assertEqual(result["reliability"][0]["count"], 2)
        self.assertAlmostEqual(result["reliability"][0]["mean_probability"], .1)
        self.assertEqual(result["reliability"][0]["observed_frequency"], .5)
        self.assertEqual(result["reliability"][1]["count"], 2)
        self.assertEqual(result["hits"], 1)
        self.assertEqual(result["misses"], 1)
        self.assertEqual(result["false_alarms"], 1)
        self.assertEqual(result["pod"], .5)
        self.assertEqual(result["far"], .5)
        self.assertEqual(result["csi"], 1 / 3)

    def test_average_precision_ties_are_one_threshold_not_input_order(self):
        first = probability_metrics(np.array([.5, .5]), np.array([0., 1.]), .5)
        second = probability_metrics(np.array([.5, .5]), np.array([1., 0.]), .5)
        self.assertEqual(first["average_precision"], .5)
        self.assertEqual(first["average_precision"], second["average_precision"])

    def test_empty_threshold_denominators_and_single_class_are_explicit(self):
        result = probability_metrics(np.array([.1, .1]), np.array([0., 0.]), 0.)
        for key in ("pod", "far", "csi", "average_precision", "brier_skill"):
            self.assertIsNone(result[key], key)
        self.assertIsNone(result["reliability"][9]["mean_probability"])
        json.dumps(result, allow_nan=False)

    def test_covered_values_are_validated_unknown_cells_are_excluded(self):
        event = EventPredictions("one", np.array([0., np.nan]), np.array([1., np.nan]), np.array([1, 0]))
        report = evaluate_events([event], .5)
        self.assertEqual(report["raw"]["covered_pixels"], 1)
        self.assertEqual(report["raw"]["brier"], .25)
        self.assertEqual(report["event_bootstrap"]["status"], "unavailable")
        with self.assertRaisesRegex(ValueError, "coverage"):
            EventPredictions("one", np.array([0.]), np.array([1.]), np.array([2]))
        with self.assertRaisesRegex(ValueError, "finite"):
            EventPredictions("one", np.array([np.nan]), np.array([1.]), np.array([1]))
        with self.assertRaisesRegex(ValueError, "binary"):
            EventPredictions("one", np.array([0.]), np.array([2.]), np.array([1]))
        with self.assertRaisesRegex(ValueError, "covered"):
            evaluate_events([EventPredictions("one", np.array([0.]), np.array([1.]), np.array([0]))], .5)

    def test_temperature_reduces_overconfidence_on_calibration_data(self):
        event = EventPredictions("cal", np.array([-4., -4., 4., 4.]), np.array([0., 1., 0., 1.]), np.ones(4))
        params = fit_temperature([event])
        self.assertEqual(params["fit_status"], "fitted")
        self.assertGreater(params["temperature"], 1)
        report = evaluate_events([event], .5, params)
        self.assertLess(report["calibrated"]["log_loss"], report["raw"]["log_loss"])
        self.assertEqual(report["raw"]["average_precision"], report["calibrated"]["average_precision"])
        self.assertEqual(report["raw"]["hits"], report["calibrated"]["hits"])

    def test_degenerate_calibration_does_not_claim_a_fit(self):
        for logits, labels, status in (([1., 2.], [0., 0.], "identity_single_class"), ([1., 1.], [0., 1.], "identity_constant_logits")):
            params = fit_temperature([EventPredictions("cal", np.array(logits), np.array(labels), np.ones(2))])
            self.assertEqual(params["fit_status"], status)
            self.assertEqual(params["temperature"], 1.)

    def test_test_labels_cannot_change_frozen_temperature(self):
        calibration = EventPredictions("cal", np.array([-3., -1., 1., 3.]), np.array([0., 1., 0., 1.]), np.ones(4))
        params = fit_temperature([calibration])
        frozen = json.dumps(params, sort_keys=True)
        for labels in ([0., 0.], [1., 1.]):
            test = EventPredictions("test", np.array([-2., 2.]), np.array(labels), np.ones(2))
            evaluate_events([test], .25, params)
            self.assertEqual(json.dumps(params, sort_keys=True), frozen)
        self.assertEqual(fit_temperature([calibration]), params)

    def test_bootstrap_resamples_events_not_individual_pixels(self):
        logit = np.log(.1 / .9)
        events = [EventPredictions("a", np.full(100, logit), np.zeros(100), np.ones(100)),
                  EventPredictions("b", np.full(1, logit), np.ones(1), np.ones(1))]
        report = evaluate_events(events, .2)
        boot = report["event_bootstrap"]
        self.assertEqual(boot["event_count"], 2)
        self.assertEqual(boot["status"], "available")
        self.assertAlmostEqual(boot["intervals"]["raw_brier"]["lower"], .01)
        self.assertAlmostEqual(boot["intervals"]["raw_brier"]["upper"], .81)
        self.assertEqual(boot["intervals"]["raw_brier"]["valid_replicates"], 200)
        self.assertEqual(report, evaluate_events(events, .2))
        with self.assertRaisesRegex(ValueError, "unique"):
            evaluate_events(events + [events[0]], .2)


class CalibratedSplitTests(unittest.TestCase):
    def test_normalization_uses_unique_causal_measurements_and_accepts_reachable_late_data(self):
        with tempfile.TemporaryDirectory() as directory:
            make_smoke(directory, event_count=8)
            episodes, splits = corpus(directory, calibrate=True)
            first = episodes[0]
            first["available"][0] = first["times"][-1] + 1_000_000
            first["available"][1] = first["times"][3]
            mean, std = normalizer(episodes, splits["train"], history=3)
            # Frame zero is never available; frame one arrives at its last usable issue.
            expected = np.concatenate([first["values"][1:, 0].ravel(), episodes[1]["values"][:, 0].ravel()]).astype(float)
            np.testing.assert_allclose(mean, [expected.mean()], rtol=1e-6)
            np.testing.assert_allclose(std, [expected.std()], rtol=1e-6)
            before = examples(episodes, splits["train"], 3, mean, std)
            first["values"][0] = 1_000_000
            new_mean, new_std = normalizer(episodes, splits["train"], history=3)
            np.testing.assert_array_equal(new_mean, mean)
            np.testing.assert_array_equal(new_std, std)
            after = examples(episodes, splits["train"], 3, new_mean, new_std)
            for prior, updated in zip(before, after):
                np.testing.assert_array_equal(prior[0], updated[0])
            if importlib.util.find_spec("torch"):
                import torch
                model = make_model(2).eval()
                with torch.no_grad():
                    old = model(torch.from_numpy(np.stack([row[0] for row in before])))
                    new = model(torch.from_numpy(np.stack([row[0] for row in after])))
                self.assertTrue(torch.equal(old, new))

    def test_four_chronological_splits_are_disjoint_with_two_test_events(self):
        with tempfile.TemporaryDirectory() as directory:
            make_smoke(directory, event_count=8)
            episodes, splits = corpus(directory, calibrate=True)
            self.assertEqual(list(splits), ["train", "validation", "calibration", "test"])
            flat = [event for ids in splits.values() for event in ids]
            self.assertEqual(len(flat), len(set(flat)))
            self.assertEqual(len(splits["test"]), 2)
            self.assertEqual(len(episodes), 8)
            by_id = {e["meta"]["event_id"]: e for e in episodes}
            for left, right in zip(list(splits), list(splits)[1:]):
                self.assertLess(max(by_id[k]["ends"][-1] for k in splits[left]), min(by_id[k]["times"][0] for k in splits[right]))

    def test_six_group_default_survives_but_calibration_requires_eight(self):
        with tempfile.TemporaryDirectory() as directory:
            make_smoke(directory)
            self.assertEqual(set(corpus(directory)[1]), {"train", "validation", "test"})
            with self.assertRaisesRegex(ValueError, "eight"):
                corpus(directory, calibrate=True)

    def test_calibration_test_future_window_overlap_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            make_smoke(directory, event_count=8)
            path = Path(directory) / "episode-6.npz"
            with np.load(path, allow_pickle=False) as z:
                data = {k: z[k] for k in z.files}
            with np.load(Path(directory) / "episode-5.npz", allow_pickle=False) as z:
                for key in ("times_utc", "available_at_utc", "target_end_utc"):
                    data[key] = z[key]
            np.savez_compressed(path, **data)
            with self.assertRaisesRegex(ValueError, "calibration/test overlap"):
                corpus(directory, calibrate=True)

    @unittest.skipUnless(importlib.util.find_spec("torch"), "Actual ConvLSTM integration requires the opt-in .venv-ml environment")
    def test_training_and_temperature_ignore_test_labels_and_frozen_evaluation_rejects_changes(self):
        import torch
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            base = Path(directory)
            make_smoke(base / "episodes", event_count=8)
            args = SimpleNamespace(data=str(base / "episodes"), output=str(base / "first"), history=3,
                                   epochs=1, batch_size=3, device="cpu", calibrate=True)
            first_report = train(args)
            first_path = base / "first/model.pt"
            first = torch.load(first_path, map_location="cpu", weights_only=True)
            evaluated = evaluate(SimpleNamespace(data=args.data, checkpoint=str(first_path)))
            self.assertEqual(evaluated["test"], first_report["test"])
            self.assertEqual(evaluated["test_calibrated"], first_report["test_calibrated"])
            self.assertEqual(evaluated["probability_verification"], first_report["probability_verification"])
            sidecar = json.loads((base / "first/calibration.json").read_text())
            self.assertEqual(sidecar["calibrator"], first["calibrator"])
            for path in (base / "episodes").glob("*.npz"):
                with np.load(path, allow_pickle=False) as z:
                    data = {k: z[k] for k in z.files}
                if json.loads(str(data["metadata_json"].item()))["event_id"] in first["splits"]["test"]:
                    data["targets"] = 1 - data["targets"]
                    np.savez_compressed(path, **data)
            with self.assertRaisesRegex(ValueError, "corpus differs"):
                evaluate(SimpleNamespace(data=args.data, checkpoint=str(first_path)))
            args.output = str(base / "second")
            second_report = train(args)
            second = torch.load(base / "second/model.pt", map_location="cpu", weights_only=True)
            self.assertEqual(first["calibrator"], second["calibrator"])
            self.assertEqual(first["training_climatology"], second["training_climatology"])
            self.assertEqual(first["mean"], second["mean"])
            self.assertEqual(first["std"], second["std"])
            self.assertEqual(first_report["history"], second_report["history"])
            for name in first["state_dict"]:
                self.assertTrue(torch.equal(first["state_dict"][name], second["state_dict"][name]), name)
            for split in ("train", "validation", "calibration"):
                self.assertEqual(first["split_hashes"][split], second["split_hashes"][split])
            self.assertNotEqual(first["split_hashes"]["test"], second["split_hashes"]["test"])
            self.assertNotEqual(first_report["test"]["brier"], second_report["test"]["brier"])


if __name__ == "__main__":
    unittest.main()

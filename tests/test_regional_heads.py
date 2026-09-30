import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from nowcast.regional_heads import make_regional_model, regional_loss
from nowcast.regional_science import survival_nll
from scripts.train_regional_heads import load_corpus, make_fixture, predict_history, prepare_inputs, train_corpus


class RegionalCorpusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = make_fixture(Path(self.temporary.name) / "fixture.npz")

    def alter(self, change):
        with np.load(self.path, allow_pickle=False) as source:
            data = {key: source[key] for key in source.files}
        change(data)
        np.savez_compressed(self.path, **data)

    def test_core_imports_do_not_load_torch(self):
        result = subprocess.run([sys.executable, "-c", "import sys; import nowcast.regional_science, nowcast.regional_heads; assert 'torch' not in sys.modules"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_future_arriving_inputs_are_masked_and_train_only_normalization_is_stable(self):
        original = load_corpus(self.path)
        _, expected = prepare_inputs(original)
        def modify(data):
            data["values"][-1] = 99999.
            data["available_at_utc"][0, -1, 0] = "2020-01-01T12:05:00Z"
        self.alter(modify)
        changed = load_corpus(self.path)
        self.assertFalse(changed["causal"][0, -1, 0].any())
        # Changing a held-out sample alone must not affect fitted normalization.
        changed["causal"] = original["causal"]
        _, actual = prepare_inputs(changed)
        self.assertEqual(actual, expected)

    def test_duplicate_event_across_split_is_rejected(self):
        self.alter(lambda d: d["event_ids"].__setitem__(-1, d["event_ids"][0]))
        with self.assertRaisesRegex(ValueError, "cannot cross"):
            load_corpus(self.path)

    def test_retrospective_phase_is_rejected(self):
        self.alter(lambda d: d["phase_available_at_utc"].__setitem__(0, "2020-01-02T12:00:00Z"))
        with self.assertRaisesRegex(ValueError, "available"):
            load_corpus(self.path)

    def test_adjacent_partitions_cannot_share_input_or_future_label_time(self):
        def change(data):
            for key in ("times_utc", "available_at_utc", "issue_utc", "target_end_utc", "phase_available_at_utc"):
                data[key][2] = data[key][1]
        self.alter(change)
        with self.assertRaisesRegex(ValueError, "overlap"):
            load_corpus(self.path)

    def test_onset_needs_event_free_initial_state(self):
        self.alter(lambda d: d["rain_at_risk"].__setitem__((0, 0, 0), False))
        with self.assertRaisesRegex(ValueError, "at-risk"):
            load_corpus(self.path)

    def test_full_horizon_lightning_heads_cannot_have_conflicting_labels(self):
        self.alter(lambda d: d["lightning_targets"].__setitem__((0, 0, 0), 1 - d["lightning_targets"][0, 0, 0]))
        with self.assertRaisesRegex(ValueError, "disagree"):
            load_corpus(self.path)

    def test_detected_censored_lightning_onset_cannot_be_a_covered_binary_negative(self):
        def change(data):
            data["lightning_event_bin"][0, 0, 0] = 1
            data["lightning_observed_bins"][0, 0, 0] = 2
            data["lightning_targets"][0, 0, 0] = 0
        self.alter(change)
        with self.assertRaisesRegex(ValueError, "including censored"):
            load_corpus(self.path)

    def test_detected_censored_lightning_onset_can_have_unknown_binary_label(self):
        def change(data):
            data["lightning_event_bin"][0, 0, 0] = 1
            data["lightning_observed_bins"][0, 0, 0] = 2
            data["lightning_targets"][0, 0, 0] = 0
            data["lightning_coverage"][0, 0, 0] = False
        self.alter(change)
        load_corpus(self.path)


@unittest.skipUnless(importlib.util.find_spec("torch"), "Optional PyTorch environment required")
class RegionalHeadTests(unittest.TestCase):
    def test_torch_loss_matches_hand_censoring_loss_and_ignores_unknown_targets(self):
        import torch
        zero = torch.zeros((1, 1, 2, 3), requires_grad=True)
        outputs = {"lightning_logits": torch.zeros((1, 1, 2), requires_grad=True),
                   "rain_onset_logits": zero, "lightning_onset_logits": zero}
        event, observed, coverage = np.array([[[1, 999]]]), np.array([[[3, 999]]]), np.array([[[1, 0]]])
        labels, covered = np.array([[[1, np.nan]]]), np.array([[[1, 0]]])
        result = regional_loss(outputs, lightning_targets=labels, lightning_coverage=covered,
            rain_onset=(event, observed, coverage), lightning_onset=(event, observed, coverage))
        expected = survival_nll(zero.detach().numpy(), event, observed, coverage)
        self.assertAlmostEqual(float(result["rain_onset_nll"].detach()), expected, places=6)
        result["loss"].backward()
        self.assertEqual(float(zero.grad[0, 0, 1].abs().sum()), 0.)
        with self.assertRaisesRegex(ValueError, "No covered"):
            regional_loss(outputs, lightning_targets=labels, lightning_coverage=np.zeros_like(covered),
                rain_onset=(event, observed, np.zeros_like(coverage)), lightning_onset=(event, observed, np.zeros_like(coverage)))

    def test_shared_temporal_model_has_distinct_trainable_heads(self):
        import torch
        torch.set_num_threads(2)
        model = make_regional_model(6, hidden=4, bins=6)
        outputs = model(torch.randn(2, 3, 6, 4, 4))
        self.assertEqual(tuple(outputs["lightning_logits"].shape), (2, 4, 4))
        self.assertEqual(tuple(outputs["rain_onset_logits"].shape), (2, 4, 4, 6))
        self.assertIsNot(model.rain_onset, model.lightning_onset)
        sum(value.square().mean() for value in outputs.values()).backward()
        self.assertTrue(all(parameter.grad is not None for parameter in model.parameters()))

    def test_training_saves_reloads_infers_and_identical_retry_reuses_verified_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = make_fixture(Path(directory) / "fixture.npz")
            first = train_corpus(path, Path(directory) / "runs", steps=3, hidden=4)
            report = json.loads((Path(first["directory"]) / "report.json").read_text())
            self.assertTrue(report["checkpoint_reload_verified"])
            self.assertFalse(report["operational"])
            self.assertEqual(report["scope"], "synthetic_fixture")
            self.assertEqual(len(report["training_history"]), 3)
            self.assertGreater(report["test_covered_counts"]["lightning"], 0)
            corpus = load_corpus(path)
            inputs = dict(values=corpus["values"][-1],
                masks=corpus["masks"][-1], times_utc=corpus["times_utc"][-1], available_at_utc=corpus["available_at_utc"][-1],
                issue_time=str(corpus["issue_utc"][-1]), input_contract=corpus["meta"], phase="active",
                phase_available_at=str(corpus["phase_available_at_utc"][-1]))
            checkpoint_path = Path(first["directory"]) / "checkpoint.pt"
            prediction = predict_history(checkpoint_path, **inputs, rain_at_risk=corpus["rain_at_risk"][-1],
                                         lightning_at_risk=corpus["lightning_at_risk"][-1])
            self.assertFalse(prediction["operational"])
            self.assertEqual(prediction["lightning_probability"].shape, (4, 4))
            np.testing.assert_allclose(prediction["rain_onset"]["event_mass"].sum(-1) + prediction["rain_onset"]["no_event_probability"], 1)
            with self.assertRaises(TypeError):
                predict_history(checkpoint_path, **inputs)
            with self.assertRaisesRegex(ValueError, "eligibility"):
                predict_history(checkpoint_path, **inputs, rain_at_risk=np.ones((1, 1)), lightning_at_risk=np.ones((4, 4)))
            rain_risk, lightning_risk = np.ones((4, 4), bool), np.ones((4, 4), bool)
            rain_risk[0, 0], lightning_risk[0, 1] = False, False
            masked = predict_history(checkpoint_path, **inputs, rain_at_risk=rain_risk, lightning_at_risk=lightning_risk)
            self.assertFalse(masked["rain_onset"]["eligible"][0, 0])
            self.assertTrue(np.isnan(masked["rain_onset"]["event_mass"][0, 0]).all())
            self.assertTrue(np.isnan(masked["lightning_onset"]["event_mass"][0, 1]).all())
            self.assertTrue(np.isfinite(masked["rain_onset"]["event_mass"][0, 1]).all())
            self.assertTrue(np.isfinite(masked["lightning_onset"]["event_mass"][0, 0]).all())
            self.assertTrue(np.isfinite(masked["lightning_probability"]).all())
            second = train_corpus(path, Path(directory) / "runs", steps=3, hidden=4)
            self.assertTrue(second["reused"])
            self.assertEqual(first["id"], second["id"])
            (Path(first["directory"]) / "report.json").write_text("corrupted")
            with self.assertRaisesRegex(ValueError, "integrity"):
                train_corpus(path, Path(directory) / "runs", steps=3, hidden=4)


if __name__ == "__main__":
    unittest.main()

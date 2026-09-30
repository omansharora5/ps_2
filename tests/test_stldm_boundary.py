import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from scripts.run_stldm import REFERENCE_METADATA, download, file_hash, image_scores, partition_reference


class STLDMBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.sequence = np.zeros((1, 25, 1, 32, 32), dtype=np.float32)

    def test_future_images_are_separate_copies_and_cannot_change_past(self):
        self.sequence[:, :5] = .25
        past, future = partition_reference(self.sequence, REFERENCE_METADATA)
        self.sequence[:, 5:] = 1
        updated, _ = partition_reference(self.sequence, REFERENCE_METADATA)
        np.testing.assert_array_equal(past, updated)
        future[:] = .8
        self.assertTrue((past == .25).all())
        self.assertFalse(np.shares_memory(past, self.sequence))

    def test_rejects_wrong_shape_and_channel_contract(self):
        for shape in ((1, 24, 1, 32, 32), (1, 25, 2, 32, 32), (25, 1, 32, 32), (2, 25, 1, 32, 32)):
            with self.assertRaisesRegex(ValueError, "sequence"):
                partition_reference(np.zeros(shape), REFERENCE_METADATA)

    def test_rejects_nonfinite_or_unscaled_pixels(self):
        for value in (np.nan, np.inf, -10, 35):
            self.sequence[0, 0, 0, 0, 0] = value
            with self.assertRaisesRegex(ValueError, "normalized"):
                partition_reference(self.sequence, REFERENCE_METADATA)

    def test_rejects_units_or_scope_relabelling(self):
        for key, value in (("units", "dBZ"), ("scope", "live_lightning"), ("coverage_status", "verified")):
            metadata = copy.deepcopy(REFERENCE_METADATA); metadata[key] = value
            with self.assertRaisesRegex(ValueError, "metadata"):
                partition_reference(self.sequence, metadata)

    def test_reference_metrics_have_shared_finite_support_and_known_values(self):
        truth = np.array([[[[[0., 1., np.nan]]], [[[0., 1., .5]]]]])
        prediction = np.array([[[[[.5, .5, .5]]], [[[.5, .5, .5]]]]])
        last = np.array([[[[[0., 0., .5]]]]])
        result = image_scores(prediction, truth, last)
        self.assertEqual(result["samples"], 5)
        self.assertAlmostEqual(result["stldm_mse"], .2)
        self.assertAlmostEqual(result["persistence_mse"], .4)
        self.assertIn("coverage is unknown", result["scope"])

    def test_cached_checkpoint_hash_mismatch_is_not_silently_downloaded_over(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.safetensors"; path.write_bytes(b"changed")
            before = file_hash(path)
            with self.assertRaisesRegex(ValueError, "pinned"):
                download("https://example.invalid/never-called", path, 100, "0" * 64)
            self.assertEqual(file_hash(path), before)

    def test_cli_failure_leaves_honest_report_and_no_predictions(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = subprocess.run([sys.executable, "scripts/run_stldm.py", "infer", "--checkout", str(base / "missing-source"),
                                     "--output", str(base / "run")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            report = json.loads((base / "run/report.json").read_text())
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["error_type"], "CalledProcessError")
            self.assertFalse((base / "run/predictions.npz").exists())


if __name__ == "__main__":
    unittest.main()

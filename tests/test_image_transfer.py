import contextlib
import copy
from datetime import datetime, timedelta
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np

try:
    import torch
except ImportError:
    torch = None

from scripts.train_images import checkpoint_normalizer, corpus, initialize_model, input_contract, load_episode, make_model, make_smoke, train
from scripts.predict_images import predict, predict_episode, temperature_for


def make_episodes(directory, prefix="base", shift_days=0):
    make_smoke(directory)
    for path in Path(directory).glob("*.npz"):
        with np.load(path, allow_pickle=False) as archive:
            arrays = {key: archive[key] for key in archive.files}
        meta = json.loads(str(arrays["metadata_json"].item()))
        meta["event_id"] = prefix + "-" + meta["event_id"]
        meta["horizon_minutes"] = 30
        times = [datetime.fromisoformat(value) + timedelta(days=shift_days) for value in arrays["times_utc"]]
        arrays["times_utc"] = np.array([value.isoformat() for value in times])
        arrays["available_at_utc"] = np.array([[value.isoformat()] for value in times])
        arrays["target_end_utc"] = np.array([(value + timedelta(minutes=30)).isoformat() for value in times])
        arrays["metadata_json"] = np.array(json.dumps(meta))
        if shift_days:
            arrays["values"] = arrays["values"] * 2 + 17
        np.savez_compressed(path, **arrays)


@unittest.skipIf(torch is None, "Optional image transfer checks require the .venv-ml PyTorch environment")
class ImageTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        make_episodes(cls.root / "episodes")
        cls.args = SimpleNamespace(data=cls.root / "episodes", output=cls.root / "base-run", history=3,
                                   epochs=1, batch_size=4, device="cpu", calibrate=False, initialize_from=None)
        with contextlib.redirect_stdout(io.StringIO()):
            train(cls.args)
        cls.checkpoint = cls.root / "base-run/model.pt"
        cls.original = torch.load(cls.checkpoint, map_location="cpu", weights_only=True)
        cls.episode = load_episode(cls.root / "episodes/episode-0.npz")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_checkpoint_rejects_semantic_mismatches_and_invalid_normalizer(self):
        for field, value in (("channels", ["other_echo"]), ("units", ["dBZ"]),
                             ("grid", {"crs": "EPSG:4326", "shape": [16, 16]}),
                             ("target_definition", "observed rain"), ("horizon_minutes", 60)):
            with self.subTest(field=field):
                artifact = copy.deepcopy(self.original)
                artifact["metadata"][field] = value
                with self.assertRaisesRegex(ValueError, field):
                    checkpoint_normalizer(artifact, self.episode, 3)
        for field, value, message in (("architecture", "other", "architecture"), ("history", 4, "history"),
                                       ("channels", 4, "channels"), ("std", [0.], "normalizer"),
                                       ("mean", [float("nan")], "normalizer")):
            artifact = copy.deepcopy(self.original); artifact[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                checkpoint_normalizer(artifact, self.episode, 3)
        artifact = copy.deepcopy(self.original)
        artifact["input_contract"]["frame_interval_seconds"] = 600
        with self.assertRaisesRegex(ValueError, "cadence"):
            checkpoint_normalizer(artifact, self.episode, 3)

    def test_channel_order_is_part_of_contract(self):
        episode = copy.deepcopy(self.episode)
        episode["values"] = np.repeat(episode["values"], 2, axis=1)
        episode["meta"]["channels"] = ["thermal", "echo"]
        episode["meta"]["units"] = ["K", "dBZ"]
        artifact = copy.deepcopy(self.original)
        artifact.update(channels=4, mean=[0., 0.], std=[1., 1.], input_contract=input_contract(episode))
        artifact["metadata"].update(channels=["echo", "thermal"], units=["K", "dBZ"])
        with self.assertRaisesRegex(ValueError, "channels"):
            checkpoint_normalizer(artifact, episode, 3)

    def test_new_held_out_cannot_reuse_any_prior_split_or_ancestral_exposure(self):
        episodes, _ = corpus(self.root / "episodes")
        artifact = copy.deepcopy(self.original)
        artifact["exposure_event_ids"].append("ancestor-only")
        path = self.root / "with-ancestor.pt"; torch.save(artifact, path)
        for old_id in [ids[0] for ids in self.original["splits"].values()] + ["ancestor-only"]:
            for new_split in ("validation", "calibration", "test"):
                splits = {"train": ["fresh-train"], "validation": ["fresh-validation"],
                          "calibration": ["fresh-calibration"], "test": ["fresh-test"]}
                splits[new_split] = [old_id]
                with self.subTest(old_id=old_id, split=new_split), self.assertRaisesRegex(ValueError, "exposure overlaps"):
                    initialize_model(make_model(2), path, episodes, splits, 3, torch)

    def test_fine_tune_preserves_normalizer_and_records_full_exposure(self):
        new_data = self.root / "fresh-episodes"
        make_episodes(new_data, prefix="new", shift_days=120)
        source = copy.deepcopy(self.original)
        source.update(calibrated=True, calibration_requested=True,
                      calibrator={"method": "regularized_temperature_v1", "fit_status": "fitted",
                                  "temperature": 2., "fit_event_ids": ["source-calibration"]})
        source["splits"]["calibration"] = ["source-calibration"]
        source_path = self.root / "calibrated-initializer.pt"
        torch.save(source, source_path)
        args = copy.copy(self.args)
        args.data, args.output, args.initialize_from = new_data, self.root / "fine-run", source_path
        with contextlib.redirect_stdout(io.StringIO()):
            report = train(args)
        artifact = torch.load(args.output / "model.pt", map_location="cpu", weights_only=True)
        self.assertEqual(artifact["mean"], self.original["mean"])
        self.assertEqual(artifact["std"], self.original["std"])
        self.assertEqual(artifact["initialization"]["checkpoint_sha256"], hashlib.sha256(source_path.read_bytes()).hexdigest())
        self.assertTrue(set(self.original["exposure_event_ids"]) < set(artifact["exposure_event_ids"]))
        self.assertIn("source-calibration", artifact["exposure_event_ids"])
        self.assertIsNone(artifact["calibrator"])
        self.assertFalse(artifact["calibrated"])
        self.assertTrue(any(not torch.equal(value, artifact["state_dict"][key]) for key, value in self.original["state_dict"].items()))
        self.assertEqual(report["initialization"]["normalizer"], "preserved_from_initializer")

    def test_future_frames_targets_coverage_and_late_values_cannot_change_inference(self):
        episode = copy.deepcopy(self.episode)
        episode["available"][1, 0] = episode["times"][2] + 60
        expected = predict_episode(self.original, episode, 2, torch)
        episode["values"][3:] = 1e6
        episode["values"][1] = -1e6
        episode["targets"][:] = 1 - episode["targets"]
        episode["coverage"][:] = False
        actual = predict_episode(self.original, episode, 2, torch)
        np.testing.assert_array_equal(expected["probabilities"], actual["probabilities"])
        self.assertEqual(actual["metadata"]["horizon_minutes"], 30)
        self.assertEqual(actual["metadata"]["valid_until_utc"], "2024-01-01T00:40:00Z")
        self.assertFalse(actual["metadata"]["automatic_alert"])
        self.assertEqual(actual["metadata"]["calibration_status"], "uncalibrated")

    def test_missing_observations_are_unknown_and_all_missing_abstains(self):
        episode = copy.deepcopy(self.episode)
        episode["masks"][:, :, 0, 0] = False
        result = predict_episode(self.original, episode, 2, torch)
        self.assertTrue(np.isnan(result["probabilities"][0, 0]))
        self.assertFalse(result["input_support"][0, 0])
        episode["available"][:] = episode["times"][-1] + 60
        with self.assertRaisesRegex(ValueError, "abstaining"):
            predict_episode(self.original, episode, 2, torch)
        with self.assertRaisesRegex(ValueError, "full history"):
            predict_episode(self.original, self.episode, 0, torch)

    def test_only_independently_fitted_calibrator_can_change_probabilities(self):
        artifact = copy.deepcopy(self.original)
        artifact.update(calibrated=True, calibration_requested=True,
                        calibrator={"method": "regularized_temperature_v1", "fit_status": "fitted",
                                    "temperature": 2., "fit_event_ids": ["fresh-calibration"]})
        artifact["splits"]["calibration"] = ["fresh-calibration"]
        raw = predict_episode(self.original, self.episode, 2, torch)["probabilities"]
        scaled = predict_episode(artifact, self.episode, 2, torch)
        self.assertTrue(np.all(np.abs(scaled["probabilities"] - .5) <= np.abs(raw - .5) + 1e-7))
        self.assertIn("held_out_temperature", scaled["metadata"]["calibration_status"])
        artifact["initialization"] = {"exposure_event_ids": ["fresh-calibration"]}
        with self.assertRaisesRegex(ValueError, "overlap"):
            temperature_for(artifact)
        artifact["initialization"] = None
        artifact["calibrator"]["temperature"] = float("nan")
        with self.assertRaisesRegex(ValueError, "temperature"):
            temperature_for(artifact)

    def test_inference_writes_reproducible_provenance_and_refuses_overwrite(self):
        output = self.root / "prediction.npz"
        with contextlib.redirect_stdout(io.StringIO()):
            result = predict(self.checkpoint, self.root / "episodes/episode-0.npz", 2, output)
        with np.load(output, allow_pickle=False) as archive:
            meta = json.loads(str(archive["metadata_json"].item()))
            self.assertEqual(meta["checkpoint_sha256"], hashlib.sha256(self.checkpoint.read_bytes()).hexdigest())
            np.testing.assert_array_equal(archive["probabilities"], result["probabilities"])
        previous = output.read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            predict(self.checkpoint, self.root / "episodes/episode-0.npz", 2, output)
        self.assertEqual(previous, output.read_bytes())


if __name__ == "__main__":
    unittest.main()

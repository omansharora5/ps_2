import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import numpy as np

from nowcast import data_catalog
from nowcast.image_processing import dense_backward_flow, extrapolate, image_run, preprocess, segment, to_dbz, to_z
from nowcast.numerics import translate
from nowcast.service import app
from scripts.train_images import corpus, examples, load_episode, make_smoke, normalizer


class ImageScienceTests(unittest.TestCase):
    def test_weak_positive_reflectivity_survives_dbz_round_trip(self):
        z = np.array([[0.01, 0.1, 1.]])
        np.testing.assert_allclose(to_z(to_dbz(z)), z)
        np.testing.assert_array_equal(to_z(np.array([-10., -10.]), np.array([True, False])), [0., .1])

    def test_smoothed_weak_echo_is_in_intensity_cohort_not_no_echo(self):
        field = np.full((5, 5), -10.); field[2, 2] = -9
        frames = np.stack([field] * 6)
        y, x = np.mgrid[:5, :5]
        with patch("nowcast.image_processing.load_sample", return_value=(frames, [str(i) for i in range(6)], y, x, {})):
            result = image_run("persistence", "smooth", 10)
        self.assertLess(result["layers"]["forecast"][2][2], -10)
        self.assertEqual(result["metrics"]["selected"]["intensity_samples"], 1)
        self.assertEqual(result["masks"]["no_echo"]["forecast"][2][2], 0)
        self.assertEqual(result["masks"]["intensity_evaluation"][2][2], 1)

    def test_smoothing_averages_linear_reflectivity_and_preserves_unknown(self):
        field = np.array([[10., 30.], [10., 30.]])
        actual = preprocess(field, "smooth")
        np.testing.assert_allclose(actual, 10 * np.log10(505))
        field[0, 0] = np.nan
        self.assertTrue(np.isnan(preprocess(field, "smooth")[0, 0]))

    def test_despeckle_does_not_call_missing_pixels_quiet(self):
        field = np.zeros((8, 8)); field[0, 0] = np.nan; field[2, 2] = 35; field[4:6, 4:6] = 30
        output = preprocess(field, "despeckle")
        self.assertEqual(output[2, 2], -10)
        self.assertTrue(np.isnan(output[0, 0]))
        self.assertEqual(output[4, 4], 30)
        _, objects = segment(output)
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["pixels"], 4)

    def test_dense_backward_flow_direction_and_invalid_border(self):
        y, x = np.mgrid[:32, :32]
        previous = 50 * np.exp(-((x - 14) ** 2 + (y - 14) ** 2) / 22)
        current = translate(previous, 0, 1, fill=0)
        _, u, valid = dense_backward_flow(previous, current)
        self.assertLess(float(u[10:18, 10:18].mean()), 0)
        self.assertFalse(valid[0].any())

    def test_future_truth_never_changes_image_forecast_or_preprocessing(self):
        y, x = np.mgrid[:16, :16]
        field = 45 * np.exp(-((x - 7) ** 2 + (y - 7) ** 2) / 10)
        frames = np.stack([translate(field, 0, i * .25, fill=0) for i in range(6)])
        dates = [f"2018-12-19 10:{10+i*5:02d}:00" for i in range(6)]
        for method in ("persistence", "global_translation", "dense_optical_flow"):
            with patch("nowcast.image_processing.load_sample", return_value=(frames, dates, y, x, {})):
                before = image_run(method, "smooth", 10)
            changed = frames.copy(); changed[2:] = 60
            with patch("nowcast.image_processing.load_sample", return_value=(changed, dates, y, x, {})):
                after = image_run(method, "smooth", 10)
            self.assertEqual(before["layers"]["forecast"], after["layers"]["forecast"])
            self.assertEqual(before["layers"]["processed"], after["layers"]["processed"])
            self.assertEqual(before["metrics"]["selected"]["samples"], before["metrics"]["persistence"]["samples"])
            self.assertEqual(before["metrics"]["selected"]["intensity_samples"], before["metrics"]["persistence"]["intensity_samples"])

    def test_bad_horizon_and_extra_future_frames_rejected(self):
        with self.assertRaises(ValueError): extrapolate(np.zeros((2, 5, 5)), "persistence", "raw", 60)
        with self.assertRaises(ValueError): extrapolate(np.zeros((3, 5, 5)), "persistence", "raw", 5)


class DataApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000))

    def tearDown(self):
        self.client.close()

    def test_catalog_lists_actual_counts_pending_sources_and_normalized_units(self):
        response = self.client.get("/api/data/catalog")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["training_ready"])
        self.assertEqual(sum(c["local_file_count"] for c in data["collections"]), 18)
        self.assertTrue(any(source["status"] == "access_pending" for source in data["sources"]))
        gfs = next(c for c in data["collections"] if c["id"] == "gfs")
        self.assertTrue(gfs["files"][1]["units"])
        self.assertEqual(gfs["files"][1]["timezone"], "UTC")

    def test_file_endpoint_only_serves_manifest_ids(self):
        self.assertEqual(self.client.get("/api/data/files/receipts.sqlite").status_code, 404)
        response = self.client.get("/api/data/files/india--imd_synop_queryables")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_collection_requires_opt_in_loopback_json_and_trusted_origin(self):
        with patch.dict(os.environ, {"VAJRA_ENABLE_COLLECTIONS": "0"}):
            self.assertEqual(self.client.post("/api/data/collections/india", json={}).status_code, 403)
        with patch.dict(os.environ, {"VAJRA_ENABLE_COLLECTIONS": "1"}), patch("nowcast.data_catalog.start_collection", return_value={"id": "fixed", "status": "queued"}) as start:
            self.assertEqual(self.client.post("/api/data/collections/india", json={}, headers={"origin": "https://untrusted.example"}).status_code, 403)
            self.assertEqual(self.client.post("/api/data/collections/india", json={}, headers={"host": "untrusted.example"}).status_code, 403)
            self.assertGreaterEqual(self.client.post("/api/data/collections/india", content="{}", headers={"content-type": "text/plain"}).status_code, 400)
            response = self.client.post("/api/data/collections/india", json={}, headers={"origin": "http://localhost:8081"})
            self.assertEqual(response.status_code, 202)
            start.assert_called_once_with("india")
            with TestClient(app, base_url="http://localhost", client=("192.168.1.8", 50000)) as remote:
                self.assertEqual(remote.post("/api/data/collections/india", json={}).status_code, 403)

    def test_queue_deduplicates_active_job_and_rejects_other_collection(self):
        with patch.dict(data_catalog.JOBS, {}, clear=True), patch.object(data_catalog.EXECUTOR, "submit"):
            first = data_catalog.start_collection("india")
            self.assertEqual(data_catalog.start_collection("india")["id"], first["id"])
            with self.assertRaises(RuntimeError): data_catalog.start_collection("gfs")
            with self.assertRaises(KeyError): data_catalog.start_collection("arbitrary-shell")

    def test_corrupt_and_escaping_manifest_files_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); base = root / "data/government"; base.mkdir(parents=True)
            path = base / "file.json"; path.write_bytes(b"bad")
            entry = {"id": "one", "path": "data/government/file.json", "bytes": 3, "sha256": hashlib.sha256(b"good").hexdigest()}
            with patch.object(data_catalog, "ROOT", root), patch.object(data_catalog, "BASE", base), patch.object(data_catalog, "manifest_entries", return_value=[entry]):
                with self.assertRaises(ValueError): data_catalog.resolve_file("india--one")
                outside = root / "private.txt"; outside.write_text("private")
                with self.assertRaises(FileNotFoundError): data_catalog.safe_path({"path": "private.txt"})

    def test_real_image_api_and_boundary_validation(self):
        response = self.client.post("/api/image-runs", json={"method": "global_translation", "preprocessing": "smooth", "horizon": 10})
        self.assertEqual(response.status_code, 200, response.text[:500])
        result = response.json()
        self.assertEqual(result["mode"], "observed_radar_image")
        self.assertGreater(result["metrics"]["selected"]["samples"], 0)
        self.assertEqual(set(result["layers"]), {"original", "processed", "forecast", "truth", "segments"})
        self.assertEqual(self.client.post("/api/image-runs", json={"horizon": 60}).status_code, 422)
        self.assertEqual(self.client.post("/api/image-runs", json={"method": "fake-neural-model"}).status_code, 422)


class TrainingContractTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(); self.path = Path(self.directory.name)
        make_smoke(self.path)

    def tearDown(self):
        self.directory.cleanup()

    def test_grouped_split_normalization_and_late_inputs(self):
        episodes, splits = corpus(self.path)
        self.assertFalse(set(splits["train"]) & set(splits["test"]))
        mean, std = normalizer(episodes, splits["train"])
        original = mean.copy()
        for episode in episodes:
            if episode["meta"]["event_id"] in splits["test"]:
                episode["values"][:] = 9999
        np.testing.assert_array_equal(normalizer(episodes, splits["train"])[0], original)
        episode = episodes[0]
        episode["available"][0] = episode["times"][-1] + 60
        data = examples([episode], [episode["meta"]["event_id"]], 3, mean, std)
        self.assertTrue((data[0][0][0] == 0).all())

    def test_tiny_corpus_and_ambiguous_timezone_fail(self):
        for path in list(self.path.glob("*.npz"))[1:]: path.unlink()
        with self.assertRaisesRegex(ValueError, "six independent"): corpus(self.path)
        path = next(self.path.glob("*.npz"))
        with np.load(path, allow_pickle=False) as z: data = {k: z[k] for k in z.files}
        data["times_utc"] = np.array(["2024-01-01T00:00:00"] * 8)
        np.savez_compressed(path, **data)
        with self.assertRaisesRegex(ValueError, "UTC"): load_episode(path)

    def test_overlapping_event_windows_fail(self):
        path = self.path / "episode-5.npz"
        with np.load(path, allow_pickle=False) as z: data = {k: z[k] for k in z.files}
        with np.load(self.path / "episode-4.npz", allow_pickle=False) as z:
            for key in ("times_utc", "available_at_utc", "target_end_utc"): data[key] = z[key]
        np.savez_compressed(path, **data)
        with self.assertRaisesRegex(ValueError, "overlap"): corpus(self.path)

    def test_different_cadences_cannot_share_one_model_schema(self):
        path = self.path / "episode-5.npz"
        with np.load(path, allow_pickle=False) as z: data = {k: z[k] for k in z.files}
        start = datetime(2024, 1, 11, tzinfo=timezone.utc)
        times = [start + timedelta(minutes=i * 10) for i in range(8)]
        data["times_utc"] = np.array([t.isoformat() for t in times])
        data["available_at_utc"] = np.array([[t.isoformat()] for t in times])
        data["target_end_utc"] = np.array([(t + timedelta(minutes=10)).isoformat() for t in times])
        np.savez_compressed(path, **data)
        with self.assertRaisesRegex(ValueError, "incompatible"): corpus(self.path)


if __name__ == "__main__":
    unittest.main()

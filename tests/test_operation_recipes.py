from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from nowcast import operation_recipes as recipes
from scripts.train_images import make_smoke


class LocalStore:
    def __init__(self, root, dataset=None):
        self.root = Path(root)
        self.record = dataset
        self.stages = []
        self.submissions = []

    def dataset(self, identifier):
        if self.record is None or identifier != self.record["id"]:
            raise KeyError("Unknown dataset")
        return self.record

    def stage(self, identifier, token, stage):
        self.stages.append(stage)
        return True

    def enqueue(self, kind, identity, parameters, scope):
        self.submissions.append((kind, identity, parameters, scope))
        return {"kind": kind, "identity": identity, "parameters": parameters, "scope": scope}


def job(kind, dataset=None):
    return {"id": "a" * 64, "kind": kind, "attempt_token": "one",
            "dataset_id": dataset["id"] if dataset else None, "identity": recipes.recipe_identity(kind, dataset)}


def rewrite_episode(path, **overrides):
    with np.load(path, allow_pickle=False) as archive:
        values = {name: archive[name] for name in archive.files}
    values.update(overrides)
    np.savez_compressed(path, **values)


class DatasetBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / "incoming"
        self.store = self.base / "store"
        make_smoke(self.source, 8)

    def tearDown(self):
        self.temp.cleanup()

    def freeze(self, **changes):
        arguments = {"name": "Boundary fixture", "series": "fixture-series",
                     "labels_available_at": "2024-02-01T00:00:00+00:00",
                     "coverage_evidence": "Test fixture with explicit complete target masks"}
        arguments.update(changes)
        return recipes.freeze_dataset(self.source, self.store, **arguments)

    def test_freeze_is_repeatable_complete_and_preserves_scope(self):
        first, second = self.freeze(), self.freeze()
        self.assertEqual(first, second)
        self.assertEqual(len(first["id"]), 64)
        self.assertFalse(first["learning_eligible"])
        self.assertEqual(first["scope"], "synthetic_smoke_only")
        self.assertEqual(len(first["event_ids"]), 8)
        self.assertEqual(set(first["splits"]), {"train", "validation", "calibration", "test"})
        self.assertEqual({entry["event_id"] for entry in first["files"]}, set(first["event_ids"]))
        self.assertGreater(first["decoded_bytes"], 0)
        self.assertLess(first["window_bytes"], recipes.MAX_WINDOW_BYTES)
        frozen = recipes.verify_dataset(first, self.store)
        self.assertEqual(frozen.parent.name, first["id"])
        self.assertFalse(list((self.store / "datasets").glob(".staging-*")))
        original = self.source / "episode-0.npz"
        original.write_bytes(b"later external changes")
        self.assertEqual(recipes.verify_dataset(first, self.store), frozen)

    def test_tampered_copy_manifest_and_incomplete_publication_fail(self):
        record = self.freeze()
        path = recipes.verify_dataset(record, self.store) / "episode-0.npz"
        path.write_bytes(b"corrupt")
        with self.assertRaises((ValueError, recipes.zipfile.BadZipFile)):
            recipes.verify_dataset(record, self.store)
        changed = dict(record, scope="observed_research")
        with self.assertRaisesRegex(ValueError, "identity"):
            recipes.verify_dataset(changed, self.store)
        with self.assertRaises((ValueError, recipes.zipfile.BadZipFile)):
            self.freeze()

    def test_budgets_are_checked_before_numpy_load(self):
        for constant, value, expected in (("MAX_COMPRESSED_BYTES", 1, "compressed"),
                                          ("MAX_DECODED_BYTES", 1, "decoded"),
                                          ("MAX_WINDOW_BYTES", 1, "window")):
            with self.subTest(constant=constant), patch.object(recipes, constant, value), patch.object(np, "load", side_effect=AssertionError("Arrays loaded too early")):
                with self.assertRaisesRegex(ValueError, expected):
                    self.freeze()
        self.assertFalse((self.store / "datasets").exists())

    def test_object_arrays_and_episode_count_rejected_before_load(self):
        rewrite_episode(self.source / "episode-0.npz", values=np.array([{"bad": 1}], dtype=object))
        with patch.object(np, "load", side_effect=AssertionError("Objects reached array loading")):
            with self.assertRaisesRegex(ValueError, "Object arrays"):
                self.freeze()
        with patch.object(recipes, "MAX_EPISODES", 7):
            with self.assertRaisesRegex(ValueError, "episode files"):
                self.freeze()

    def test_changed_source_during_copy_never_publishes(self):
        original = shutil.copyfile
        changed = False

        def copy_then_change(source, destination):
            nonlocal changed
            result = original(source, destination)
            if not changed:
                Path(source).write_bytes(Path(source).read_bytes() + b"changed")
                changed = True
            return result

        with patch.object(recipes.shutil, "copyfile", side_effect=copy_then_change):
            with self.assertRaisesRegex(ValueError, "changed during"):
                self.freeze()
        self.assertEqual(list((self.store / "datasets").iterdir()), [])

    def test_maturity_timezone_and_source_overlap_rejected(self):
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        for stamp in (future, "2024-02-01T00:00:00", "2024-01-01T00:00:00+00:00"):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                self.freeze(labels_available_at=stamp)
        with self.assertRaisesRegex(ValueError, "separate"):
            recipes.freeze_dataset(self.source, self.source / "nested", name="bad", series="bad",
                                   labels_available_at="2024-02-01T00:00:00+00:00", coverage_evidence="fixture")

    def test_observed_eligibility_requires_recorded_availability_and_coverage(self):
        for path in self.source.glob("*.npz"):
            with np.load(path, allow_pickle=False) as archive:
                metadata = json.loads(str(archive["metadata_json"].item()))
            metadata.update(scope="observed_research", availability_mode="recorded",
                            provenance="Eligibility unit-test fixture; not an observational claim")
            rewrite_episode(path, metadata_json=np.array(json.dumps(metadata)))
        record = self.freeze()
        self.assertTrue(record["learning_eligible"])
        self.assertEqual(record["readiness_reasons"], [])
        with np.load(self.source / "episode-0.npz", allow_pickle=False) as archive:
            coverage = np.zeros_like(archive["coverage"])
        rewrite_episode(self.source / "episode-0.npz", coverage=coverage)
        with self.assertRaisesRegex(ValueError, "covered labels"):
            self.freeze()


class ScientificRecipeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = LocalStore(Path(self.temp.name) / "store")

    def tearDown(self):
        self.temp.cleanup()

    def test_submission_uses_only_registered_kind_dataset_and_recipe(self):
        result = recipes.submit_recipe(self.store, "starter_audit")
        self.assertEqual(result["parameters"], {})
        self.assertIn("provider_manifests", result["identity"])
        for kind, identifier in (("shell", None), ("train_candidate", None), ("radar_replay", "a" * 64)):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                recipes.submit_recipe(self.store, kind, identifier)

    def test_dataset_and_result_round_trip_through_real_sqlite_store(self):
        from nowcast.operation_store import OperationsStore
        store = OperationsStore(self.store.root)
        dataset = recipes.prepare_demo_dataset(store.root)
        self.assertEqual(store.register_dataset(dataset), dataset)
        training = recipes.submit_recipe(store, "train_candidate", dataset["id"])
        self.assertEqual(training["dataset_id"], dataset["id"])
        self.assertEqual(recipes.submit_recipe(store, "train_candidate", dataset["id"])["id"], training["id"])
        store.cancel(training["id"])
        audit = recipes.submit_recipe(store, "starter_audit")
        claimed = store.claim()
        self.assertEqual(claimed["id"], audit["id"])
        result = recipes.execute_recipe(claimed, store.root / "attempts" / claimed["id"] / claimed["attempt_token"], store)
        self.assertTrue(store.finish(claimed["id"], claimed["attempt_token"], result))
        reopened = OperationsStore(store.root)
        self.assertEqual(reopened.get(audit["id"])["summary"]["verified"], 18)
        self.assertEqual(recipes.submit_recipe(reopened, "starter_audit")["id"], audit["id"])

    def test_actual_starter_audit_checks_bytes_not_training_readiness(self):
        result = recipes.execute_recipe(job("starter_audit"), self.store.root / "attempt", self.store)
        self.assertEqual(result["summary"]["checked"], 18)
        self.assertEqual(result["summary"]["verified"], 18)
        self.assertEqual(result["summary"]["problems"], 0)
        self.assertFalse(result["summary"]["training_ready"])
        self.assertFalse(result["summary"]["public_dispatch_eligible"])
        artifact = result["artifacts"][0]
        self.assertEqual(hashlib.sha256((self.store.root / artifact["relative_path"]).read_bytes()).hexdigest(), artifact["sha256"])

    def test_audit_records_same_size_corruption_as_failed_integrity(self):
        from nowcast.operation_store import OperationsStore
        base = Path(self.temp.name) / "government"
        base.mkdir()
        (base / "data.json").write_bytes(b"bad!")
        entry = {"id": "one", "path": "data.json", "bytes": 4, "sha256": hashlib.sha256(b"good").hexdigest()}
        with patch.object(recipes.data_catalog, "BASE", base), patch.object(recipes.data_catalog, "ROOT", base), \
             patch.object(recipes.data_catalog, "COLLECTIONS", {"fixture": ("Fixture", "unused.py")}), \
             patch.object(recipes.data_catalog, "manifest_entries", return_value=[entry]):
            store = OperationsStore(self.store.root)
            before = recipes.submit_recipe(store, "starter_audit")
            claimed = store.claim()
            result = recipes.execute_recipe(claimed, self.store.root / "audit-corrupt", store)
            self.assertTrue(store.finish(claimed["id"], claimed["attempt_token"], result))
            (base / "data.json").write_bytes(b"good")
            repaired = recipes.submit_recipe(store, "starter_audit")
            self.assertNotEqual(before["id"], repaired["id"])
            self.assertEqual(repaired["status"], "queued")
            (base / "data.json").unlink()
            missing = recipes.submit_recipe(store, "starter_audit")
            self.assertNotIn(missing["id"], (before["id"], repaired["id"]))
        self.assertEqual(result["summary"]["problems"], 1)
        self.assertEqual(result["summary"]["verified"], 0)

    def test_actual_observed_replay_keeps_scope_and_compact_evidence(self):
        result = recipes.execute_recipe(job("radar_replay"), self.store.root / "replay", self.store)
        self.assertEqual(result["summary"]["mode"], "observed_radar_replay")
        self.assertIn("French", result["summary"]["scope"])
        self.assertIn("persistence", result["summary"]["metrics"])
        artifact = result["artifacts"][0]
        evidence = json.loads((self.store.root / artifact["relative_path"]).read_text())
        self.assertNotIn("layers", evidence)
        self.assertNotIn("masks", evidence)
        self.assertGreater(evidence["metrics"]["selected"]["samples"], 0)

    def test_replay_rechecks_files_even_after_previous_cached_load(self):
        inputs = Path(self.temp.name) / "changed-radar"
        inputs.mkdir()
        for name in recipes.real_data.EXPECTED:
            (inputs / name).write_bytes(b"changed")
        with patch.object(recipes.real_data, "DATA", inputs), patch.object(recipes.image_processing, "image_run") as run:
            with self.assertRaisesRegex(ValueError, "pinned integrity"):
                recipes.execute_recipe(job("radar_replay"), self.store.root / "tampered", self.store)
            run.assert_not_called()

    def test_attempt_reuse_escape_recipe_change_and_cancel_are_rejected(self):
        existing = self.store.root / "old"
        existing.mkdir(parents=True)
        (existing / "partial.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "fresh"):
            recipes.execute_recipe(job("starter_audit"), existing, self.store)
        with self.assertRaisesRegex(ValueError, "registered root"):
            recipes.execute_recipe(job("starter_audit"), Path(self.temp.name) / "outside", self.store)
        changed = job("starter_audit")
        changed["identity"]["recipe_version"] = "changed"
        with self.assertRaisesRegex(ValueError, "identity changed"):
            recipes.execute_recipe(changed, self.store.root / "changed", self.store)
        with patch.object(self.store, "stage", return_value=False), patch.object(recipes.image_processing, "image_run") as run:
            with self.assertRaisesRegex(ValueError, "no longer owned"):
                recipes.execute_recipe(job("radar_replay"), self.store.root / "cancelled", self.store)
            run.assert_not_called()

    def test_worker_with_stale_imported_source_cannot_run_a_new_disk_identity(self):
        with patch.dict(recipes._IMPORTED_SOURCE_HASHES, {"nowcast/operation_recipes.py": "0" * 64}):
            with self.assertRaisesRegex(ValueError, "restart the research worker"):
                recipes.execute_recipe(job("starter_audit"), self.store.root / "stale-import", self.store)

    def test_training_rechecks_source_and_environment_before_result_publication(self):
        dataset = recipes.prepare_demo_dataset(self.store.root)
        self.store.record = dataset
        expected = recipes.recipe_identity("train_candidate", dataset)
        report = {"test": {"brier": .2, "training_climatology_brier": .15},
                  "test_calibrated": {"brier": .22}, "probability_verification": {"event_count": 2},
                  "checkpoint_sha256": hashlib.sha256(b"test checkpoint").hexdigest(),
                  "split_hashes": dataset["split_hashes"]}

        def bounded_fake_fit(arguments):
            output = Path(arguments.output)
            (output / "model.pt").write_bytes(b"test checkpoint")
            (output / "report.json").write_text(json.dumps(report))
            (output / "calibration.json").write_text("{}")
            return report

        evaluation = {key: report[key] for key in ("test", "test_calibrated", "probability_verification")}
        for changed_part in ("source_hashes", "packages"):
            changed = deepcopy(expected)
            field = "scripts/train_images.py" if changed_part == "source_hashes" else "torch"
            changed[changed_part][field] = "changed-while-fitting"
            submitted = job("train_candidate", dataset)
            with self.subTest(part=changed_part), \
                 patch.object(recipes, "recipe_identity", side_effect=[expected, changed]), \
                 patch.object(recipes.importlib.metadata, "version", side_effect=lambda name: expected["packages"][name]), \
                 patch.object(recipes.train_images, "train", side_effect=bounded_fake_fit), \
                 patch.object(recipes.train_images, "evaluate", return_value=evaluation):
                with self.assertRaisesRegex(ValueError, "changed during training"):
                    recipes.execute_recipe(submitted, self.store.root / changed_part, self.store)
            self.assertEqual(self.store.stages[-1], "verifying_result_artifacts")

    @unittest.skipUnless(importlib.util.find_spec("torch"), "Optional training integration requires .venv-ml")
    def test_actual_convlstm_candidate_and_frozen_evaluation(self):
        dataset = recipes.prepare_demo_dataset(self.store.root)
        self.store.record = dataset
        self.assertEqual(dataset, recipes.prepare_demo_dataset(self.store.root))
        with redirect_stdout(io.StringIO()):
            result = recipes.execute_recipe(job("train_candidate", dataset), self.store.root / "train", self.store)
        summary = result["summary"]
        self.assertEqual(summary["scope"], "synthetic_smoke_only")
        self.assertEqual(summary["test_event_count"], 2)
        self.assertTrue(0 <= summary["raw_brier"] <= 1)
        self.assertTrue(0 <= summary["calibrated_brier"] <= 1)
        self.assertTrue(0 <= summary["baseline_brier"] <= 1)
        self.assertIn(summary["recommendation"], ("retain_baseline", "research_review_only"))
        self.assertFalse(summary["promoted"])
        self.assertFalse(summary["public_dispatch_eligible"])
        self.assertEqual({item["name"] for item in result["artifacts"]},
                         {"model.pt", "report.json", "calibration.json", "frozen-evaluation.json"})
        for item in result["artifacts"]:
            path = self.store.root / item["relative_path"]
            self.assertEqual(recipes._file_hash(path), item["sha256"])
            self.assertEqual(path.stat().st_size, item["bytes"])


if __name__ == "__main__":
    unittest.main()

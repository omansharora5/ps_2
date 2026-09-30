import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from nowcast.public_verification import build_scorecard, prepare_benchmark, publish_scorecard, read_benchmark, read_scorecard


HASH = "a" * 64


def case(index=1, probability=.8, observed=1):
    issue = f"2026-09-{index:02d}T12:00:00Z"
    end = f"2026-09-{index:02d}T12:30:00Z"
    return {"case_id": f"case-{index}", "event_id": f"storm-{index}", "hazard": "rain",
            "label_definition": "rain-any-30min-v1", "geometry_id": "block-example", "geometry_sha256": HASH,
            "issued_at": issue, "target_start": issue, "target_end": end, "forecast_archived_at": issue,
            "forecast_record_sha256": HASH, "probability": probability, "data_mode": "observed",
            "truth": {"observed": observed, "source_kind": "instrument", "source_id": "fixture-gauge",
                      "record_sha256": HASH, "coverage_complete": True, "available_at": end,
                      "target_start": issue, "target_end": end, "geometry_sha256": HASH,
                      "label_definition": "rain-any-30min-v1"}}


def config(cases=None):
    return {"month": "2026-09", "publication_cutoff": "2026-10-01T00:00:00Z", "model_id": "fixture-model",
            "hazard": "rain", "label_definition": "rain-any-30min-v1", "threshold": .5,
            "lead_time_seconds": 0, "target_duration_seconds": 1800,
            "training_climatology": .2, "train_event_ids": ["train-storm"], "validation_event_ids": ["validation-storm"],
            "calibration_event_ids": ["cal-storm"],
            "cases": cases if cases is not None else [case()]}


def comparator(source, prediction=1):
    keys = ("case_id", "event_id", "hazard", "label_definition", "geometry_id", "geometry_sha256", "issued_at", "target_start", "target_end")
    return {**{key: source[key] for key in keys}, "source_id": "fixture-archived-bulletin", "archive_sha256": HASH,
            "archived_at": source["issued_at"], "prediction": prediction}


class ScorecardTests(unittest.TestCase):
    def test_known_counts_probabilities_and_event_bootstrap(self):
        result = build_scorecard(config([case(1, .8, 1), case(2, .7, 0), case(3, .1, 1), case(4, .2, 0)]))
        metrics = result["metrics"]
        self.assertEqual((metrics["hits"], metrics["misses"], metrics["false_alarms"], metrics["correct_negatives"]), (1, 1, 1, 1))
        self.assertAlmostEqual(metrics["pod"], .5)
        self.assertAlmostEqual(metrics["far"], .5)
        self.assertAlmostEqual(metrics["csi"], 1 / 3)
        self.assertAlmostEqual(metrics["brier"], .345)
        self.assertEqual(sum(b["count"] for b in metrics["reliability"]), 4)
        self.assertEqual(result["event_bootstrap"]["status"], "available")

    def test_undefined_counts_are_null(self):
        result = build_scorecard(config([case(1, 0., 0)]))
        for key in ("pod", "far", "csi"):
            self.assertIsNone(result["metrics"][key])
        self.assertEqual(result["metrics"]["brier"], 0.)
        self.assertEqual(result["event_bootstrap"]["status"], "unavailable")

    def test_coverage_synthetic_crowd_and_maturity_are_excluded(self):
        rows = [case(i) for i in range(1, 6)]
        rows[0]["truth"]["coverage_complete"] = False
        rows[1]["data_mode"] = "synthetic"
        rows[2]["truth"]["source_kind"] = "reviewed_crowd"
        rows[3]["truth"]["available_at"] = "2026-10-02T00:00:00Z"
        rows[4]["truth"]["geometry_sha256"] = "b" * 64
        result = build_scorecard(config(rows))
        self.assertEqual(result["admitted_case_count"], 0)
        self.assertEqual(sum(result["excluded"].values()), 5)
        self.assertEqual(result["status"], "unavailable")

    def test_leakage_duplicates_bad_horizon_and_nonfinite_fail(self):
        for change in (lambda c: c["cases"][0].update(event_id="train-storm"),
                       lambda c: c["cases"].append(copy.deepcopy(c["cases"][0])),
                       lambda c: c.update(target_duration_seconds=3600),
                       lambda c: c["cases"][0].update(probability=float("nan"))):
            data = config()
            change(data)
            with self.assertRaises(ValueError):
                build_scorecard(data)

    def test_late_forecast_is_not_hindsight_success(self):
        row = case()
        row["forecast_archived_at"] = "2026-09-01T12:01:00Z"
        self.assertEqual(build_scorecard(config([row]))["excluded"], {"forecast_not_archived_by_issue": 1})

    def test_renaming_case_or_geometry_cannot_duplicate_physical_case(self):
        original = case()
        duplicate = copy.deepcopy(original)
        duplicate["case_id"] = "renamed-case"
        duplicate["geometry_id"] = "same-polygon-another-name"
        duplicate["target_start"] = duplicate["target_start"].replace("Z", "+00:00")
        duplicate["target_end"] = duplicate["target_end"].replace("Z", "+00:00")
        with self.assertRaisesRegex(ValueError, "Duplicate physical evaluation case"):
            build_scorecard(config([original, duplicate]))

    def test_validation_exposure_is_not_an_untouched_test_event(self):
        row = case()
        row["event_id"] = "validation-storm"
        with self.assertRaisesRegex(ValueError, "model-selection validation"):
            build_scorecard(config([row]))
        data = config()
        data["validation_event_ids"] = ["train-storm"]
        with self.assertRaisesRegex(ValueError, "events overlap"):
            build_scorecard(data)

    def test_future_phase_is_unknown(self):
        row = case()
        row["monsoon_phase"] = {"value": "active", "source_id": "phase-index", "available_at": "2026-09-02T00:00:00Z"}
        row["season"] = {"value": "monsoon", "source_id": "calendar-v1", "available_at": "2026-01-01T00:00:00Z"}
        result = build_scorecard(config([row]))
        self.assertEqual(set(result["strata"]["monsoon_phase"]), {"unknown"})
        self.assertEqual(set(result["strata"]["season"]), {"monsoon"})

    def test_comparator_matches_exact_target_and_issue_deadline(self):
        rows = [case(i, .8, 1) for i in range(1, 4)]
        comparisons = [comparator(r) for r in rows]
        comparisons[1]["geometry_sha256"] = "b" * 64
        comparisons[2]["archived_at"] = "2026-09-03T12:01:00Z"
        data = config(rows)
        data["comparator"] = {"name": "IMD test fixture only", "kind": "categorical", "cases": comparisons}
        comparison = build_scorecard(data)["comparison"]
        self.assertEqual(comparison["matched_cases"], 1)
        self.assertEqual(comparison["model"]["case_count"], 1)
        self.assertEqual(comparison["comparator"]["case_count"], 1)
        self.assertNotIn("brier", comparison["comparator"])
        self.assertNotIn("reliability", comparison["comparator"])
        self.assertEqual(comparison["excluded"], {"incompatible_target": 1, "unavailable_by_issue_deadline": 1})

    def test_publication_is_immutable_idempotent_and_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(read_scorecard(root, "2026-09")["status"], "unavailable")
            first = publish_scorecard(root, config())
            self.assertEqual(first, publish_scorecard(root, config()))
            changed = config([case(1, .3, 1)])
            with self.assertRaises(ValueError):
                publish_scorecard(root, changed)
            publish_scorecard(root, changed, revision=2)
            self.assertEqual(read_scorecard(root, "2026-09")["revision"], 2)
            path = root / "2026-09/r0002.json"
            envelope = json.loads(path.read_text())
            envelope["scorecard"]["metrics"]["brier"] = 0
            path.write_text(json.dumps(envelope))
            with self.assertRaises(ValueError):
                read_scorecard(root, "2026-09")

    def test_cli_publishes_to_explicit_temporary_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fixture-config.json"
            source.write_text(json.dumps(config()), encoding="utf-8")
            result = subprocess.run([sys.executable, "scripts/publish_scorecard.py", str(source), "--root", str(root / "published")],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(read_scorecard(root / "published", "2026-09")["admitted_case_count"], 1)


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        artifacts = []
        for index, split in enumerate(("train", "calibration", "test"), 1):
            body = f"Unit-test fixture {split}".encode()
            (self.root / f"{split}.bin").write_bytes(body)
            issue = f"2026-09-{index:02d}T12:00:00Z"
            end = f"2026-09-{index:02d}T12:30:00Z"
            artifacts.append({"path": f"{split}.bin", "sha256": hashlib.sha256(body).hexdigest(),
                              "event_id": f"storm-{index}", "split": split, "data_mode": "observed", "source_id": "fixture",
                              "input_start": f"2026-09-{index:02d}T11:00:00Z", "input_end": issue,
                              "input_available_at": issue, "issued_at": issue, "target_start": issue, "target_end": end,
                              "truth_available_at": end, "target_duration_seconds": 1800, "label_coverage_complete": True,
                              "label_definition": "fixture-rain-v1", "geometry_sha256": HASH,
                              "recipe": "Unit-test fixture; not observational evidence", "privacy_review": "approved",
                              "redistribution": {"allowed": True, "license": "fixture", "evidence": "fixture-permission"}})
        self.config = {"benchmark_id": "unit-test-fixture", "frozen_at": "2026-10-01T00:00:00Z", "artifacts": artifacts}

    def test_metadata_only_and_rights_gates(self):
        manifest = prepare_benchmark(self.config, self.root)
        self.assertTrue(manifest["release_ready"])
        self.assertEqual(manifest["raw_files_exported"], 0)
        self.assertNotIn("path", manifest["artifacts"][0])
        self.config["artifacts"][0].pop("redistribution")
        self.config["artifacts"][1]["privacy_review"] = "pending"
        manifest = prepare_benchmark(self.config, self.root)
        self.assertFalse(manifest["release_ready"])
        self.assertEqual(set(manifest["release_blockers"]), {"missing_per_file_redistribution_permission", "privacy_review_incomplete"})

    def test_rejects_corruption_synthetic_leakage_and_incomplete_labels(self):
        variants = (
            lambda c: c["artifacts"][0].update(sha256="b" * 64),
            lambda c: c["artifacts"][0].update(data_mode="synthetic"),
            lambda c: c["artifacts"][1].update(event_id="storm-1"),
            lambda c: c["artifacts"][0].update(input_available_at="2026-09-01T12:01:00Z"),
            lambda c: c["artifacts"][0].update(label_coverage_complete=False),
            lambda c: c["artifacts"][0].update(target_duration_seconds=600),
            lambda c: c["artifacts"][1].update(input_start="2026-09-01T12:00:00Z"),
        )
        for change in variants:
            data = copy.deepcopy(self.config)
            change(data)
            with self.assertRaises(ValueError):
                prepare_benchmark(data, self.root)

    def test_manifest_integrity_and_append_only_output(self):
        output = self.root / "benchmark.json"
        self.assertFalse(read_benchmark(output)["raw_release_allowed"])
        prepare_benchmark(self.config, self.root, output)
        prepare_benchmark(self.config, self.root, output)
        self.assertTrue(read_benchmark(output)["raw_release_allowed"])
        changed = copy.deepcopy(self.config)
        changed["benchmark_id"] = "new-version"
        with self.assertRaises(ValueError):
            prepare_benchmark(changed, self.root, output)
        envelope = json.loads(output.read_text())
        envelope["benchmark"]["event_count"] = 999
        output.write_text(json.dumps(envelope))
        with self.assertRaises(ValueError):
            read_benchmark(output)

    def test_rejects_path_escape(self):
        self.config["artifacts"][0]["path"] = str(self.root / "train.bin")
        with self.assertRaises(ValueError):
            prepare_benchmark(self.config, self.root)

    def test_same_episode_content_cannot_cross_splits(self):
        body = (self.root / "train.bin").read_bytes()
        (self.root / "test.bin").write_bytes(body)
        self.config["artifacts"][2]["sha256"] = hashlib.sha256(body).hexdigest()
        with self.assertRaises(ValueError):
            prepare_benchmark(self.config, self.root)

    def test_validation_partition_is_supported_without_replacing_calibration(self):
        row = copy.deepcopy(self.config["artifacts"][0])
        body = b"Unit-test fixture validation"
        (self.root / "validation.bin").write_bytes(body)
        row.update(path="validation.bin", sha256=hashlib.sha256(body).hexdigest(), split="validation", event_id="validation-storm")
        for key in ("input_start", "input_end", "input_available_at", "issued_at", "target_start", "target_end", "truth_available_at"):
            row[key] = row[key].replace("T11:", "T16:").replace("T12:", "T17:")
        self.config["artifacts"].append(row)
        manifest = prepare_benchmark(self.config, self.root)
        self.assertTrue(manifest["release_ready"])
        self.assertEqual(manifest["split_event_counts"], {"train": 1, "validation": 1, "calibration": 1, "test": 1})
        self.config["artifacts"] = [r for r in self.config["artifacts"] if r["split"] != "calibration"]
        self.assertIn("incomplete_train_calibration_test_splits", prepare_benchmark(self.config, self.root)["release_blockers"])

    def test_cli_prepares_actual_local_files_without_exporting_them(self):
        source = self.root / "fixture-config.json"
        source.write_text(json.dumps(self.config), encoding="utf-8")
        output = self.root / "export/benchmark.json"
        result = subprocess.run([sys.executable, "scripts/prepare_benchmark.py", str(source), "--base-dir", str(self.root),
                                 "--output", str(output)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(read_benchmark(output)["raw_files_exported"], 0)
        self.assertEqual([p.name for p in output.parent.iterdir()], ["benchmark.json"])


if __name__ == "__main__":
    unittest.main()

"""Registered, bounded scientific work and immutable research datasets.

The worker owns process lifetime and durable transitions. This module never starts
a subprocess, selects an arbitrary command, promotes a model, or sends an alert.
"""

from argparse import Namespace
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
from uuid import uuid4
import zipfile

import numpy as np

from . import data_catalog, image_processing, real_data
from scripts import train_images


ROOT = Path(__file__).resolve().parents[1]
MAX_EPISODES = 32
MAX_COMPRESSED_BYTES = 64 * 1024 * 1024
MAX_DECODED_BYTES = 64 * 1024 * 1024
MAX_WINDOW_BYTES = 128 * 1024 * 1024
HISTORY = 3
RECIPE_VERSION = "bounded-research-recipes-v1"
KINDS = {"starter_audit", "radar_replay", "train_candidate"}
EPISODE_ARRAYS = {"values", "masks", "times_utc", "available_at_utc", "targets",
                  "coverage", "target_end_utc", "metadata_json"}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _file_hash(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


_IMPORTED_SOURCE_HASHES = {name: _file_hash(ROOT / name) for name in (
    "nowcast/operation_recipes.py", "nowcast/data_catalog.py", "nowcast/image_processing.py",
    "nowcast/real_data.py", "nowcast/numerics.py", "nowcast/verification.py",
    "scripts/train_images.py", "nowcast/probability_evaluation.py")}


def _now():
    return datetime.now(timezone.utc)


def _utc(value):
    stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
        raise ValueError("Dataset evidence timestamps must explicitly identify UTC")
    return stamp


def _under(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Research path must stay within its registered root")
    return path


def _text(value, label, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be nonempty text of at most {maximum} characters")
    return value.strip()


def _preflight(directory):
    """Inspect compressed sizes and NPY headers before allocating dataset arrays."""
    paths = sorted(directory.glob("*.npz"))
    if not 8 <= len(paths) <= MAX_EPISODES:
        raise ValueError(f"A calibrated dataset requires 8 to {MAX_EPISODES} episode files")
    if sum(path.stat().st_size for path in paths) > MAX_COMPRESSED_BYTES:
        raise ValueError("Dataset exceeds the 64 MiB compressed budget")
    decoded, windows = 0, 0
    for path in paths:
        if path.is_symlink() or not path.is_file() or path.resolve().parent != directory.resolve():
            raise ValueError("Dataset files must be direct regular files, not links")
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [item.filename for item in entries]
            if len(names) != len(set(names)) or set(names) != {key + ".npy" for key in EPISODE_ARRAYS}:
                raise ValueError("Episode archive must contain exactly the registered NPY arrays")
            decoded += sum(item.file_size for item in entries)
            if decoded > MAX_DECODED_BYTES:
                raise ValueError("Dataset exceeds the 64 MiB decoded budget")
            shapes = {}
            for item in entries:
                with archive.open(item) as member:
                    version = np.lib.format.read_magic(member)
                    if version == (1, 0):
                        shape, _, dtype = np.lib.format.read_array_header_1_0(member)
                    elif version == (2, 0):
                        shape, _, dtype = np.lib.format.read_array_header_2_0(member)
                    else:
                        raise ValueError("Unsupported NPY header version")
                    if dtype.hasobject or len(shape) > 4 or any(not isinstance(n, int) or n < 0 for n in shape):
                        raise ValueError("Object arrays or unbounded array dimensions are not admitted")
                    payload = math.prod(shape) * dtype.itemsize
                    if payload > MAX_DECODED_BYTES or member.tell() + payload != item.file_size:
                        raise ValueError("NPY shape does not match its bounded payload")
                    shapes[item.filename[:-4]] = shape
            shape = shapes["values"]
            if len(shape) != 4:
                raise ValueError("Episode values need [time, channel, height, width]")
            steps, channels, height, width = shape
            if not (HISTORY <= steps <= 256 and 1 <= channels <= 16 and 1 <= height <= 128 and 1 <= width <= 128):
                raise ValueError("Episode shape exceeds the bounded training recipe")
            # examples() materializes float32 values plus float32 input masks,
            # float32 targets and boolean target coverage for every causal window.
            windows += (steps - HISTORY + 1) * height * width * (HISTORY * channels * 2 * 4 + 4 + 1)
            if windows > MAX_WINDOW_BYTES:
                raise ValueError("Dataset exceeds the 128 MiB materialized-window budget")
    return paths, decoded, windows


def _record_identity(record):
    return {key: value for key, value in record.items() if key not in ("id", "created_at")}


def freeze_dataset(source: Path, store_root: Path, *, name: str, series: str,
                   labels_available_at: str, coverage_evidence: str):
    """Copy bounded local episodes, validate a complete snapshot, then publish it.

    This is a local administrative function. HTTP callers supply registered IDs,
    never this source path. A partial staging directory is never a dataset.
    """
    source, store_root = Path(source), Path(store_root).resolve()
    if source.is_symlink() or getattr(source, "is_junction", lambda: False)():
        raise ValueError("Dataset source must not be a directory link")
    source = source.resolve(strict=True)
    if not source.is_dir() or source == store_root or source.is_relative_to(store_root) or store_root.is_relative_to(source):
        raise ValueError("Dataset source must be a separate regular directory")
    name, series = _text(name, "Dataset name", 120), _text(series, "Learning series", 120)
    evidence = _text(coverage_evidence, "Coverage evidence", 4096)
    available = _utc(labels_available_at)
    if available > _now():
        raise ValueError("Declared labels have not yet arrived; future receipt times are not evidence")
    paths, _, _ = _preflight(source)
    source_hashes = {path.name: _file_hash(path) for path in paths}
    datasets = _under(store_root, store_root / "datasets")
    datasets.mkdir(parents=True, exist_ok=True)
    staging = _under(datasets, datasets / (".staging-" + uuid4().hex))
    staging.mkdir()
    try:
        episodes_path = staging / "episodes"
        episodes_path.mkdir()
        for path in paths:
            shutil.copyfile(path, episodes_path / path.name)
            if _file_hash(path) != source_hashes[path.name] or _file_hash(episodes_path / path.name) != source_hashes[path.name]:
                raise ValueError("Dataset source changed during freezing")
        if {path.name for path in source.glob("*.npz")} != set(source_hashes):
            raise ValueError("Dataset file membership changed during freezing")
        copied, decoded, windows = _preflight(episodes_path)
        episodes, splits = train_images.corpus(episodes_path, HISTORY, calibrate=True)
        manifest = train_images.split_hashes(episodes, splits)
        if manifest["files"] != source_hashes:
            raise ValueError("Validated episode bytes differ from the copied snapshot")
        max_end = datetime.fromtimestamp(max(float(e["ends"].max()) for e in episodes), timezone.utc)
        if max_end > available:
            raise ValueError("Declared truth arrived before one or more future target windows ended")
        if any(not episode["coverage"].any() for episode in episodes):
            raise ValueError("Each admitted episode needs declared covered labels")
        # Validate causal training support and covered examples in each split,
        # without constructing the materialized windows a second time here.
        train_images.normalizer(episodes, splits["train"], HISTORY)
        for split, event_ids in splits.items():
            if not any(e["meta"]["event_id"] in event_ids and
                       any(e["coverage"][i].any() and train_images.causal_input_mask(e, i, HISTORY).any()
                           for i in range(HISTORY - 1, len(e["times"]))) for e in episodes):
                raise ValueError(f"The {split} split has no covered causal examples")
        metadata = episodes[0]["meta"]
        eligible = metadata["scope"] == "observed_research" and metadata["availability_mode"] == "recorded"
        reasons = []
        if metadata["scope"] != "observed_research":
            reasons.append("Automatic learning requires observed_research scope; synthetic or other research datasets are excluded.")
        if metadata["availability_mode"] != "recorded":
            reasons.append("Historical source availability is assumed, not recorded.")
        by_name = {Path(e["path"]).name: e for e in episodes}
        record = {
            "schema_version": 1, "name": name, "series": series, "scope": metadata["scope"],
            "event_ids": sorted({e["meta"]["event_id"] for e in episodes}), "splits": splits,
            "files": [{"name": p.name, "sha256": source_hashes[p.name], "bytes": p.stat().st_size,
                       "event_id": by_name[p.name]["meta"]["event_id"]} for p in copied],
            "split_hashes": manifest["split_hashes"], "corpus_sha256": manifest["corpus_sha256"],
            "channels": metadata["channels"], "units": metadata["units"], "target": metadata["target_definition"],
            "grid": metadata["grid"], "horizon_minutes": metadata["horizon_minutes"],
            "availability_mode": metadata["availability_mode"], "labels_available_at": available.isoformat(),
            "coverage_evidence": evidence, "max_target_end_utc": max_end.isoformat(),
            "learning_eligible": eligible, "readiness_reasons": reasons,
            "decoded_bytes": decoded, "window_bytes": windows,
        }
        record["id"] = _digest(record)
        record["created_at"] = _now().isoformat()
        (staging / "manifest.json").write_bytes(_canonical(record) + b"\n")
        destination = _under(datasets, datasets / record["id"])
        if destination.exists():
            existing = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
            verify_dataset(existing, store_root)
            if _record_identity(existing) != _record_identity(record):
                raise ValueError("An existing dataset identity has conflicting metadata")
            return existing
        try:
            staging.rename(destination)
        except FileExistsError:
            existing = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
            verify_dataset(existing, store_root)
            if _record_identity(existing) != _record_identity(record):
                raise ValueError("Concurrent dataset registration has conflicting metadata")
            return existing
        verify_dataset(record, store_root)
        return record
    finally:
        # Only this call's verified temporary directory is eligible for cleanup.
        if staging.exists():
            shutil.rmtree(_under(datasets, staging))


def prepare_demo_dataset(store_root):
    with tempfile.TemporaryDirectory(prefix="vajra-episodes-") as directory:
        source = Path(directory) / "episodes"
        train_images.make_smoke(source, event_count=8)
        return freeze_dataset(source, store_root, name="Eight-event synthetic ConvLSTM demonstration",
                              series="synthetic-blob-demonstration-v1", labels_available_at="2024-02-01T00:00:00+00:00",
                              coverage_evidence="Generated complete synthetic target masks; no observed weather or Indian lightning labels.")


def verify_dataset(record, store_root):
    identifier = record.get("id", "")
    if not isinstance(identifier, str) or not re.fullmatch(r"[0-9a-f]{64}", identifier) or _digest(_record_identity(record)) != identifier:
        raise ValueError("Dataset manifest identity failed verification")
    base = _under(store_root, Path(store_root) / "datasets" / identifier)
    saved = json.loads(_under(base, base / "manifest.json").read_text(encoding="utf-8"))
    if saved != record:
        raise ValueError("Dataset registry and immutable manifest disagree")
    directory = _under(base, base / "episodes")
    paths, decoded, windows = _preflight(directory)
    if decoded != record["decoded_bytes"] or windows != record["window_bytes"]:
        raise ValueError("Dataset admission budgets no longer match")
    files = record["files"]
    if {p.name for p in paths} != {entry["name"] for entry in files} or len(paths) != len(files):
        raise ValueError("Frozen dataset membership changed")
    for entry in files:
        if Path(entry["name"]).name != entry["name"]:
            raise ValueError("Dataset contains an invalid filename")
        path = _under(directory, directory / entry["name"])
        if path.stat().st_size != entry["bytes"] or _file_hash(path) != entry["sha256"]:
            raise ValueError("Frozen dataset file failed integrity verification")
    return directory


def recipe_identity(kind, dataset=None):
    if kind not in KINDS:
        raise ValueError("Unknown registered scientific recipe")
    sources = ["nowcast/operation_recipes.py"]
    identity = {"recipe_version": RECIPE_VERSION, "kind": kind}
    if kind == "starter_audit":
        sources.append("nowcast/data_catalog.py")
        identity["provider_manifests"] = {
            key: _file_hash(data_catalog.BASE / key / "manifest.json") if (data_catalog.BASE / key / "manifest.json").is_file() else None
            for key in sorted(data_catalog.COLLECTIONS)}
        identity["observed_files"] = {}
        for collection in sorted(data_catalog.COLLECTIONS):
            for entry in data_catalog.manifest_entries(collection):
                try:
                    path = data_catalog.safe_path(entry)
                    observed = {"sha256": _file_hash(path), "bytes": path.stat().st_size}
                except (FileNotFoundError, OSError, ValueError):
                    observed = {"status": "unavailable"}
                identity["observed_files"][collection + "--" + entry["id"]] = observed
    elif kind == "radar_replay":
        sources += ["nowcast/image_processing.py", "nowcast/real_data.py", "nowcast/numerics.py", "nowcast/verification.py"]
        identity.update(method="dense_optical_flow", preprocessing="smooth", horizon=10, input_hashes=real_data.EXPECTED)
        archive_manifest = real_data.DATA / "meteonet_manifest.json"
        identity["archive_manifest_sha256"] = _file_hash(archive_manifest) if archive_manifest.is_file() else None
    else:
        if dataset is None or not re.fullmatch(r"[0-9a-f]{64}", str(dataset.get("id", ""))):
            raise ValueError("Training requires a registered immutable dataset identity")
        sources += ["scripts/train_images.py", "nowcast/probability_evaluation.py"]
        identity.update(dataset_id=dataset["id"], corpus_sha256=dataset["corpus_sha256"],
                        split_hashes=dataset["split_hashes"], model="compact-convlstm-12-v1",
                        epochs=1, history=HISTORY, batch_size=4, device="cpu", calibrate=True, seed=17)
    identity["source_hashes"] = {name: _file_hash(ROOT / name) for name in sources}
    # The API need not load Torch. Identity describes the configured worker
    # environment, independently of which Python serves an HTTP request.
    worker_packages = ROOT / ".venv-ml" / "Lib" / "site-packages"
    if not worker_packages.is_dir():
        candidates = sorted((ROOT / ".venv-ml" / "lib").glob("python*/site-packages"))
        worker_packages = candidates[0] if len(candidates) == 1 else None
    versions = {dist.metadata["Name"].lower(): dist.version for dist in
                importlib.metadata.distributions(path=[str(worker_packages)])} if worker_packages else {}
    identity["packages"] = {name: versions.get(name, "not_installed")
                            for name in (["numpy", "torch"] if kind == "train_candidate" else ["numpy"])}
    identity["worker_profile"] = "repository-.venv-ml"
    return identity


def submit_recipe(store, kind, dataset_id=None):
    if kind not in KINDS:
        raise ValueError("Unknown registered scientific recipe")
    if kind == "train_candidate":
        if not isinstance(dataset_id, str) or not re.fullmatch(r"[0-9a-f]{64}", dataset_id):
            raise ValueError("Training requires a registered dataset ID")
        dataset = store.dataset(dataset_id)
        scope = dataset["scope"]
    else:
        if dataset_id is not None:
            raise ValueError("This recipe does not accept a training dataset")
        dataset = None
        scope = "Historical unmatched government starter files" if kind == "starter_audit" else "Historical French radar; not Indian or lightning validation"
    return store.enqueue(kind, recipe_identity(kind, dataset), {"dataset_id": dataset_id} if dataset else {}, scope)


def _artifact(path, root):
    path = _under(root, path)
    return {"id": path.stem.replace("_", "-"), "name": path.name,
            "relative_path": path.relative_to(Path(root).resolve()).as_posix(),
            "sha256": _file_hash(path), "bytes": path.stat().st_size}


def _write_json(path, value):
    path.write_bytes(_canonical(value) + b"\n")


def execute_recipe(job, attempt_dir: Path, store):
    kind = job["kind"]
    if kind not in KINDS:
        raise ValueError("Unknown registered scientific recipe")
    attempt_dir = _under(store.root, attempt_dir)
    if attempt_dir.exists() and any(attempt_dir.iterdir()):
        raise ValueError("Scientific execution requires a fresh attempt directory")
    attempt_dir.mkdir(parents=True, exist_ok=True)
    dataset = store.dataset(job["dataset_id"]) if kind == "train_candidate" else None
    expected = recipe_identity(kind, dataset)
    # The API and worker must use one environment/code version. Changed recipe
    # bytes require a new job identity, not silently different execution.
    if "identity" in job and job["identity"] != expected:
        raise ValueError("Recipe identity changed since this job was requested")
    if any(_IMPORTED_SOURCE_HASHES[name] != digest for name, digest in expected["source_hashes"].items()):
        raise ValueError("Source files changed after import; restart the research worker before execution")
    for package, version in expected["packages"].items():
        if version == "not_installed" or importlib.metadata.version(package) != version:
            raise ValueError("Run scientific work with the configured repository .venv-ml worker environment")

    def stage(value):
        if store.stage(job["id"], job["attempt_token"], value) is False:
            raise ValueError("Operation is no longer owned by this attempt")

    if kind == "starter_audit":
        stage("checking_manifest_hashes")
        rows = []
        for collection in sorted(data_catalog.COLLECTIONS):
            entries = data_catalog.manifest_entries(collection)
            if not entries:
                rows.append({"collection": collection, "file_id": None, "status": "missing_manifest_or_empty"})
            for entry in entries:
                file_id = collection + "--" + entry["id"]
                try:
                    path = data_catalog.safe_path(entry)
                    actual = _file_hash(path)
                    passed = path.stat().st_size == entry["bytes"] and actual == entry["sha256"]
                    rows.append({"collection": collection, "file_id": file_id, "status": "verified" if passed else "integrity_mismatch",
                                 "expected_sha256": entry["sha256"], "actual_sha256": actual, "bytes": path.stat().st_size})
                except (FileNotFoundError, OSError, ValueError):
                    rows.append({"collection": collection, "file_id": file_id, "status": "unavailable"})
        summary = {"mode": "starter_integrity_audit", "scope": "Historical unmatched government starter files",
                   "checked": len(rows), "verified": sum(row["status"] == "verified" for row in rows),
                   "problems": sum(row["status"] != "verified" for row in rows), "training_ready": False,
                   "public_dispatch_eligible": False,
                   "notes": "Byte integrity does not establish matched events, live observations or training readiness."}
        path = attempt_dir / "starter-audit.json"
        if recipe_identity(kind) != expected:
            raise ValueError("Starter files changed during the audit; request a new snapshot identity")
        _write_json(path, {"summary": summary, "files": rows, "identity": expected})
        return {"summary": summary, "artifacts": [_artifact(path, store.root)]}

    if kind == "radar_replay":
        stage("verifying_observed_radar")
        # load_sample is cached for the interactive UI. Verify current bytes and
        # clear that cache so a new operation never trusts stale loaded arrays.
        for name, digest in real_data.EXPECTED.items():
            if _file_hash(real_data.DATA / name) != digest:
                raise ValueError("Observed radar input failed its pinned integrity check")
        real_data.load_sample.cache_clear()
        stage("computing_observed_optical_flow")
        result = image_processing.image_run("dense_optical_flow", "smooth", 10)
        if recipe_identity(kind) != expected:
            raise ValueError("Observed radar provenance changed during the replay")
        compact = {key: value for key, value in result.items() if key not in ("layers", "masks")}
        summary = {"mode": "observed_radar_replay", "scope": result["scope"], "method": result["method"],
                   "horizon_minutes": 10, "metrics": result["metrics"], "public_dispatch_eligible": False,
                   "notes": result["limitations"], "time_note": result["time_note"]}
        path = attempt_dir / "observed-replay.json"
        _write_json(path, compact)
        return {"summary": summary, "artifacts": [_artifact(path, store.root)]}

    stage("verifying_frozen_dataset")
    directory = verify_dataset(dataset, store.root)
    stage("fitting_compact_convlstm")
    report = train_images.train(Namespace(data=str(directory), output=str(attempt_dir), history=HISTORY,
                                         epochs=1, batch_size=4, device="cpu", calibrate=True))
    stage("rechecking_frozen_evaluation")
    evaluation = train_images.evaluate(Namespace(data=str(directory), checkpoint=str(attempt_dir / "model.pt")))
    if evaluation != {key: report[key] for key in ("test", "test_calibrated", "probability_verification")}:
        raise ValueError("Frozen evaluation does not reproduce the training report")
    verify_dataset(dataset, store.root)
    if _file_hash(attempt_dir / "model.pt") != report["checkpoint_sha256"] or report["split_hashes"] != dataset["split_hashes"]:
        raise ValueError("Candidate checkpoint or split identity disagrees with the frozen report")
    path = attempt_dir / "frozen-evaluation.json"
    _write_json(path, evaluation)
    raw = report["test"]["brier"]
    calibrated = report["test_calibrated"]["brier"] if report["test_calibrated"] else None
    baseline = report["test"]["training_climatology_brier"]
    compared = calibrated if calibrated is not None else raw
    summary = {"mode": "training_candidate", "dataset_id": dataset["id"], "scope": dataset["scope"],
               "model": "compact-convlstm-12-v1", "raw_brier": raw, "calibrated_brier": calibrated,
               "baseline_brier": baseline, "test_event_count": report["probability_verification"]["event_count"],
               "recommendation": "retain_baseline" if compared >= baseline else "research_review_only",
               "public_dispatch_eligible": False, "promoted": False,
               "notes": ["One-epoch CPU research candidate; no operational or Indian lightning skill established.",
                         "Frozen evaluation reproduced exactly; repeated inspection is development evidence.",
                         "A lower Brier score on this small held-out cohort does not authorize model promotion."]}
    stage("verifying_result_artifacts")
    if recipe_identity(kind, dataset) != expected:
        raise ValueError("Recipe source or worker environment changed during training; request a new candidate identity")
    return {"summary": summary, "artifacts": [_artifact(attempt_dir / name, store.root)
            for name in ("model.pt", "report.json", "calibration.json", "frozen-evaluation.json")]}

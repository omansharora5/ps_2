"""Frozen observation verification and permission-aware benchmark manifests."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile

import numpy as np

from .probability_evaluation import probability_metrics


def _bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be an explicit UTC string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("Timestamp must use UTC")
    return parsed.astimezone(timezone.utc)


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("Expected a lowercase SHA256")
    return value


def _month(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise ValueError("month must be YYYY-MM")
    datetime.strptime(value, "%Y-%m")
    return value


def _probability(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Probability must be finite and in [0,1]")
    return float(value)


def _binary(value):
    if type(value) is not int or value not in (0, 1):
        raise ValueError("Observation and categorical forecast must be integer 0 or 1")
    return value


def _identity(case):
    return tuple(_text(case[key], key) for key in (
        "case_id", "event_id", "hazard", "label_definition", "geometry_id", "geometry_sha256", "target_start", "target_end"))


def _contingency(predictions, observations):
    hits = sum(p == 1 and y == 1 for p, y in zip(predictions, observations))
    misses = sum(p == 0 and y == 1 for p, y in zip(predictions, observations))
    alarms = sum(p == 1 and y == 0 for p, y in zip(predictions, observations))
    negatives = sum(p == 0 and y == 0 for p, y in zip(predictions, observations))
    def ratio(a, b):
        return a / b if b else None
    return {"case_count": len(observations), "hits": hits, "misses": misses, "false_alarms": alarms,
            "correct_negatives": negatives, "pod": ratio(hits, hits + misses),
            "far": ratio(alarms, hits + alarms), "csi": ratio(hits, hits + misses + alarms)}


def _metrics(cases, rate, threshold):
    if not cases:
        return {"case_count": 0, "event_count": 0, "pod": None, "far": None, "csi": None,
                "brier": None, "reliability": [], "status": "unavailable"}
    result = probability_metrics([c["probability"] for c in cases], [c["truth"]["observed"] for c in cases], rate, threshold)
    result["case_count"] = result.pop("covered_pixels")
    result["event_count"] = len({c["event_id"] for c in cases})
    result["status"] = "available"
    return result


def _bootstrap(cases, threshold, seed=17, replicates=200):
    groups = defaultdict(list)
    for case in cases:
        groups[case["event_id"]].append(case)
    result = {"status": "unavailable", "event_count": len(groups), "replicates": replicates, "seed": seed,
              "confidence_level": .95, "method": "Percentile bootstrap resampling whole event groups; model and threshold fixed",
              "note": "Few independent events give unstable intervals; training/calibration uncertainty is excluded.", "intervals": {}}
    if len(groups) < 2:
        return result
    statistics = []
    for rows in groups.values():
        counts = _contingency([int(c["probability"] >= threshold) for c in rows], [c["truth"]["observed"] for c in rows])
        statistics.append([len(rows), sum((c["probability"] - c["truth"]["observed"]) ** 2 for c in rows),
                           counts["hits"], counts["misses"], counts["false_alarms"]])
    rng = np.random.default_rng(seed)
    statistics = np.asarray(statistics)
    totals = np.empty((replicates, 5))
    for index in range(replicates):
        totals[index] = statistics[rng.integers(0, len(groups), size=len(groups))].sum(axis=0)
    scores = {"brier": totals[:, 1] / totals[:, 0]}
    for key, numerator, denominator in (("pod", totals[:, 2], totals[:, 2] + totals[:, 3]),
                                         ("far", totals[:, 4], totals[:, 2] + totals[:, 4]),
                                         ("csi", totals[:, 2], totals[:, 2] + totals[:, 3] + totals[:, 4])):
        scores[key] = np.divide(numerator, denominator, out=np.full(replicates, np.nan), where=denominator > 0)
    for key, values in scores.items():
        finite = values[np.isfinite(values)]
        limits = np.quantile(finite, [.025, .975]) if finite.size else (None, None)
        result["intervals"][key] = {"lower": float(limits[0]) if finite.size else None,
                                    "upper": float(limits[1]) if finite.size else None, "valid_replicates": int(finite.size)}
    result["status"] = "available"
    return result


def build_scorecard(config):
    """Evaluate frozen cases; invalid identity data fails, uncovered cases are counted."""
    month = _month(config["month"])
    cutoff = _instant(config["publication_cutoff"])
    model_id = _text(config["model_id"], "model_id")
    hazard = _text(config["hazard"], "hazard")
    definition = _text(config["label_definition"], "label_definition")
    threshold = _probability(config["threshold"])
    rate = _probability(config["training_climatology"])
    lead = config["lead_time_seconds"]
    duration = config["target_duration_seconds"]
    if type(lead) is not int or lead < 0 or type(duration) is not int or duration <= 0:
        raise ValueError("Task lead and target duration must be nonnegative/positive integer seconds")
    train = {_text(e, "train_event_id") for e in config["train_event_ids"]}
    validation = {_text(e, "validation_event_id") for e in config.get("validation_event_ids", [])}
    calibration = {_text(e, "calibration_event_id") for e in config["calibration_event_ids"]}
    if train & validation or train & calibration or validation & calibration:
        raise ValueError("Training, validation and calibration events overlap")
    cases = config["cases"]
    if not isinstance(cases, list) or len(cases) > 100000:
        raise ValueError("cases must be a list of at most 100000 frozen records")
    seen, physical_cases, admitted, excluded = set(), set(), [], Counter()
    for case in cases:
        _identity(case)
        _hash(case["geometry_sha256"])
        _hash(case["forecast_record_sha256"])
        if case["case_id"] in seen:
            raise ValueError("Duplicate case_id")
        seen.add(case["case_id"])
        issue, start, end = (_instant(case[key]) for key in ("issued_at", "target_start", "target_end"))
        physical_identity = (case["event_id"], case["hazard"], case["label_definition"], case["geometry_sha256"], start, end)
        if physical_identity in physical_cases:
            raise ValueError("Duplicate physical evaluation case, regardless of case_id or geometry alias")
        physical_cases.add(physical_identity)
        archive = _instant(case["forecast_archived_at"])
        probability = _probability(case["probability"])
        if issue > start or start >= end:
            raise ValueError("Target must be a positive interval beginning no earlier than issue time")
        if (start - issue).total_seconds() != lead or (end - start).total_seconds() != duration:
            raise ValueError("Case lead or target duration differs from scorecard task")
        if case["hazard"] != hazard or case["label_definition"] != definition:
            raise ValueError("A scorecard must describe one hazard and label definition")
        if case["event_id"] in train | validation | calibration:
            raise ValueError("Evaluation event was exposed to training, model-selection validation or calibration")
        truth = case["truth"]
        reason = None
        if start.strftime("%Y-%m") != month:
            reason = "outside_target_month"
        elif case.get("data_mode") != "observed":
            reason = "not_observed_data"
        elif archive > issue:
            reason = "forecast_not_archived_by_issue"
        elif truth.get("source_kind") != "instrument":
            reason = "truth_not_independent_instrument"
        elif truth.get("coverage_complete") is not True:
            reason = "incomplete_truth_coverage"
        else:
            available = _instant(truth["available_at"])
            _text(truth["source_id"], "truth source_id")
            _hash(truth["record_sha256"])
            if available < end:
                raise ValueError("Complete target truth cannot be available before target_end")
            if end > cutoff or available > cutoff:
                reason = "truth_not_mature_at_publication"
            elif _instant(truth["target_start"]) != start or _instant(truth["target_end"]) != end:
                reason = "truth_window_mismatch"
            elif truth["geometry_sha256"] != case["geometry_sha256"] or truth["label_definition"] != definition:
                reason = "truth_support_mismatch"
            else:
                _binary(truth["observed"])
        if reason:
            excluded[reason] += 1
            continue
        row = dict(case, probability=probability)
        for key in ("monsoon_phase", "season"):
            item = case.get(key)
            value = "unknown"
            if item is not None:
                _text(item["value"], key)
                _text(item["source_id"], f"{key} source_id")
                if _instant(item["available_at"]) <= issue:
                    value = item["value"]
            row[key] = value
        admitted.append(row)
    admitted.sort(key=lambda c: c["case_id"])
    metrics = _metrics(admitted, rate, threshold)
    strata = {}
    for key in ("monsoon_phase", "season"):
        groups = defaultdict(list)
        for case in admitted:
            groups[case[key]].append(case)
        strata[key] = {name: _metrics(rows, rate, threshold) for name, rows in sorted(groups.items())}
    comparison = _compare(config.get("comparator"), admitted, threshold, rate)
    return {"schema_version": 1, "month": month, "publication_cutoff": config["publication_cutoff"], "model_id": model_id,
            "hazard": hazard, "label_definition": definition, "status": metrics["status"],
            "lead_time_seconds": lead, "target_duration_seconds": duration,
            "input_sha256": _sha(_bytes(config)), "input_case_count": len(cases), "admitted_case_count": len(admitted),
            "cohort_sha256": _sha(_bytes([list(_identity(c)) + [c["issued_at"]] for c in admitted])),
            "excluded": dict(sorted(excluded.items())), "metrics": metrics, "strata": strata,
            "event_bootstrap": _bootstrap(admitted, threshold), "comparison": comparison,
            "notes": ["Month is determined by target_start in UTC.", "No model fitting or threshold tuning occurs during publication.",
                      "Citizen reports and synthetic cases are excluded from this independent instrument scorecard.",
                      "FAR is false-alarm ratio, not false-positive rate. Null metrics have undefined denominators.",
                      "Case/interval scores do not establish person-level safety or exact-point accuracy."]}


def _compare(comparator, admitted, threshold, rate):
    if comparator is None:
        return {"status": "unavailable", "reason": "No archived compatible comparator was provided", "matched_cases": 0}
    name = _text(comparator["name"], "comparator name")
    if comparator["kind"] != "categorical":
        raise ValueError("Comparator schema currently supports categorical forecasts only")
    originals = {c["case_id"]: c for c in admitted}
    seen, matched, predictions, excluded = set(), [], [], Counter()
    for entry in comparator["cases"]:
        _identity(entry)
        if entry["case_id"] in seen:
            raise ValueError("Duplicate comparator case_id")
        seen.add(entry["case_id"])
        _text(entry["source_id"], "comparator source_id")
        _hash(entry["archive_sha256"])
        prediction = _binary(entry["prediction"])
        own = originals.get(entry["case_id"])
        if own is None:
            excluded["outside_admitted_cohort"] += 1
        elif _identity(entry) != _identity(own):
            excluded["incompatible_target"] += 1
        elif _instant(entry["issued_at"]) > _instant(own["issued_at"]) or _instant(entry["archived_at"]) > _instant(own["issued_at"]):
            excluded["unavailable_by_issue_deadline"] += 1
        elif _instant(entry["archived_at"]) < _instant(entry["issued_at"]):
            raise ValueError("Comparator cannot be archived before it was issued")
        else:
            matched.append(own)
            predictions.append(prediction)
    return {"status": "available" if matched else "unavailable", "name": name, "kind": "categorical",
            "matched_cases": len(matched), "event_count": len({c["event_id"] for c in matched}),
            "unmatched_model_cases": len(admitted) - len(matched), "excluded": dict(sorted(excluded.items())),
            "paired_cohort_sha256": _sha(_bytes(sorted(c["case_id"] for c in matched))),
            "model": _metrics(matched, rate, threshold),
            "comparator": _contingency(predictions, [c["truth"]["observed"] for c in matched]),
            "note": "Both sides use only these matched cases. Categorical bulletins do not acquire invented probabilities or reliability curves."}


def _immutable(path, body):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == body:
            return
        raise ValueError(f"Immutable output already differs: {path.name}")
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != body:
                raise ValueError(f"Immutable output already differs: {path.name}")
    finally:
        Path(temporary).unlink(missing_ok=True)


def publish_scorecard(root, config, revision=1):
    if type(revision) is not int or not 1 <= revision <= 9999:
        raise ValueError("Revision must be an integer in [1,9999]")
    card = build_scorecard(config)
    card["revision"] = revision
    envelope = {"sha256": _sha(_bytes(card)), "scorecard": card}
    _immutable(Path(root) / card["month"] / f"r{revision:04d}.json", _bytes(envelope))
    return card


def read_scorecard(root, month):
    month = _month(month)
    paths = sorted((Path(root) / month).glob("r[0-9][0-9][0-9][0-9].json"))
    if not paths:
        return {"status": "unavailable", "month": month, "reason": "No verified scorecard has been published"}
    envelope = json.loads(paths[-1].read_text(encoding="utf-8"))
    card = envelope["scorecard"]
    if envelope["sha256"] != _sha(_bytes(card)) or card["month"] != month or paths[-1].stem != f"r{card['revision']:04d}":
        raise ValueError("Published scorecard checksum or identity mismatch")
    return card


def prepare_benchmark(config, base_dir, output=None):
    """Validate local files and write metadata only; never publish or copy raw data."""
    root = Path(base_dir).resolve()
    cutoff = _instant(config["frozen_at"])
    benchmark_id = _text(config["benchmark_id"], "benchmark_id")
    artifacts = config["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("Benchmark requires local artifacts")
    events, file_splits, intervals, output_rows, paths, reasons = {}, {}, defaultdict(list), [], set(), set()
    for entry in artifacts:
        event = _text(entry["event_id"], "event_id")
        split = entry["split"]
        if split not in ("train", "validation", "calibration", "test"):
            raise ValueError("split must be train, validation, calibration or test")
        if event in events and events[event] != split:
            raise ValueError("An event crosses benchmark splits")
        events[event] = split
        if entry["data_mode"] != "observed":
            raise ValueError("Synthetic artifacts cannot be admitted to an observed benchmark")
        relative = Path(entry["path"])
        candidate = (root / relative).resolve()
        if relative.is_absolute() or not candidate.is_relative_to(root) or not candidate.is_file():
            raise ValueError("Artifact must be an existing file within base_dir")
        if candidate in paths:
            raise ValueError("Artifact file is listed more than once")
        paths.add(candidate)
        digest = hashlib.sha256()
        with candidate.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != _hash(entry["sha256"]):
            raise ValueError("Artifact checksum mismatch")
        if entry["sha256"] in file_splits and file_splits[entry["sha256"]] != split:
            raise ValueError("Identical artifact content crosses benchmark splits")
        file_splits[entry["sha256"]] = split
        start, input_end, available, issue, target_start, target_end, truth_at = (_instant(entry[key]) for key in (
            "input_start", "input_end", "input_available_at", "issued_at", "target_start", "target_end", "truth_available_at"))
        if not start <= input_end <= available <= issue <= target_start < target_end <= truth_at <= cutoff:
            raise ValueError("Artifact violates causal availability or has immature truth")
        if entry["label_coverage_complete"] is not True:
            raise ValueError("Uncovered labels cannot enter the complete-label benchmark")
        duration = (target_end - target_start).total_seconds()
        if type(entry["target_duration_seconds"]) not in (int, float) or entry["target_duration_seconds"] != duration:
            raise ValueError("Declared target duration differs from timestamps")
        _text(entry["label_definition"], "label_definition")
        _hash(entry["geometry_sha256"])
        _text(entry["source_id"], "source_id")
        _text(entry["recipe"], "recipe")
        intervals[split].append((start, target_end))
        rights = entry.get("redistribution", {})
        permitted = rights.get("allowed") is True and isinstance(rights.get("evidence"), str) and bool(rights["evidence"].strip()) and isinstance(rights.get("license"), str) and bool(rights["license"].strip())
        private_ok = entry.get("privacy_review") == "approved"
        if not permitted:
            reasons.add("missing_per_file_redistribution_permission")
        if not private_ok:
            reasons.add("privacy_review_incomplete")
        output_rows.append({key: entry[key] for key in ("event_id", "split", "sha256", "source_id", "input_start", "input_end", "input_available_at", "issued_at", "target_start", "target_end", "truth_available_at", "target_duration_seconds", "label_definition", "geometry_sha256", "recipe")}
                           | {"bytes": candidate.stat().st_size, "raw_redistribution_permitted": permitted,
                              "redistribution": {key: rights.get(key) for key in ("allowed", "evidence", "license")},
                              "privacy_review": entry.get("privacy_review", "pending")})
    if not {"train", "calibration", "test"}.issubset(intervals):
        reasons.add("incomplete_train_calibration_test_splits")
    ordered = [s for s in ("train", "validation", "calibration", "test") if s in intervals]
    for before, after in zip(ordered, ordered[1:]):
        if max(end for _, end in intervals[before]) > min(start for start, _ in intervals[after]):
            raise ValueError("Chronological splits overlap in input or target windows")
    manifest = {"schema_version": 1, "benchmark_id": benchmark_id, "frozen_at": config["frozen_at"],
                "input_sha256": _sha(_bytes(config)), "export_mode": "metadata_and_recipes_only", "raw_files_exported": 0,
                "release_ready": not reasons, "release_blockers": sorted(reasons),
                "artifact_count": len(output_rows), "event_count": len(events),
                "split_event_counts": dict(Counter(events.values())), "artifacts": output_rows,
                "notes": ["This manifest does not transfer raw files or grant data rights.",
                          "Permissions and privacy status are supplied attestations requiring provider-specific review.",
                          "Observed metadata and hashes alone do not prove that the scientific labels are correct."]}
    if output is not None:
        _immutable(Path(output), _bytes({"sha256": _sha(_bytes(manifest)), "benchmark": manifest}))
    return manifest


def read_benchmark(output):
    path = Path(output)
    if not path.exists():
        return {"status": "metadata_only", "raw_release_allowed": False,
                "blockers": ["No verified aligned corpus manifest is available", "Per-file redistribution rights have not been established"]}
    envelope = json.loads(path.read_text(encoding="utf-8"))
    manifest = envelope["benchmark"]
    if envelope["sha256"] != _sha(_bytes(manifest)) or manifest.get("schema_version") != 1:
        raise ValueError("Benchmark manifest checksum or schema mismatch")
    return {**manifest, "status": "metadata_only", "raw_release_allowed": manifest["release_ready"],
            "blockers": manifest["release_blockers"],
            "integrity_note": "Manifest checksum verified; artifact hashes were verified when prepared. Raw files are not served."}

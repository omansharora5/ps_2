"""Bounded regional research training. No checkpoint is promoted or connected to alerts."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nowcast.probability_evaluation import EventPredictions, probability_metrics
from nowcast.regional_heads import make_regional_model, regional_loss
from nowcast.regional_science import (PHASES, PhaseEvent, apply_phase_calibration, fit_phase_calibration,
                                     eligible_onset_distribution, hazard_distribution, onset_summary, utc, validate_survival)


VERSION = "regional-convlstm-v1"
ROLES = ("train", "validation", "calibration", "test")
ARRAYS = {"values", "masks", "times_utc", "available_at_utc", "issue_utc", "target_end_utc",
          "event_ids", "roles", "phases", "phase_available_at_utc", "metadata_json",
          "lightning_targets", "lightning_coverage", "rain_event_bin", "rain_observed_bins",
          "rain_coverage", "rain_at_risk", "lightning_event_bin", "lightning_observed_bins",
          "lightning_onset_coverage", "lightning_at_risk"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_corpus(path):
    path = Path(path)
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Regional corpus exceeds the 64 MiB compressed budget")
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) != len(ARRAYS) or {e.filename for e in entries} != {name + ".npy" for name in ARRAYS}:
            raise ValueError("Regional corpus must contain exactly the documented arrays")
        if sum(e.file_size for e in entries) > 128 * 1024 * 1024:
            raise ValueError("Regional corpus exceeds the 128 MiB decoded budget")
        for item in entries:
            with archive.open(item) as stream:
                version = np.lib.format.read_magic(stream)
                reader = {(1, 0): np.lib.format.read_array_header_1_0,
                          (2, 0): np.lib.format.read_array_header_2_0}.get(version)
                if reader is None:
                    raise ValueError("Unsupported NPY version")
                shape, _, dtype = reader(stream)
                size = int(np.prod(shape, dtype=object)) * dtype.itemsize
                if dtype.hasobject or len(shape) > 5 or size > 128 * 1024 * 1024 or size + stream.tell() != item.file_size:
                    raise ValueError("Unsafe NPY shape, object dtype or payload size")
    with np.load(path, allow_pickle=False) as source:
        data = {key: source[key] for key in ARRAYS}
    meta = json.loads(str(data["metadata_json"].item()))
    required = {"schema_version", "channels", "units", "grid", "bin_edges_minutes", "scope",
                "availability_mode", "label_provenance", "target_definition"}
    if not isinstance(meta, dict) or not required.issubset(meta) or meta["schema_version"] != 1:
        raise ValueError("Missing versioned regional task metadata")
    if meta["scope"] not in ("synthetic_fixture", "observed_research") or meta["availability_mode"] not in ("recorded", "assumed_research_latency"):
        raise ValueError("Scope and availability mode must be explicit")
    if not meta["label_provenance"] or not meta["target_definition"] or not meta["grid"]:
        raise ValueError("Provenance, target definition and native spatial support are required")
    values = data["values"].astype(np.float32)
    if values.ndim != 5:
        raise ValueError("Regional values require [sample,history,channel,height,width]")
    n, history, channels, height, width = values.shape
    if not (8 <= n <= 256 and 2 <= history <= 12 and 1 <= channels <= 16 and 1 <= height <= 64 and 1 <= width <= 64):
        raise ValueError("Regional image dimensions exceed the bounded training contract")
    if len(meta["channels"]) != channels or len(meta["units"]) != channels or len(set(meta["channels"])) != channels:
        raise ValueError("Unique channels and units must match the tensor")
    masks = data["masks"]
    if masks.shape != values.shape or not np.isin(masks, [0, 1]).all():
        raise ValueError("Input masks must be boolean and match values")
    if not np.isfinite(values[masks.astype(bool)]).all():
        raise ValueError("Covered input values must be finite")
    for key in ("issue_utc", "target_end_utc", "event_ids", "roles", "phases", "phase_available_at_utc"):
        if data[key].shape != (n,):
            raise ValueError(f"{key} needs one entry per sample")
    if data["times_utc"].shape != (n, history) or data["available_at_utc"].shape != (n, history, channels):
        raise ValueError("History timestamps require [N,T] acquisition and [N,T,C] availability")
    timestamps = lambda array: np.asarray([utc(x).timestamp() for x in array.flat]).reshape(array.shape)
    times, available, issues, ends = (timestamps(data[key]) for key in ("times_utc", "available_at_utc", "issue_utc", "target_end_utc"))
    edges = meta["bin_edges_minutes"]
    hazard_distribution(np.zeros(len(edges)), edges)
    if ((np.diff(times, axis=1) <= 0).any() or (times > issues[:, None]).any()
            or (available < times[:, :, None]).any()
            or not np.allclose(ends - issues, edges[-1] * 60, rtol=0, atol=1e-6)):
        raise ValueError("Acquisitions/availability/target horizons violate causal time support")
    roles, event_ids = data["roles"].tolist(), data["event_ids"].tolist()
    if any(role not in ROLES for role in roles) or any(not isinstance(e, str) or not e for e in event_ids):
        raise ValueError("Every sample needs an event identity and a known partition")
    assignments = {}
    for event, role in zip(event_ids, roles):
        if event in assignments and assignments[event] != role:
            raise ValueError("An event cannot cross train/validation/calibration/test partitions")
        assignments[event] = role
    for role in ROLES:
        if len({event for event, assigned in assignments.items() if assigned == role}) < 2:
            raise ValueError("Each partition needs at least two independent event groups")
    for left, right in zip(ROLES, ROLES[1:]):
        if ends[data["roles"] == left].max() >= times[data["roles"] == right].min():
            raise ValueError("Adjacent partitions overlap in acquisition or label time")
    for index in range(n):
        PhaseEvent(EventPredictions(str(event_ids[index]), np.array([0.]), np.array([0.]), np.array([1])),
                   str(data["phases"][index]), str(data["issue_utc"][index]), str(data["phase_available_at_utc"][index]), roles[index])
    shape = (n, height, width)
    for key in ARRAYS - {"values", "masks", "times_utc", "available_at_utc", "issue_utc", "target_end_utc", "event_ids", "roles", "phases", "phase_available_at_utc", "metadata_json"}:
        if data[key].shape != shape:
            raise ValueError(f"{key} must match [sample,height,width]")
    for key in ("lightning_coverage", "rain_coverage", "lightning_onset_coverage", "rain_at_risk", "lightning_at_risk"):
        if not np.isin(data[key], [0, 1]).all():
            raise ValueError("All coverage and at-risk masks must be boolean")
    covered = data["lightning_coverage"].astype(bool)
    if not np.isin(data["lightning_targets"][covered], [0, 1]).all():
        raise ValueError("Covered lightning event labels must be binary")
    any_task = covered | data["rain_coverage"].astype(bool) | data["lightning_onset_coverage"].astype(bool)
    if not any_task.reshape(n, -1).any(axis=1).all():
        raise ValueError("Training samples require at least one covered task; keep unknown-only windows out of training")
    for prefix, coverage_key in (("rain", "rain_coverage"), ("lightning", "lightning_onset_coverage")):
        mask = data[coverage_key].astype(bool)
        if (mask & ~data[prefix + "_at_risk"].astype(bool)).any():
            raise ValueError("Onset labels require an observed event-free at-risk state at issue")
        validate_survival(np.zeros(shape + (len(edges),)), data[prefix + "_event_bin"], data[prefix + "_observed_bins"], mask)
    onset_covered = data["lightning_onset_coverage"].astype(bool)
    detected = covered & onset_covered & (data["lightning_event_bin"] >= 0)
    if (data["lightning_targets"][detected] != 1).any():
        raise ValueError("Detected lightning onset and covered binary occurrence disagree, including censored horizons")
    full = covered & onset_covered & (data["lightning_observed_bins"] == len(edges))
    if (data["lightning_targets"][full] != (data["lightning_event_bin"][full] >= 0)).any():
        raise ValueError("Full-horizon lightning event and onset labels disagree")
    causal = masks.astype(bool) & (available <= issues[:, None, None])[:, :, :, None, None]
    if not causal.reshape(n, -1).any(axis=1).all():
        raise ValueError("Every sample needs at least one usable causal observation")
    data.update(meta=meta, values=values, causal=causal, issue_seconds=issues, acquisition_seconds=times,
                sha256=sha(path), assignments=assignments)
    return data


def prepare_inputs(data):
    training = data["roles"] == "train"
    channels = data["values"].shape[2]
    mean, std = [], []
    for channel in range(channels):
        values = data["values"][training, :, channel][data["causal"][training, :, channel]].astype(np.float64)
        if not values.size:
            raise ValueError("A training input channel has no causal observations")
        mean.append(float(values.mean())); std.append(max(float(values.std()), 1e-3))
    normalized = (data["values"] - np.asarray(mean)[None, None, :, None, None]) / np.asarray(std)[None, None, :, None, None]
    age = np.clip((data["issue_seconds"][:, None] - data["acquisition_seconds"]) / 3600., 0, 2)
    age = np.broadcast_to(age[:, :, None, None, None], normalized.shape)
    x = np.concatenate([np.where(data["causal"], normalized, 0), data["causal"],
                        np.where(data["causal"], age, 0)], axis=2).astype(np.float32)
    if not np.isfinite(x).all():
        raise ValueError("Normalized inputs exceed finite float32 support")
    return x, {"mean": mean, "std": std, "age_scale_seconds": 3600, "age_clip_hours": 2}


def loss_for(outputs, data, index):
    return regional_loss(outputs, lightning_targets=data["lightning_targets"][index],
        lightning_coverage=data["lightning_coverage"][index],
        rain_onset=tuple(data[key][index] for key in ("rain_event_bin", "rain_observed_bins", "rain_coverage")),
        lightning_onset=tuple(data[key][index] for key in ("lightning_event_bin", "lightning_observed_bins", "lightning_onset_coverage")))


def train_corpus(path, output, *, steps=20, hidden=8, seed=17):
    if not (type(steps) is int and 1 <= steps <= 200 and type(hidden) is int and 1 <= hidden <= 32
            and type(seed) is int and 0 <= seed < 2 ** 32):
        raise ValueError("Training is bounded to 1–200 steps and 1–32 hidden channels")
    import torch
    torch.set_num_threads(2)
    torch.manual_seed(seed)
    data = load_corpus(path)
    x, normalization = prepare_inputs(data)
    config = {"version": VERSION, "corpus_sha256": data["sha256"], "steps": steps, "hidden": hidden, "seed": seed,
              "torch_version": str(torch.__version__), "numpy_version": str(np.__version__),
              "code_sha256": {name: sha(ROOT / name) for name in ("scripts/train_regional_heads.py", "nowcast/regional_heads.py", "nowcast/regional_science.py")}}
    identity = hashlib.sha256(canonical(config)).hexdigest()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    destination = output / identity
    if destination.exists():
        manifest = json.loads((destination / "manifest.json").read_text())
        if manifest["config"] != config or any(sha(destination / name) != digest for name, digest in manifest["files"].items()):
            raise ValueError("Existing research output failed its identity/integrity check")
        return manifest | {"directory": str(destination), "reused": True}
    model = make_regional_model(x.shape[2], hidden=hidden, bins=len(data["meta"]["bin_edges_minutes"]))
    optimizer = torch.optim.Adam(model.parameters(), lr=.01)
    train_index = np.flatnonzero(data["roles"] == "train")
    validation_index = np.flatnonzero(data["roles"] == "validation")
    best_loss, best_state = float("inf"), None
    history = []
    for step in range(steps):
        model.train()
        optimizer.zero_grad()
        index = train_index[(step * 4 + np.arange(min(4, len(train_index)))) % len(train_index)]
        loss = loss_for(model(torch.from_numpy(x[index])), data, index)["loss"]
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.)
        optimizer.step()
        model.eval()
        with torch.no_grad():
            val_losses = [float(loss_for(model(torch.from_numpy(x[part])), data, part)["loss"])
                          for part in np.array_split(validation_index, max(1, int(np.ceil(len(validation_index) / 4))))]
        validation_loss = float(np.mean(val_losses))
        if validation_loss < best_loss:
            best_loss = validation_loss
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
        history.append({"step": step + 1, "train_loss": float(loss.detach()), "validation_loss": validation_loss})
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        chunks = [model(torch.from_numpy(x[i:i + 4])) for i in range(0, len(x), 4)]
    outputs = {key: torch.cat([chunk[key] for chunk in chunks]).numpy() for key in chunks[0]}
    phase_events = []
    for event, role in data["assignments"].items():
        if role != "calibration":
            continue
        index = np.flatnonzero(data["event_ids"] == event)
        phases = set(data["phases"][index].tolist())
        if len(phases) != 1:
            raise ValueError("A calibration event must use one declared phase; split phase transitions into distinct events")
        if not data["lightning_coverage"][index].any():
            continue
        predictions = EventPredictions(event, outputs["lightning_logits"][index], data["lightning_targets"][index], data["lightning_coverage"][index])
        phase_events.append(PhaseEvent(predictions, phases.pop(), str(data["issue_utc"][index[0]]), str(data["phase_available_at_utc"][index[0]])))
    calibration = fit_phase_calibration(phase_events) if phase_events else None
    lightning_p = 1 / (1 + np.exp(-outputs["lightning_logits"]))
    if calibration:
        for i in range(len(x)):
            lightning_p[i] = apply_phase_calibration(outputs["lightning_logits"][i], str(data["phases"][i]), calibration,
                issue_time=str(data["issue_utc"][i]), phase_available_at=str(data["phase_available_at_utc"][i]))["probabilities"]
    test_index = np.flatnonzero(data["roles"] == "test")
    test_losses = loss_for({key: torch.from_numpy(value[test_index]) for key, value in outputs.items()}, data, test_index)
    training_labels = data["lightning_targets"][train_index][data["lightning_coverage"][train_index].astype(bool)]
    test_mask = data["lightning_coverage"][test_index].astype(bool)
    metrics = probability_metrics(lightning_p[test_index][test_mask], data["lightning_targets"][test_index][test_mask],
                                  float(training_labels.mean())) if training_labels.size and test_mask.any() else None
    rain_examples = np.argwhere(data["rain_at_risk"][test_index])
    if len(rain_examples):
        sample, row, column = rain_examples[0]
        rain_example = onset_summary(outputs["rain_onset_logits"][test_index[sample], row, column], data["meta"]["bin_edges_minutes"])
    else:
        rain_example = {"status": "unavailable", "reason": "No observed event-free rain-onset test pixels"}
    report = {"scope": data["meta"]["scope"], "operational": False, "validation_best_loss": best_loss,
              "test_lightning": metrics, "test_task_losses": {k: float(v) for k, v in test_losses.items() if k != "covered_counts"},
              "test_covered_counts": test_losses["covered_counts"], "phase_calibration": calibration, "training_history": history,
              "test_event_ids": sorted({str(data["event_ids"][i]) for i in test_index}),
              "rain_onset_example": rain_example,
              "note": "Smoke fixtures verify computation only. These are not validated NCR forecasts. Hazard probabilities remain uncalibrated."}
    staging = Path(tempfile.mkdtemp(prefix=".regional-", dir=output))
    try:
        checkpoint = {"version": VERSION, "state_dict": best_state, "model_channels": x.shape[2], "hidden": hidden,
                      "bins": len(data["meta"]["bin_edges_minutes"]), "normalization": normalization,
                      "history_length": x.shape[1], "spatial_shape": list(x.shape[-2:]),
                      "input_contract": data["meta"], "corpus_sha256": data["sha256"], "event_roles": data["assignments"],
                      "phase_calibration": calibration, "operational": False}
        torch.save(checkpoint, staging / "checkpoint.pt")
        reloaded = torch.load(staging / "checkpoint.pt", map_location="cpu", weights_only=True)
        restored = make_regional_model(reloaded["model_channels"], hidden=hidden, bins=reloaded["bins"])
        restored.load_state_dict(reloaded["state_dict"])
        restored.eval()
        with torch.no_grad():
            actual = restored(torch.from_numpy(x[test_index[:1]]))
        if any(not np.allclose(actual[key].numpy(), outputs[key][test_index[:1]], atol=1e-6) for key in outputs):
            raise RuntimeError("Checkpoint reload changed inference")
        report["checkpoint_reload_verified"] = True
        rain = eligible_onset_distribution(outputs["rain_onset_logits"][test_index], data["meta"]["bin_edges_minutes"], data["rain_at_risk"][test_index])
        lightning = eligible_onset_distribution(outputs["lightning_onset_logits"][test_index], data["meta"]["bin_edges_minutes"], data["lightning_at_risk"][test_index])
        np.savez_compressed(staging / "test_predictions.npz", lightning_probability=lightning_p[test_index],
                            rain_onset_mass=rain["event_mass"], rain_no_event_probability=rain["no_event_probability"],
                            rain_onset_eligible=rain["eligible"], lightning_onset_eligible=lightning["eligible"],
                            lightning_onset_mass=lightning["event_mass"], lightning_no_event_probability=lightning["no_event_probability"],
                            issue_utc=data["issue_utc"][test_index], event_ids=data["event_ids"][test_index])
        (staging / "report.json").write_bytes(canonical(report))
        manifest = {"schema_version": 1, "id": identity, "scope": data["meta"]["scope"], "config": config,
                    "files": {name: sha(staging / name) for name in ("checkpoint.pt", "report.json", "test_predictions.npz")},
                    "operational": False}
        (staging / "manifest.json").write_bytes(canonical(manifest))
        try:
            os.rename(staging, destination)
        except OSError:
            if not destination.is_dir():
                raise
            existing = json.loads((destination / "manifest.json").read_text())
            if existing["config"] != config or any(sha(destination / name) != digest for name, digest in existing["files"].items()):
                raise ValueError("Concurrent research output failed integrity verification")
            manifest = existing
        return manifest | {"directory": str(destination), "reused": False}
    finally:
        if staging.exists():
            if not staging.resolve().is_relative_to(output) or staging.resolve() == output:
                raise RuntimeError("Refusing cleanup outside the research output directory")
            shutil.rmtree(staging)


def predict_history(checkpoint_path, *, values, masks, times_utc, available_at_utc,
                    issue_time, input_contract, rain_at_risk, lightning_at_risk,
                    phase="unknown", phase_available_at=None):
    """Causal inference accepts no labels/future outcomes. Returns research probability arrays."""
    import torch
    path = Path(checkpoint_path)
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Research checkpoint exceeds the bounded size")
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if checkpoint.get("version") != VERSION or checkpoint.get("operational") is not False:
        raise ValueError("Expected an unpromoted regional research checkpoint")
    contract = checkpoint["input_contract"]
    if phase not in PHASES or utc(phase_available_at or issue_time) > utc(issue_time):
        raise ValueError("Inference phase must be known or unknown and available by issue time")
    if any(input_contract.get(key) != contract[key] for key in ("channels", "units", "grid", "availability_mode")):
        raise ValueError("Inference channels, units, grid and availability mode must match the checkpoint")
    values, masks = np.asarray(values, dtype=np.float32), np.asarray(masks)
    channels = len(contract["channels"])
    expected = (checkpoint["history_length"], channels, *checkpoint["spatial_shape"])
    if values.shape != expected or masks.shape != expected or not np.isin(masks, [0, 1]).all():
        raise ValueError("Inference values/masks differ from the checkpoint image contract")
    for eligibility in (rain_at_risk, lightning_at_risk):
        if np.asarray(eligibility).shape != tuple(checkpoint["spatial_shape"]) or not np.isin(eligibility, [0, 1]).all():
            raise ValueError("Inference requires explicit boolean rain and lightning onset eligibility for every pixel")
    acquired = np.array([utc(t).timestamp() for t in times_utc])
    available = np.asarray([[utc(t).timestamp() for t in row] for row in available_at_utc])
    issue = utc(issue_time).timestamp()
    if acquired.shape != (expected[0],) or available.shape != expected[:2]:
        raise ValueError("Inference timestamps require [history] acquisition and [history,channel] availability")
    if (np.diff(acquired) <= 0).any() or (acquired > issue).any() or (available < acquired[:, None]).any():
        raise ValueError("Inference timestamps violate causal support")
    causal = masks.astype(bool) & (available <= issue)[:, :, None, None]
    if not causal.any() or not np.isfinite(values[causal]).all():
        raise ValueError("Inference needs finite causal measurements")
    norm = checkpoint["normalization"]
    normalized = (values - np.asarray(norm["mean"])[None, :, None, None]) / np.asarray(norm["std"])[None, :, None, None]
    age = np.broadcast_to(np.clip((issue - acquired) / norm["age_scale_seconds"], 0, norm["age_clip_hours"])[:, None, None, None], values.shape)
    x = np.concatenate([np.where(causal, normalized, 0), causal, np.where(causal, age, 0)], axis=1).astype(np.float32)
    if not np.isfinite(x).all():
        raise ValueError("Normalized inference inputs exceed finite float32 support")
    model = make_regional_model(checkpoint["model_channels"], hidden=checkpoint["hidden"], bins=checkpoint["bins"])
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    with torch.no_grad():
        outputs = {key: value[0].numpy() for key, value in model(torch.from_numpy(x[None])).items()}
    lightning = np.exp(-np.logaddexp(0, -outputs["lightning_logits"]))
    calibration_source = "uncalibrated"
    if checkpoint["phase_calibration"] is not None:
        calibrated = apply_phase_calibration(outputs["lightning_logits"], phase, checkpoint["phase_calibration"],
            issue_time=issue_time, phase_available_at=phase_available_at or issue_time)
        lightning, calibration_source = calibrated["probabilities"], calibrated["source"]
    return {"operational": False, "scope": contract["scope"], "issue_time": issue_time,
            "lightning_probability": lightning, "lightning_calibration_source": calibration_source,
            "rain_onset": eligible_onset_distribution(outputs["rain_onset_logits"], contract["bin_edges_minutes"], rain_at_risk),
            "lightning_onset": eligible_onset_distribution(outputs["lightning_onset_logits"], contract["bin_edges_minutes"], lightning_at_risk),
            "hazard_calibration": "uncalibrated", "missing_input_fraction": float(1 - causal.mean())}


def make_fixture(path):
    """Eight distinct synthetic dates, two events per partition; no skill evidence."""
    rng = np.random.default_rng(17)
    n, t, c, h, w, bins = 8, 3, 2, 4, 4, 6
    values = rng.normal(size=(n, t, c, h, w)).astype(np.float32)
    rain_bins = np.clip(((values[:, -1, 0] + 2) * 1.3).astype(int), 0, bins - 1)
    lightning_bins = np.where(values[:, -1, 1] > 0, 2, -1)
    observed = np.full((n, h, w), bins)
    start = datetime(2020, 1, 1, 12, tzinfo=timezone.utc)
    stamp = lambda dt: dt.isoformat().replace("+00:00", "Z")
    issues = [start + timedelta(days=i) for i in range(n)]
    times = [[stamp(issue - timedelta(minutes=10 * (t - j - 1))) for j in range(t)] for issue in issues]
    meta = {"schema_version": 1, "channels": ["synthetic_radar", "synthetic_environment"], "units": ["arbitrary", "arbitrary"],
            "grid": "synthetic_4x4_no_geography", "bin_edges_minutes": [5, 10, 15, 20, 25, 30],
            "scope": "synthetic_fixture", "availability_mode": "assumed_research_latency",
            "label_provenance": "Generated deterministic fixture, not Indian observations", "target_definition": "Covered lightning within 30 minutes and first rain/lightning onset after event-free issue"}
    data = dict(values=values, masks=np.ones_like(values, dtype=bool), times_utc=np.array(times),
                available_at_utc=np.repeat(np.array(times)[:, :, None], c, axis=2),
                issue_utc=np.array([stamp(x) for x in issues]), target_end_utc=np.array([stamp(x + timedelta(minutes=30)) for x in issues]),
                event_ids=np.array([f"synthetic-{i}" for i in range(n)]), roles=np.repeat(ROLES, 2),
                phases=np.array(["active"] * n), phase_available_at_utc=np.array([stamp(x - timedelta(hours=1)) for x in issues]),
                metadata_json=np.array(json.dumps(meta)), lightning_targets=(lightning_bins >= 0).astype(np.float32),
                lightning_coverage=np.ones_like(observed, bool), rain_event_bin=rain_bins, rain_observed_bins=observed,
                rain_coverage=np.ones_like(observed, bool), rain_at_risk=np.ones_like(observed, bool),
                lightning_event_bin=lightning_bins, lightning_observed_bins=observed,
                lightning_onset_coverage=np.ones_like(observed, bool), lightning_at_risk=np.ones_like(observed, bool))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with np.load(path, allow_pickle=False) as existing:
            if set(existing.files) != set(data) or any(not np.array_equal(existing[key], value) for key, value in data.items()):
                raise ValueError("Existing synthetic fixture differs; choose a separate output directory")
        return path
    np.savez_compressed(path, **data)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("smoke", "validate", "train"))
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "regional-research")
    parser.add_argument("--steps", type=int, default=20)
    args = parser.parse_args()
    if args.command == "smoke":
        path = make_fixture(args.output / "synthetic_fixture.npz")
        result = train_corpus(path, args.output, steps=args.steps)
    elif args.corpus is None:
        parser.error("--corpus is required for observed validate/train")
    elif args.command == "validate":
        data = load_corpus(args.corpus)
        result = {"status": "valid_research_contract", "scope": data["meta"]["scope"], "events": data["assignments"], "operational": False}
    else:
        result = train_corpus(args.corpus, args.output, steps=args.steps)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

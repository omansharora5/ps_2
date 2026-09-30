"""Validate event episodes and train a compact, masked ConvLSTM experiment.

This opt-in CLI does not load weights into the web application's simulator.
Torch is needed only for train/evaluate/smoke, not for episode validation.
"""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nowcast.probability_evaluation import EventPredictions, evaluate_events, fit_temperature


def instant(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise ValueError("Episode timestamps must explicitly identify UTC; unverified French timestamps cannot be relabelled UTC")
    return dt.timestamp()


def load_episode(path, history=3):
    with zipfile.ZipFile(path) as archive:
        if sum(item.file_size for item in archive.infolist()) > 512_000_000:
            raise ValueError("Episode exceeds 512 MB decoded budget; prepare smaller bounded episodes")
    required = {"values", "masks", "times_utc", "available_at_utc", "targets", "coverage", "target_end_utc", "metadata_json"}
    with np.load(path, allow_pickle=False) as archive:
        if not required.issubset(archive.files):
            raise ValueError(f"{path.name}: not an episode; missing {sorted(required-set(archive.files))}. Starter radar files are not training episodes.")
        data = {key: archive[key] for key in required}
    meta = json.loads(str(data["metadata_json"].item()))
    for key in ("event_id", "channels", "units", "grid", "target_definition", "horizon_minutes", "availability_mode", "provenance", "scope"):
        if key not in meta:
            raise ValueError(f"{path.name}: missing metadata {key}")
    if meta["availability_mode"] not in ("recorded", "assumed_research_latency"):
        raise ValueError("Availability mode must distinguish recorded readiness from assumed research latency")
    values = data["values"].astype(np.float32)
    masks, coverage, targets = data["masks"], data["coverage"], data["targets"].astype(np.float32)
    if values.ndim != 4 or values.shape[0] < history or min(values.shape[1:]) < 1:
        raise ValueError("values must have shape [time,channel,height,width] and enough causal frames")
    t, c, h, w = values.shape
    if masks.shape != values.shape or targets.shape != (t, h, w) or coverage.shape != targets.shape:
        raise ValueError("Mask/target/coverage shapes do not match the episode")
    if not np.isin(masks, [0, 1]).all() or not np.isin(coverage, [0, 1]).all():
        raise ValueError("Masks and coverage must be boolean or 0/1")
    masks, coverage = masks.astype(bool), coverage.astype(bool)
    if not np.isfinite(values[masks]).all() or not np.isin(targets[coverage], [0, 1]).all():
        raise ValueError("Valid inputs must be finite and covered targets must be binary")
    if len(meta["channels"]) != c or len(meta["units"]) != c or len(set(meta["channels"])) != c:
        raise ValueError("Channel names and declared units must match unique input channels")
    if data["times_utc"].shape != (t,) or data["available_at_utc"].shape != (t, c) or data["target_end_utc"].shape != (t,):
        raise ValueError("UTC arrays must have shapes [T], [T,C], [T]")
    times = np.array([instant(x) for x in data["times_utc"]])
    available = np.array([[instant(x) for x in row] for row in data["available_at_utc"]])
    ends = np.array([instant(x) for x in data["target_end_utc"]])
    if (np.diff(times) <= 0).any() or not np.allclose(np.diff(times), np.diff(times)[0]):
        raise ValueError("Episode requires ordered, equally spaced issue/acquisition times; gaps must be explicit masked slots")
    if (available < times[:, None]).any():
        raise ValueError("A source cannot be ready before its acquisition ends")
    if not 0 < float(meta["horizon_minutes"]) <= 120 or not np.allclose(ends - times, float(meta["horizon_minutes"]) * 60):
        raise ValueError("Each target must end at issue plus the declared positive horizon")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "meta": meta,
            "values": values, "masks": masks, "targets": np.where(coverage, targets, 0), "coverage": coverage,
            "times": times, "available": available, "ends": ends}


def corpus(directory, history=3, calibrate=False):
    paths = sorted(Path(directory).glob("*.npz"))
    if not paths:
        raise ValueError("No episode NPZ files found")
    episodes = [load_episode(path, history) for path in paths]
    signature = lambda e: (e["meta"]["channels"], e["meta"]["units"], e["meta"]["target_definition"],
                           e["meta"]["horizon_minutes"], float(e["times"][1] - e["times"][0]), e["values"].shape[1:], e["meta"]["grid"], e["meta"]["availability_mode"], e["meta"]["scope"])
    if any(signature(e) != signature(episodes[0]) for e in episodes):
        raise ValueError("Episodes mix incompatible channels, geometry, targets, availability mode or scope")
    groups = {}
    for e in episodes:
        groups.setdefault(e["meta"]["event_id"], []).append(e)
    if len(groups) < 6:
        raise ValueError("At least six independent event groups are required for this experimental split; a small single-event radar replay is not a training corpus")
    if calibrate and len(groups) < 8:
        raise ValueError("Calibration requires at least eight independent event groups for train/validation/calibration/test")
    ordered = sorted(groups, key=lambda key: min(e["times"][0] for e in groups[key]))
    if calibrate:
        ntest = max(2, len(ordered) // 5)
        splits = {"train": ordered[:-3 * ntest], "validation": ordered[-3 * ntest:-2 * ntest],
                  "calibration": ordered[-2 * ntest:-ntest], "test": ordered[-ntest:]}
    else:
        ntest = max(1, len(ordered) // 5)
        splits = {"train": ordered[:-2 * ntest], "validation": ordered[-2 * ntest:-ntest], "test": ordered[-ntest:]}
    # Conservative global temporal purge: adjacent splits cannot share acquisition or target windows.
    for left, right in zip(list(splits), list(splits)[1:]):
        end = max(e["ends"][-1] for key in splits[left] for e in groups[key])
        start = min(e["times"][0] for key in splits[right] for e in groups[key])
        if end >= start:
            raise ValueError(f"{left}/{right} overlap in input or future-label time; separate event dates or purge overlap")
    return episodes, splits


def split_hashes(episodes, splits):
    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    files = {Path(e["path"]).name: e["sha256"] for e in episodes}
    hashes = {key: digest({"event_ids": ids, "files": {Path(e["path"]).name: e["sha256"]
                         for e in episodes if e["meta"]["event_id"] in ids}}) for key, ids in splits.items()}
    return {"files": files, "split_hashes": hashes, "corpus_sha256": digest(files)}


def causal_input_mask(episode, index, history):
    section = slice(index - history + 1, index + 1)
    return episode["masks"][section] & (episode["available"][section] <= episode["times"][index])[:, :, None, None]


def normalizer(episodes, train_ids, history=3):
    c = episodes[0]["values"].shape[1]
    sums, squares, counts = np.zeros(c), np.zeros(c), np.zeros(c)
    for e in episodes:
        if e["meta"]["event_id"] not in train_ids:
            continue
        supported = np.zeros_like(e["masks"], dtype=bool)
        for index in range(history - 1, len(e["times"])):
            if e["coverage"][index].any():
                supported[index - history + 1:index + 1] |= causal_input_mask(e, index, history)
        for channel in range(c):
            values = e["values"][:, channel][supported[:, channel]].astype(float)
            sums[channel] += values.sum(); squares[channel] += (values ** 2).sum(); counts[channel] += values.size
    if (counts == 0).any():
        raise ValueError("A training channel has no valid measurements in covered causal input windows")
    mean = sums / counts
    std = np.sqrt(np.maximum(squares / counts - mean ** 2, 1e-6))
    return mean.astype(np.float32), std.astype(np.float32)


def examples(episodes, event_ids, history, mean, std):
    data = []
    for e in episodes:
        if e["meta"]["event_id"] not in event_ids:
            continue
        for index in range(history - 1, len(e["times"])):
            section = slice(index - history + 1, index + 1)
            mask = causal_input_mask(e, index, history)
            if not mask.any() or not e["coverage"][index].any():
                continue
            values = (e["values"][section] - mean[None, :, None, None]) / std[None, :, None, None]
            x = np.concatenate([np.where(mask, values, 0), mask.astype(np.float32)], axis=1).astype(np.float32)
            data.append((x, e["targets"][index], e["coverage"][index]))
    if not data:
        raise ValueError("A split has no covered, causal examples")
    return data


def make_model(channels, hidden=12):
    import torch
    from torch import nn

    class CompactConvLSTM(nn.Module):
        def __init__(self):
            super().__init__()
            self.gates = nn.Conv2d(channels + hidden, hidden * 4, 3, padding=1)
            self.head = nn.Conv2d(hidden, 1, 1)

        def forward(self, sequence):
            b, _, _, h, w = sequence.shape
            state = sequence.new_zeros((b, hidden, h, w))
            cell = torch.zeros_like(state)
            for frame in sequence.unbind(1):
                i, f, o, candidate = self.gates(torch.cat([frame, state], dim=1)).chunk(4, dim=1)
                cell = torch.sigmoid(f) * cell + torch.sigmoid(i) * torch.tanh(candidate)
                state = torch.sigmoid(o) * torch.tanh(cell)
            return self.head(state).squeeze(1)

    return CompactConvLSTM()


def batches(data, batch_size, torch, shuffle=False):
    indices = torch.randperm(len(data)).tolist() if shuffle else list(range(len(data)))
    for start in range(0, len(indices), batch_size):
        batch = [data[i] for i in indices[start:start + batch_size]]
        yield tuple(torch.from_numpy(np.stack([row[k] for row in batch])) for k in range(3))


def evaluate_model(model, data, torch, device, batch_size):
    model.eval()
    squared, count, positives, hits, misses, false_alarms = 0.0, 0, 0, 0, 0, 0
    with torch.no_grad():
        for x, y, mask in batches(data, batch_size, torch):
            p = torch.sigmoid(model(x.to(device))).cpu()
            p, y = p[mask], y[mask]
            squared += ((p - y) ** 2).sum().item(); count += y.numel(); positives += int(y.sum())
            hits += int(((p >= .5) & (y == 1)).sum())
            misses += int(((p < .5) & (y == 1)).sum())
            false_alarms += int(((p >= .5) & (y == 0)).sum())
    return {"covered_pixels": count, "brier": squared / count, "observed_rate": positives / count,
            "hits": hits, "misses": misses, "false_alarms": false_alarms,
            "csi": hits / (hits + misses + false_alarms) if hits + misses + false_alarms else None,
            "calibration": "Not calibrated; experimental sigmoid output", "independence_note": "Pixel counts are not independent event counts"}


def predict_events(model, episodes, ids, history, mean, std, torch, device, batch_size):
    model.eval()
    predictions = []
    with torch.no_grad():
        for event_id in ids:
            data = examples(episodes, [event_id], history, mean, std)
            logits, targets, coverage = [], [], []
            for x, y, mask in batches(data, batch_size, torch):
                logits.append(model(x.to(device)).cpu().numpy())
                targets.append(y.numpy()); coverage.append(mask.numpy())
            predictions.append(EventPredictions(event_id, np.concatenate(logits), np.concatenate(targets), np.concatenate(coverage)))
    return predictions


def final_evaluation(model, episodes, artifact, torch, device, batch_size):
    predictions = predict_events(model, episodes, artifact["splits"]["test"], artifact["history"],
                                 np.array(artifact["mean"], dtype=np.float32), np.array(artifact["std"], dtype=np.float32),
                                 torch, device, batch_size)
    scores = evaluate_events(predictions, artifact["training_climatology"], artifact["calibrator"])
    return {"test": scores.pop("raw"), "test_calibrated": scores.pop("calibrated"), "probability_verification": scores}


def input_contract(episode):
    return {"shape": list(episode["values"].shape[1:]),
            "frame_interval_seconds": float(episode["times"][1] - episode["times"][0])}


def checkpoint_normalizer(artifact, episode, history):
    """Validate a compatible compact model before reusing its weights or scales."""
    if artifact.get("architecture") != "compact-convlstm-12-v1":
        raise ValueError("Checkpoint architecture is not compact-convlstm-12-v1")
    if type(artifact.get("history")) is not int or artifact["history"] != history or history < 2:
        raise ValueError("Checkpoint history differs from requested history")
    channels = episode["values"].shape[1]
    if type(artifact.get("channels")) is not int or artifact["channels"] != channels * 2:
        raise ValueError("Checkpoint input channels do not match measurement and mask channels")
    metadata = artifact.get("metadata", {})
    for key in ("channels", "units", "grid", "target_definition", "horizon_minutes"):
        if metadata.get(key) != episode["meta"][key]:
            raise ValueError(f"Checkpoint {key} differs from episode; silent transfer is unsafe")
    # Legacy artifacts have the full grid in metadata, but not a recorded cadence.
    if "input_contract" in artifact and artifact["input_contract"] != input_contract(episode):
        raise ValueError("Checkpoint input shape or frame cadence differs from episode")
    mean, std = np.asarray(artifact.get("mean"), dtype=np.float32), np.asarray(artifact.get("std"), dtype=np.float32)
    if mean.shape != (channels,) or std.shape != (channels,) or not np.isfinite(mean).all() or not np.isfinite(std).all() or (std <= 0).any():
        raise ValueError("Checkpoint requires finite per-channel normalizer and positive scales")
    return mean, std


def exposure_ids(artifact):
    """All prior splits count as exposure, including ancestral held-out events."""
    splits = artifact.get("splits")
    if not isinstance(splits, dict) or not {"train", "validation", "test"}.issubset(splits):
        raise ValueError("Checkpoint has no complete event exposure manifest")
    groups = list(splits.values()) + [artifact.get("exposure_event_ids", [])]
    if any(not isinstance(ids, list) or any(not isinstance(value, str) or not value for value in ids) for ids in groups):
        raise ValueError("Checkpoint exposure groups must contain nonempty event identifiers")
    if any(not splits[key] for key in ("train", "validation", "test")):
        raise ValueError("Checkpoint exposure splits cannot be empty")
    return {value for ids in groups for value in ids}


def initialize_model(model, checkpoint, episodes, splits, history, torch):
    """Reuse weights and their normalizer; never reuse a fitted calibrator."""
    path = Path(checkpoint)
    artifact = torch.load(path, map_location="cpu", weights_only=True)
    mean, std = checkpoint_normalizer(artifact, episodes[0], history)
    exposed = exposure_ids(artifact)
    held_out = {event_id for key, ids in splits.items() if key != "train" for event_id in ids}
    overlap = sorted(exposed & held_out)
    if overlap:
        raise ValueError(f"Initializer exposure overlaps new validation/calibration/test events: {overlap}")
    try:
        model.load_state_dict(artifact["state_dict"], strict=True)
    except (KeyError, RuntimeError) as error:
        raise ValueError("Checkpoint weights do not match the declared compact architecture") from error
    if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
        raise ValueError("Checkpoint weights must be finite")
    provenance = {"checkpoint_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                  "checkpoint_name": path.name, "architecture": artifact["architecture"],
                  "corpus_sha256": artifact.get("corpus_sha256"), "exposure_event_ids": sorted(exposed),
                  "source_scope": artifact["metadata"].get("scope"), "normalizer": "preserved_from_initializer",
                  "cadence_verified": "input_contract" in artifact,
                  "calibrator": "discarded; any calibration must be fitted on new held-out events"}
    return mean, std, provenance


def train(args):
    import torch
    calibrate = getattr(args, "calibrate", False)
    episodes, splits = corpus(args.data, args.history, calibrate=calibrate)
    torch.manual_seed(17)
    torch.set_num_threads(min(4, torch.get_num_threads()))
    if args.device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA requested but unavailable; choose cpu or install a compatible CUDA PyTorch build")
    model = make_model(episodes[0]["values"].shape[1] * 2)
    initialization = None
    if getattr(args, "initialize_from", None):
        mean, std, initialization = initialize_model(model, args.initialize_from, episodes, splits, args.history, torch)
    else:
        mean, std = normalizer(episodes, splits["train"], args.history)
    datasets = {key: examples(episodes, ids, args.history, mean, std) for key, ids in splits.items()}
    covered = np.concatenate([y[m] for _, y, m in datasets["train"]])
    if len(np.unique(covered)) != 2:
        raise ValueError("Training requires covered positive and negative targets")
    training_rate = float(covered.astype(float).mean())
    manifest = split_hashes(episodes, splits)
    model.to(args.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output / "model.pt"
    if checkpoint_path.exists():
        raise ValueError("Output already contains model.pt; use a new run directory")
    history_log, best = [], float("inf")
    for epoch in range(args.epochs):
        model.train()
        for x, y, mask in batches(datasets["train"], args.batch_size, torch, shuffle=True):
            x, y, mask = x.to(args.device), y.to(args.device), mask.to(args.device)
            optimizer.zero_grad(set_to_none=True)
            loss = torch.nn.functional.binary_cross_entropy_with_logits(model(x), y, reduction="none")[mask].mean()
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); optimizer.step()
        val = evaluate_model(model, datasets["validation"], torch, args.device, args.batch_size)
        history_log.append({"epoch": epoch + 1, "validation": val})
        print(json.dumps(history_log[-1]), flush=True)
        if val["brier"] < best:
            best = val["brier"]
            artifact = {"state_dict": model.cpu().state_dict(), "channels": episodes[0]["values"].shape[1] * 2,
                        "history": args.history, "mean": mean.tolist(), "std": std.tolist(), "splits": splits,
                        "metadata": episodes[0]["meta"], **manifest, "training_climatology": training_rate,
                        "torch_version": str(torch.__version__), "calibrated": False, "architecture": "compact-convlstm-12-v1",
                        "calibration_requested": calibrate, "calibrator": None, "evaluation_version": "event-probability-v1",
                        "evaluation_batch_size": args.batch_size, "input_contract": input_contract(episodes[0]),
                        "initialization": initialization,
                        "exposure_event_ids": sorted({event_id for ids in splits.values() for event_id in ids} |
                                                     set(initialization["exposure_event_ids"] if initialization else []))}
            temporary = output / "model.pt.part"; torch.save(artifact, temporary); temporary.replace(checkpoint_path)
            model.to(args.device)
    artifact = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model.load_state_dict(artifact["state_dict"]); model.to(args.device)
    if calibrate:
        calibration_events = predict_events(model, episodes, splits["calibration"], args.history, mean, std, torch, args.device, args.batch_size)
        artifact["calibrator"] = fit_temperature(calibration_events)
        artifact["calibrated"] = artifact["calibrator"]["fit_status"] == "fitted"
        temporary = output / "model.pt.part"; torch.save(artifact, temporary); temporary.replace(checkpoint_path)
    checkpoint_hash = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    calibration_record = {"schema_version": 1, "checkpoint_sha256": checkpoint_hash, "calibration_requested": calibrate,
                          "calibrator": artifact["calibrator"], "training_climatology": training_rate, "splits": splits, **manifest}
    (output / "calibration.json").write_text(json.dumps(calibration_record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    report = {"scope": episodes[0]["meta"]["scope"], "splits": splits,
              "examples": {k: len(v) for k, v in datasets.items()}, "history": history_log,
              "initialization": initialization, "exposure_event_ids": artifact["exposure_event_ids"],
              **final_evaluation(model, episodes, artifact, torch, args.device, args.batch_size),
              "checkpoint_sha256": checkpoint_hash, "split_hashes": manifest["split_hashes"],
              "limitations": "Pipeline experiment only; no operational validation or India skill claim. Calibration may worsen held-out scores. Event minima are software checks, not sample-size guarantees."}
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"checkpoint": str(checkpoint_path), "test_brier": report["test"]["brier"],
                      "calibrated_test_brier": report["test_calibrated"]["brier"] if report["test_calibrated"] else None}))
    return report


def evaluate(args):
    import torch
    torch.set_num_threads(min(4, torch.get_num_threads()))
    artifact = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    episodes, splits = corpus(args.data, artifact["history"], calibrate=artifact.get("calibration_requested", False))
    if {Path(e["path"]).name: e["sha256"] for e in episodes} != artifact["files"]:
        raise ValueError("Evaluation corpus differs from the frozen training split manifest")
    model = make_model(artifact["channels"]); model.load_state_dict(artifact["state_dict"])
    if "evaluation_version" in artifact:
        manifest = split_hashes(episodes, splits)
        if splits != artifact["splits"] or manifest["split_hashes"] != artifact["split_hashes"] or manifest["corpus_sha256"] != artifact["corpus_sha256"]:
            raise ValueError("Evaluation split hashes differ from the frozen training manifest")
        if artifact["calibration_requested"] and artifact["calibrator"] is None:
            raise ValueError("Calibration was requested but its frozen parameters are missing")
        result = final_evaluation(model, episodes, artifact, torch, "cpu", artifact.get("evaluation_batch_size", 4))
    else:
        data = examples(episodes, artifact["splits"]["test"], artifact["history"], np.array(artifact["mean"]), np.array(artifact["std"]))
        result = evaluate_model(model, data, torch, "cpu", 4)
    print(json.dumps(result, indent=2, allow_nan=False))
    return result


def make_smoke(directory, event_count=6):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    if list(directory.glob("*.npz")):
        raise ValueError("Smoke output already has episodes; use a fresh directory")
    yy, xx = np.mgrid[:16, :16]
    for event in range(event_count):
        start = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=event * 2)
        times = [start + timedelta(minutes=i * 5) for i in range(8)]
        values = np.array([np.exp(-((xx - (4 + i * .5)) ** 2 + (yy - (5 + event)) ** 2) / 8) * 40 for i in range(8)], dtype=np.float32)[:, None]
        target = np.array([((xx - (5 + i * .5)) ** 2 + (yy - (5 + event)) ** 2) < 9 for i in range(8)], dtype=np.float32)
        meta = {"event_id": f"synthetic-{event}", "channels": ["synthetic_echo"], "units": ["arbitrary"],
                "target_definition": "Synthetic moving-blob occurrence; not observed lightning", "horizon_minutes": 10,
                "availability_mode": "assumed_research_latency", "provenance": "Generated smoke fixtures seedless-blob-v1",
                "scope": "synthetic_smoke_only", "grid": {"crs": "synthetic pixel coordinates", "shape": [16, 16]}}
        np.savez_compressed(directory / f"episode-{event}.npz", values=values, masks=np.ones_like(values, dtype=bool),
                            times_utc=np.array([t.isoformat() for t in times]), available_at_utc=np.array([[t.isoformat()] for t in times]),
                            targets=target, coverage=np.ones_like(target, dtype=bool),
                            target_end_utc=np.array([(t + timedelta(minutes=10)).isoformat() for t in times]), metadata_json=np.array(json.dumps(meta)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate"); validate.add_argument("--data", required=True); validate.add_argument("--history", type=int, default=3)
    validate.add_argument("--calibrate", action="store_true", help="Validate the four-way calibration split, requiring at least eight event groups")
    fit = sub.add_parser("train"); fit.add_argument("--data", required=True); fit.add_argument("--output", required=True)
    fit.add_argument("--history", type=int, default=3); fit.add_argument("--epochs", type=int, default=5)
    fit.add_argument("--batch-size", type=int, default=4); fit.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    fit.add_argument("--calibrate", action="store_true", help="Fit temperature only on a separate held-out calibration split")
    fit.add_argument("--initialize-from", help="Fine-tune a compatible local compact ConvLSTM checkpoint; preserve its normalizer and exclude prior exposure from new held-out groups")
    test = sub.add_parser("evaluate"); test.add_argument("--data", required=True); test.add_argument("--checkpoint", required=True)
    smoke = sub.add_parser("smoke"); smoke.add_argument("--output", required=True)
    smoke.add_argument("--calibrate", action="store_true", help="Generate eight synthetic groups and exercise held-out calibration")
    args = parser.parse_args()
    try:
        if hasattr(args, "history") and args.history < 2 or hasattr(args, "epochs") and args.epochs < 1 or hasattr(args, "batch_size") and args.batch_size < 1:
            raise ValueError("History >=2, epochs >=1 and batch size >=1 are required")
        if args.command == "validate":
            episodes, splits = corpus(args.data, args.history, calibrate=args.calibrate)
            mean, std = normalizer(episodes, splits["train"], args.history)
            sizes = {key: len(examples(episodes, ids, args.history, mean, std)) for key, ids in splits.items()}
            print(json.dumps({"episodes": len(episodes), "splits": splits, "examples": sizes, "scope": episodes[0]["meta"]["scope"]}, indent=2))
        elif args.command == "train":
            train(args)
        elif args.command == "evaluate":
            evaluate(args)
        else:
            base = Path(args.output); make_smoke(base / "episodes", event_count=8 if args.calibrate else 6)
            args.data, args.output, args.history, args.epochs, args.batch_size, args.device = str(base / "episodes"), str(base / "run"), 3, 1, 4, "cpu"
            train(args)
    except (ValueError, KeyError, ImportError, OSError, zipfile.BadZipFile) as error:
        parser.exit(2, f"Training input/setup error: {error}\n")


if __name__ == "__main__":
    main()

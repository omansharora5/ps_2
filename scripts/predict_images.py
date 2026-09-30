"""Run a compatible compact ConvLSTM on one validated episode issue index.

This is a local research inference command, not a live NCR weather service.
No target values, future frames, or future-arriving measurements enter inference.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.train_images import causal_input_mask, checkpoint_normalizer, load_episode, make_model


def temperature_for(artifact):
    """Apply only a fitted calibrator tied to an independent frozen split."""
    calibrator = artifact.get("calibrator")
    if not artifact.get("calibrated", False):
        return 1., "uncalibrated"
    if not isinstance(calibrator, dict) or calibrator.get("method") != "regularized_temperature_v1" or calibrator.get("fit_status") != "fitted":
        raise ValueError("Artifact claims calibration without a supported fitted calibrator")
    temperature = float(calibrator.get("temperature", float("nan")))
    if not np.isfinite(temperature) or not .05 <= temperature <= 20:
        raise ValueError("Artifact calibration temperature is invalid")
    splits = artifact.get("splits", {})
    ids, calibration_ids = calibrator.get("fit_event_ids"), splits.get("calibration")
    if not artifact.get("calibration_requested") or not isinstance(ids, list) or not ids or not isinstance(calibration_ids, list):
        raise ValueError("Artifact calibration has no frozen independent event split")
    if any(not isinstance(value, str) or not value for value in ids + calibration_ids):
        raise ValueError("Calibration event identifiers are invalid")
    if len(ids) != len(set(ids)) or set(ids) != set(calibration_ids):
        raise ValueError("Calibrator event identifiers differ from the frozen calibration split")
    other_ids = {value for key in ("train", "validation", "test") for value in splits.get(key, [])}
    inherited_ids = set((artifact.get("initialization") or {}).get("exposure_event_ids", []))
    if set(ids) & (other_ids | inherited_ids):
        raise ValueError("Calibration events overlap model selection or initializer exposure")
    return temperature, "held_out_temperature_fitted; reliability still requires independent evaluation"


def predict_episode(artifact, episode, index, torch):
    history = artifact.get("history")
    if type(history) is not int or history < 2:
        raise ValueError("Checkpoint requires an integer history >= 2")
    if type(index) is not int or not history - 1 <= index < len(episode["times"]):
        raise ValueError("Issue index must have the checkpoint's full history and exist in the episode")
    mean, std = checkpoint_normalizer(artifact, episode, history)
    section = slice(index - history + 1, index + 1)
    mask = causal_input_mask(episode, index, history)
    support = mask.any(axis=(0, 1))
    if not support.any():
        raise ValueError("No causal observations are available at this issue time; abstaining")
    values = (episode["values"][section] - mean[None, :, None, None]) / std[None, :, None, None]
    inputs = np.concatenate([np.where(mask, values, 0), mask.astype(np.float32)], axis=1).astype(np.float32)
    model = make_model(artifact["channels"])
    try:
        model.load_state_dict(artifact["state_dict"], strict=True)
    except (KeyError, RuntimeError) as error:
        raise ValueError("Checkpoint weights do not match the declared compact architecture") from error
    model.eval()
    temperature, calibration_status = temperature_for(artifact)
    with torch.no_grad():
        logits = model(torch.from_numpy(inputs[None]))[0].cpu().numpy()
    if not np.isfinite(logits).all():
        raise ValueError("Checkpoint produced nonfinite logits")
    probabilities = np.exp(-np.logaddexp(0., -logits / temperature)).astype(np.float32)
    probabilities[~support] = np.nan
    utc = lambda seconds: datetime.fromtimestamp(float(seconds), timezone.utc).isoformat().replace("+00:00", "Z")
    metadata = {"schema_version": 1, "architecture": artifact["architecture"],
                "issued_at_utc": utc(episode["times"][index]), "valid_until_utc": utc(episode["ends"][index]),
                "horizon_minutes": artifact["metadata"]["horizon_minutes"], "issue_index": index,
                "target_definition": artifact["metadata"]["target_definition"], "grid": artifact["metadata"]["grid"],
                "channels": artifact["metadata"]["channels"], "units": artifact["metadata"]["units"],
                "scope": episode["meta"]["scope"], "training_scope": artifact["metadata"].get("scope"),
                "availability_mode": episode["meta"]["availability_mode"],
                "episode_sha256": episode["sha256"], "event_id": episode["meta"]["event_id"],
                "calibration_status": calibration_status, "temperature": temperature,
                "input_valid_fraction": float(mask.mean()), "input_supported_pixels": int(support.sum()),
                "cadence_verified": "input_contract" in artifact, "automatic_alert": False,
                "limitations": "Research inference only; input support is not outcome coverage or certainty. Missing cells are NaN, not dry. No operational NCR skill established."}
    return {"probabilities": probabilities, "input_support": support, "metadata": metadata}


def predict(checkpoint, episode_path, index, output):
    import torch
    torch.set_num_threads(min(4, torch.get_num_threads()))
    checkpoint, output = Path(checkpoint), Path(output)
    if output.suffix != ".npz":
        raise ValueError("Output must be a new .npz forecast artifact")
    if output.exists():
        raise ValueError("Forecast output already exists; use a new issue/revision filename")
    artifact = torch.load(checkpoint, map_location="cpu", weights_only=True)
    history = artifact.get("history")
    if type(history) is not int or history < 2:
        raise ValueError("Checkpoint requires an integer history >= 2")
    episode = load_episode(Path(episode_path), history)
    result = predict_episode(artifact, episode, index, torch)
    result["metadata"]["checkpoint_sha256"] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Publish a complete file atomically without overwriting another actor's forecast.
    fd, temporary = tempfile.mkstemp(prefix=".forecast-", suffix=".part", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            np.savez_compressed(handle, probabilities=result["probabilities"], input_support=result["input_support"],
                                metadata_json=np.array(json.dumps(result["metadata"], sort_keys=True, allow_nan=False)))
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    print(json.dumps({"output": str(output), **result["metadata"]}, allow_nan=False))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--episode", required=True, help="A validated aligned episode NPZ; raw provider files are not episodes")
    parser.add_argument("--index", type=int, required=True, help="Issue/acquisition index; only data available at this index's UTC time can enter inference")
    parser.add_argument("--output", required=True, help="New NPZ path; existing forecasts are never overwritten")
    args = parser.parse_args()
    try:
        predict(args.checkpoint, args.episode, args.index, args.output)
    except (ValueError, KeyError, TypeError, ImportError, OSError, RuntimeError, zipfile.BadZipFile) as error:
        parser.exit(2, f"Inference input/setup error: {error}\n")


if __name__ == "__main__":
    main()

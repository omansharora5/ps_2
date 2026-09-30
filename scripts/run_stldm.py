"""Optional pinned STLDM inference on its supplied normalized reference example.

This does not train a model or publish a weather/lightning forecast. Preparation
downloads author source and weights; inference performs no network access.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import random
import subprocess
import sys
import time
import urllib.request

import numpy as np


SOURCE_URL = "https://github.com/sqfoo/stldm_official.git"
SOURCE_COMMIT = "49b23485734b5c00a2388febb657543afb12d6cf"
MODEL_REVISION = "cdb543e4f42ee754cb88f2c15abb74f0f987c98b"
WEIGHT_SHA256 = "ed003bc16f59ac7f88ea5b81de8809b0ad28ceb4b0f8bd28c47907e958eafbbd"
WEIGHT_BYTES = 324054852
ARTIFACT_HASHES = {
    "model.safetensors": WEIGHT_SHA256,
    "config.json": "d14fa3e23cf183ea18b77220164474c72d624346f06e4db7ec585c795ada75cf",
    "LICENSE": "cde0de39ebd25c1e130d1a88cfacb37c6bcce051e7314f252d0d15364495632f",
}
MODEL_BASE = f"https://huggingface.co/sqfoo/STLDM_official/resolve/{MODEL_REVISION}/"
REFERENCE_METADATA = {
    "scope": "official_reference_example_only",
    "units": "normalized_hko_reference",
    "source_url": f"https://github.com/sqfoo/stldm_official/blob/{SOURCE_COMMIT}/data/sample_data.npy",
    "timestamps_status": "not_supplied",
    "coverage_status": "not_supplied",
    "physical_grid_status": "not_supplied",
}


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(checkout, *arguments):
    return subprocess.run(["git", "-C", str(checkout), *arguments], capture_output=True, text=True, check=True).stdout.strip()


def verify_checkout(checkout):
    checkout = Path(checkout).resolve()
    if git(checkout, "rev-parse", "HEAD") != SOURCE_COMMIT:
        raise ValueError("Source checkout is not the pinned STLDM commit; run prepare in a new directory")
    if git(checkout, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Pinned STLDM tracked files have local changes")
    # Untracked Python modules could shadow tracked imports despite a clean diff.
    tracked = set(git(checkout, "ls-files", "stldm").splitlines())
    for path in (checkout / "stldm").rglob("*.py"):
        if path.relative_to(checkout).as_posix() not in tracked:
            raise ValueError("Untracked Python source is present in the STLDM package")
    return checkout


def download(url, destination, max_bytes, expected_sha256=None):
    destination = Path(destination)
    if destination.exists():
        if destination.stat().st_size > max_bytes or expected_sha256 and file_hash(destination) != expected_sha256:
            raise ValueError(f"Cached {destination.name} differs from the pinned artifact")
        return
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "VAJRA-STLDM-reference/1"})
    with urllib.request.urlopen(request, timeout=30) as source, temporary.open("wb") as output:
        size = 0
        while chunk := source.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                raise ValueError(f"Download exceeds the declared size budget for {destination.name}")
            output.write(chunk)
    if expected_sha256 and file_hash(temporary) != expected_sha256:
        raise ValueError(f"Downloaded {destination.name} failed its pinned SHA-256 check")
    temporary.replace(destination)


def prepare(args):
    checkout = Path(args.checkout).resolve()
    if not checkout.exists():
        subprocess.run(["git", "clone", "--no-checkout", SOURCE_URL, str(checkout)], check=True)
        subprocess.run(["git", "-C", str(checkout), "checkout", "--detach", SOURCE_COMMIT], check=True)
    verify_checkout(checkout)
    cache = Path(args.cache); cache.mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "LICENSE"):
        download(MODEL_BASE + name, cache / name, 100_000, ARTIFACT_HASHES[name])
    print("Downloading/verifying the 324 MB pinned safetensors checkpoint", flush=True)
    download(MODEL_BASE + "model.safetensors", cache / "model.safetensors", WEIGHT_BYTES, WEIGHT_SHA256)
    manifest = {"source_commit": SOURCE_COMMIT, "model_revision": MODEL_REVISION,
                "files": {name: file_hash(cache / name) for name in ("config.json", "LICENSE", "model.safetensors")}}
    # Existing manifests cannot silently bless a changed config or licence.
    manifest_path = cache / "manifest.json"
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
        raise ValueError("Cache files differ from their recorded preparation manifest")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "prepared", "checkout": str(checkout), "cache": str(cache)}))


def partition_reference(values, metadata):
    if metadata != REFERENCE_METADATA:
        raise ValueError("Only the declared normalized official reference metadata is supported; no dBZ/lightning/live inputs")
    values = np.asarray(values)
    if values.ndim != 5 or values.shape[0] != 1 or values.shape[1] != 25 or values.shape[2] != 1:
        raise ValueError("Reference requires one [1,25,1,H,W] sequence: five past and twenty future images")
    if not 32 <= values.shape[3] <= 1024 or not 32 <= values.shape[4] <= 1024:
        raise ValueError("Reference image geometry is outside the bounded input contract")
    if values.dtype.kind not in "fiu" or not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("Reference pixels must be finite normalized values in [0,1]")
    return values[:, :5].astype(np.float32, copy=True), values[:, 5:25].astype(np.float32, copy=True)


def image_scores(prediction, truth, last_observed):
    if prediction.shape != truth.shape or last_observed.shape != truth[:, :1].shape:
        raise ValueError("Reference score arrays have incompatible shapes")
    valid = np.isfinite(prediction) & np.isfinite(truth) & np.isfinite(last_observed)
    if not valid.any():
        raise ValueError("No finite image pairs available for reference scoring")
    residual = prediction[valid].astype(float) - truth[valid]
    persistence = np.broadcast_to(last_observed, truth.shape)[valid].astype(float) - truth[valid]
    return {"scope": "Finite normalized image values only; meteorological coverage is unknown",
            "samples": int(valid.sum()), "stldm_mae": float(np.abs(residual).mean()),
            "stldm_mse": float(np.square(residual).mean()),
            "persistence_mae": float(np.abs(persistence).mean()), "persistence_mse": float(np.square(persistence).mean())}


def run_inference(args, report):
    started = time.perf_counter()
    checkout = verify_checkout(args.checkout)
    cache = Path(args.cache)
    manifest = json.loads((cache / "manifest.json").read_text())
    if manifest.get("source_commit") != SOURCE_COMMIT or manifest.get("model_revision") != MODEL_REVISION:
        raise ValueError("Cache manifest has an incompatible source or checkpoint revision")
    for name in ("config.json", "LICENSE", "model.safetensors"):
        actual = file_hash(cache / name)
        if actual != manifest["files"][name] or actual != ARTIFACT_HASHES[name]:
            raise ValueError(f"Cache integrity failure: {name}")
    config = json.loads((cache / "config.json").read_text())
    if config["vp_param"]["shape_in"] != [5, 1, 128, 128] or config["vp_param"]["shape_out"] != [20, 1, 128, 128]:
        raise ValueError("Checkpoint shape is not the supported HKO reference configuration")
    if config["timesteps"] != 50 or config["sampling_timesteps"] != 20:
        raise ValueError("Checkpoint sampling schedule differs from the pinned reference")
    sample_path = checkout / "data/sample_data.npy"
    if sample_path.stat().st_size > 100_000_000:
        raise ValueError("Supplied reference example exceeds the 100 MB load budget")
    sample = np.load(sample_path, mmap_mode="r", allow_pickle=False)
    if sample.ndim != 5 or sample.shape[0] < 1:
        raise ValueError("Supplied reference example has an invalid batch layout")
    past, future = partition_reference(sample[:1], REFERENCE_METADATA)
    report.update(source_commit=SOURCE_COMMIT, model_revision=MODEL_REVISION, checkpoint_sha256=WEIGHT_SHA256,
                  cache_manifest=manifest, input_sha256=file_hash(sample_path), source_shape=list(sample.shape),
                  selected_example=0, metadata=REFERENCE_METADATA, sampling={"diffusion_steps": 50, "sampling_steps": 20,
                  "cfg_strength": 1.0, "members": 1, "seed": args.seed})
    import torch
    from safetensors.torch import load_file
    torch.set_num_threads(args.threads)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA is unavailable; the CPU reference path remains supported")
    sys.path.insert(0, str(checkout))
    from stldm.stldm_hf import GaussianDiffusion, guidance_scheduler
    model = GaussianDiffusion(**config)
    model.load_state_dict(load_file(str(cache / "model.safetensors"), device="cpu"), strict=True)
    model.setup_guidance(guidance_scheduler(config["timesteps"], 1.0))
    model.to(args.device).eval()

    def resize(values):
        tensor = torch.from_numpy(values)
        b, t, c, h, w = tensor.shape
        return torch.nn.functional.interpolate(tensor.reshape(b * t, c, h, w), size=(128, 128),
                                                mode="bilinear", align_corners=False).reshape(b, t, c, 128, 128)

    x = resize(past).to(args.device)
    # Future images are prepared only for post-inference scoring, never model input.
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    if args.device == "cuda":
        torch.cuda.reset_peak_memory_stats(); torch.cuda.synchronize()
    report["environment"] = {"python": platform.python_version(), "torch": str(torch.__version__),
                             "device": args.device, "threads": args.threads,
                             "packages": {name: importlib.metadata.version(name) for name in ("numpy", "einops", "huggingface_hub", "safetensors", "tqdm")}}
    print("Model loaded with strict weights; generating one 20-step reference member", flush=True)
    inference_start = time.perf_counter()
    with torch.inference_mode():
        prediction = model(x).cpu().numpy()
    if args.device == "cuda":
        torch.cuda.synchronize()
    inference_seconds = time.perf_counter() - inference_start
    if prediction.shape != (1, 20, 1, 128, 128) or not np.isfinite(prediction).all() or ((prediction < 0) | (prediction > 1)).any():
        raise ValueError("Official model output violates the supported shape or finite normalized-value contract")
    truth = resize(future).numpy()
    observed = x.cpu().numpy()
    destination = Path(args.output) / "predictions.npz"
    np.savez_compressed(destination, prediction=prediction, past=observed, reference_future=truth)
    report.update(status="succeeded", output_shape=list(prediction.shape), metrics=image_scores(prediction, truth, observed[:, -1:]),
                  model_inference_seconds=round(inference_seconds, 6), total_seconds=round(time.perf_counter() - started, 6),
                  peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated() if args.device == "cuda" else None,
                  cpu_peak_memory="not_measured", predictions_sha256=file_hash(destination),
                  model_parameter_count=sum(parameter.numel() for parameter in model.parameters()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "infer"):
        command = sub.add_parser(name)
        command.add_argument("--checkout", default="tools/stldm")
        command.add_argument("--cache", default="data/training_runs/stldm-reference/cache")
        if name == "infer":
            command.add_argument("--output", required=True)
            command.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
            command.add_argument("--threads", type=int, default=4)
            command.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args)
            return
        if not 1 <= args.threads <= 32 or not 0 <= args.seed < 2**32:
            raise ValueError("Use 1..32 threads and a seed in [0,2**32)")
        output = Path(args.output)
        if output.exists() and any(output.iterdir()):
            raise ValueError("Output directory is not empty; choose a new run directory")
        output.mkdir(parents=True, exist_ok=True)
        report = {"status": "not_executed", "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                  "scope": "Official supplied-example reference inference, not India/lightning validation",
                  "limitations": ["One supplied example and one generated member cannot establish forecast skill or calibration.",
                                  "Example timestamps, physical grid and observation coverage are not supplied.",
                                  "Normalized pixel errors are not dBZ, rain-rate or lightning probability scores.",
                                  "No checkpoint is loaded into the app or promoted into production."]}
        try:
            run_inference(args, report)
        except Exception as error:
            report.update(status="failed", error_type=type(error).__name__, error=str(error))
            raise
        finally:
            (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps({key: report[key] for key in ("status", "output_shape", "model_inference_seconds", "metrics")}))
    except (ValueError, KeyError, ImportError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"STLDM reference error: {error}\n")


if __name__ == "__main__":
    main()

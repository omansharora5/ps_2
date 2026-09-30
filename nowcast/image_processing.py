"""Causal image experiments on a pinned historical radar sequence, never lightning."""

import hashlib
import json

import numpy as np

from .numerics import motion, translate
from .real_data import EXPECTED, load_sample
from .verification import verify

METHODS = [
    {"id": "persistence", "label": "Persistence", "description": "Keep the most recent processed radar image fixed."},
    {"id": "global_translation", "label": "Global translation", "description": "Estimate one motion vector from two past images and advect linear reflectivity."},
    {"id": "dense_optical_flow", "label": "Dense optical flow", "description": "Experimental Horn-Schunck local motion from two past images; frozen-velocity extrapolation."},
]
PREPROCESSING = [{"id": "raw", "label": "Raw decoded radar"},
                 {"id": "despeckle", "label": "Remove isolated echo pixels"},
                 {"id": "smooth", "label": "3 x 3 smoothing in linear reflectivity"}]
VERSION = "radar-image-lab-v2"


def to_z(dbz, no_echo_mask=None):
    z = np.where(np.isfinite(dbz), 10.0 ** (dbz / 10.0), np.nan)
    return z if no_echo_mask is None else np.where(no_echo_mask, 0.0, z)


def to_dbz(z):
    return np.where(np.isfinite(z) & (z >= 0),
                    np.where(z > 0, 10 * np.log10(np.maximum(z, np.finfo(float).tiny)), -10.0), np.nan)


def segment(field, threshold=20, minimum_pixels=4):
    active = np.isfinite(field) & (field >= threshold)
    labels = np.zeros(field.shape, dtype=float)
    labels[~np.isfinite(field)] = np.nan
    seen = np.zeros(field.shape, dtype=bool)
    objects = []
    for y, x in zip(*np.where(active)):
        if seen[y, x]:
            continue
        todo, points = [(int(y), int(x))], []
        seen[y, x] = True
        while todo:
            py, px = todo.pop()
            points.append((py, px))
            for ny, nx in ((py - 1, px), (py + 1, px), (py, px - 1), (py, px + 1)):
                if 0 <= ny < field.shape[0] and 0 <= nx < field.shape[1] and active[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    todo.append((ny, nx))
        if len(points) >= minimum_pixels:
            coords = np.asarray(points)
            identifier = len(objects) + 1
            labels[coords[:, 0], coords[:, 1]] = identifier
            objects.append({"id": identifier, "x": float(coords[:, 1].mean()), "y": float(coords[:, 0].mean()),
                            "pixels": len(points), "peak": float(field[coords[:, 0], coords[:, 1]].max())})
    return labels, objects


def preprocess_z(field, method):
    z = to_z(field, no_echo_mask=field == -10)
    if method == "raw":
        return z
    if method == "despeckle":
        labels, _ = segment(field)
        result = z.copy()
        result[np.isfinite(field) & (field >= 20) & (labels == 0)] = 0
        return result
    if method != "smooth":
        raise ValueError("Unknown preprocessing method")
    total, count = np.zeros_like(z), np.zeros_like(z)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            shifted = translate(z, dy, dx)
            valid = np.isfinite(shifted)
            total += np.where(valid, shifted, 0)
            count += valid
    result = np.divide(total, count, out=np.zeros_like(total), where=count > 0)
    result[~np.isfinite(field)] = np.nan
    return result


def preprocess(field, method):
    return to_dbz(preprocess_z(field, method))


def dense_backward_flow(previous, current, iterations=60, alpha=0.12):
    """Current-to-previous Horn-Schunck flow with fixed, untuned parameters."""
    valid = np.isfinite(previous) & np.isfinite(current)
    support = valid.copy()
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        support &= translate(valid.astype(float), dy, dx, fill=0) == 1
    a = np.where(valid, np.clip((current + 10) / 70, 0, 1), 0)
    b = np.where(valid, np.clip((previous + 10) / 70, 0, 1), 0)
    iy, ix = np.gradient((a + b) / 2)
    it = b - a
    u, v = np.zeros_like(a), np.zeros_like(a)
    for _ in range(iterations):
        up = np.pad(u, 1, mode="edge")
        vp = np.pad(v, 1, mode="edge")
        ub = (up[1:-1, :-2] + up[1:-1, 2:] + up[:-2, 1:-1] + up[2:, 1:-1]) / 4
        vb = (vp[1:-1, :-2] + vp[1:-1, 2:] + vp[:-2, 1:-1] + vp[2:, 1:-1]) / 4
        correction = (ix * ub + iy * vb + it) / (alpha * alpha + ix * ix + iy * iy)
        u = np.where(support, ub - ix * correction, 0)
        v = np.where(support, vb - iy * correction, 0)
    return v, u, support


def extrapolate(history, method, preprocessing, horizon):
    if horizon not in (5, 10, 15, 20):
        raise ValueError("Only +5/+10/+15/+20 minute held-out images are available")
    if history.shape[0] != 2:
        raise ValueError("Image experiment requires exactly two causal input frames")
    previous_z, current_z = [preprocess_z(frame, preprocessing) for frame in history]
    previous, current = to_dbz(previous_z), to_dbz(current_z)
    details = {"measurement_space": "linear reflectivity Z for smoothing and spatial resampling",
               "no_echo_sentinel_dbz": -10,
               "no_echo_note": "Source -10 denotes no echo. Processed/forecast -10 can also be positive Z; use the separate no_echo masks.",
               "input_frames": 2, "input_step_minutes": 5}
    if method == "persistence":
        forecast_z = current_z.copy()
    elif method == "global_translation":
        dy, dx = motion(previous, current, radius=3)
        forecast_z = translate(current_z, dy * horizon / 5, dx * horizon / 5)
        details["motion_pixels_per_frame"] = {"dy": dy, "dx": dx}
    elif method == "dense_optical_flow":
        backward_y, backward_x, support = dense_backward_flow(previous, current)
        forecast_z = translate(current_z, -backward_y * horizon / 5, -backward_x * horizon / 5)
        forecast_z[~support] = np.nan
        details.update({"flow": "Horn-Schunck current-to-previous, frozen local velocity",
                        "iterations": 60, "alpha": 0.12, "valid_flow_pixels": int(support.sum())})
    else:
        raise ValueError("Unknown extrapolation method")
    return current, to_dbz(forecast_z), details, current_z, forecast_z


def grid_json(grid):
    return [[round(float(v), 4) if np.isfinite(v) else None for v in row] for row in grid]


def image_metrics(prediction, truth, common, intensity):
    echo_p = np.where(np.isfinite(prediction), prediction >= 20, np.nan)
    echo_y = np.where(np.isfinite(truth), truth >= 20, np.nan)
    score = verify(echo_p, echo_y, mask=common)
    error = prediction[intensity] - truth[intensity]
    score.update({"mae_dbz": float(np.abs(error).mean()) if error.size else None,
                  "rmse_dbz": float(np.sqrt((error ** 2).mean())) if error.size else None,
                  "intensity_samples": int(error.size),
                  "intensity_note": "dBZ errors require positive linear reflectivity in both forecasts and truth; valid weak echoes below -10 dBZ remain included. Binary echo scores retain no-echo pixels."})
    return score


def image_run(method="global_translation", preprocessing="smooth", horizon=10):
    fields, timestamps, lat, lon, manifest = load_sample()
    history = fields[:2].copy()
    processed, forecast, details, processed_z, forecast_z = extrapolate(history, method, preprocessing, horizon)
    truth = fields[1 + horizon // 5].copy()
    original = history[-1]
    common = np.isfinite(forecast) & np.isfinite(original) & np.isfinite(truth)
    intensity = common & (forecast_z > 0) & (original != -10) & (truth != -10)
    no_echo = {"original": original == -10, "processed": processed_z == 0,
               "forecast": forecast_z == 0, "truth": truth == -10}
    labels, objects = segment(processed)
    identity = json.dumps([VERSION, method, preprocessing, horizon, EXPECTED], sort_keys=True)
    return {"id": hashlib.sha256(identity.encode()).hexdigest()[:20], "version": VERSION,
            "method": method, "preprocessing": preprocessing, "horizon": horizon,
            "mode": "observed_radar_image", "scope": "Two past French radar frames and one held-out future; not Indian or lightning validation",
            "target": "Deterministic radar echo >=20 dBZ at valid time; not a lightning probability",
            "issued_at": timestamps[1], "valid_at": timestamps[1 + horizon // 5], "units": "dBZ",
            "time_note": "Archive timestamps; source timezone remains unverified",
            "grid": {"width": lon.shape[1], "height": lat.shape[0], "west": float(lon.min()), "east": float(lon.max()),
                     "south": float(lat.min()), "north": float(lat.max()), "row_direction": "south" if lat[0, 0] > lat[-1, 0] else "north"},
            "layers": {k: grid_json(v) for k, v in {"original": original, "processed": processed, "forecast": forecast, "truth": truth, "segments": labels}.items()},
            "masks": {k: np.isfinite(v).astype(int).tolist() for k, v in {"original": original, "processed": processed, "forecast": forecast, "truth": truth}.items()} | {"evaluation": common.astype(int).tolist(), "intensity_evaluation": intensity.astype(int).tolist(), "no_echo": {k: v.astype(int).tolist() for k, v in no_echo.items()}},
            "metrics": {"selected": image_metrics(forecast, truth, common, intensity),
                        "persistence": image_metrics(original, truth, common, intensity)},
            "segmentation": {"threshold_dbz": 20, "minimum_pixels": 4, "objects": objects},
            "processing": details,
            "provenance": {"provider": "Meteo-France / MeteoNet", "source_sha256": EXPECTED,
                           "source_url": "https://meteofrance.github.io/meteonet/", "manifest": manifest},
            "limitations": ["Small single-case image experiment; scores do not establish general forecast skill.",
                            "Despeckling is an image heuristic that can remove real small echoes; it is not instrument QC.",
                            "Dense flow assumes approximate brightness constancy and smooth motion; growth/decay violates these assumptions.",
                            "Binary echo metrics share a common valid mask; intensity errors also exclude no-echo sentinels."]}

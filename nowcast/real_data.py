import hashlib
import json
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np

from .numerics import motion, translate


DATA = Path(__file__).resolve().parents[1] / "data" / "external"
EXPECTED = {
    "reflectivity_new_SE_2018_12.2.npz": "ed83a05b302dbd13b1ee6872bdb10e7a2da5940151c0f33fb393431997be5719",
    "radar_coords_SE.npz": "311531ff06b0fffbd970eba1360c916c49c86afbcb70c77839668976d9a31287",
}


def check_sequence(timestamps, step_minutes=5):
    times = [datetime.fromisoformat(value) for value in timestamps]
    if any(b - a != timedelta(minutes=step_minutes) for a, b in zip(times, times[1:])):
        raise ValueError("Non-contiguous observations cannot be treated as consecutive frames")


@lru_cache(maxsize=1)
def load_sample():
    for name, expected in EXPECTED.items():
        path = DATA / name
        if not path.exists():
            raise FileNotFoundError("Run python scripts/fetch_sample.py to fetch the historical radar example")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Sample checksum mismatch: {name}")
    manifest = json.loads((DATA / "meteonet_manifest.json").read_text(encoding="utf-8-sig"))
    # Object/pickled datetime arrays are never loaded. Dates are pinned to this verified file.
    timestamps = [f"2018-12-19 10:{minute:02d}:00" for minute in (10, 15, 20, 25, 30, 35)]
    check_sequence(timestamps)
    with np.load(DATA / "reflectivity_new_SE_2018_12.2.npz", allow_pickle=False) as archive:
        raw = archive["data"][14:20, ::3, ::3].astype(float)
    fields = raw / 10.0
    fields[raw == -200] = np.nan
    fields[raw == -100] = -10.0  # computational no-echo sentinel, not a measured dBZ
    with np.load(DATA / "radar_coords_SE.npz", allow_pickle=False) as coords:
        lat, lon = coords["lats"][::3, ::3], coords["lons"][::3, ::3]
    return fields, timestamps, lat, lon, manifest


def replay(horizon):
    if horizon not in (5, 10, 15, 20):
        raise ValueError("The observed sample supports only +5, +10, +15 and +20 minutes")
    fields, timestamps, lat, lon, manifest = load_sample()
    observations = fields[:2].copy()
    velocity = motion(observations[0], observations[1], radius=3)
    shifted = translate(observations[-1], velocity[0] * horizon / 5, velocity[1] * horizon / 5)
    def echo(field):
        return np.where(np.isfinite(field), (field >= 20).astype(float), np.nan)
    # Truth is selected only after extrapolation. No simulator-trained model is applied here.
    truth = echo(fields[1 + horizon // 5])
    return {"current": observations[-1], "persistence": echo(observations[-1]), "advection": echo(shifted),
            "truth": truth, "velocity": velocity, "lat": lat, "lon": lon,
            "issued_at": timestamps[1], "valid_at": timestamps[1 + horizon // 5], "manifest": manifest}

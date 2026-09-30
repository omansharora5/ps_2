import hashlib
import json
from pathlib import Path

import numpy as np

from .numerics import motion, neighborhood, translate
from .observations import HORIZONS, SOURCES, Snapshot


ARTIFACT = Path(__file__).resolve().parents[1] / "data" / "model.json"
FEATURE_NAMES = ["bias", "advected_radar", "latest_radar", "radar_change", "advected_cold_cloud",
                 "cloud_cooling", "advected_lightning", "recent_lightning", "cape_context",
                 "radar_present", "satellite_present", "lightning_present", "nwp_present",
                 "radar_squared", "cloud_squared"]


def sigmoid(values):
    return 1.0 / (1.0 + np.exp(-np.clip(values, -30, 30)))


def features(observations: Snapshot, horizon: int) -> tuple[np.ndarray, tuple[float, float]]:
    if horizon not in HORIZONS:
        raise ValueError("Unsupported simulated lead time")
    fields, present = observations.fields, observations.available
    shape = fields["radar"].shape[1:]
    zero = np.zeros(shape)
    source = "radar" if present["radar"] else "satellite" if present["satellite"] else "lightning" if present["lightning"] else None
    velocity = motion(fields[source][-2], fields[source][-1]) if source else (0.0, 0.0)
    dy, dx = (v * horizon / 5 for v in velocity)
    def field(name, index=-1):
        return fields[name][index] if present[name] else zero
    r = np.clip(field("radar") / 60, 0, 1)
    ra = translate(r, dy, dx, fill=0) if present["radar"] else zero
    rg = np.clip((field("radar") - field("radar", -2)) / 10, -2, 2)
    cloud = np.clip((285 - field("satellite")) / 70, 0, 1) if present["satellite"] else zero
    ca = translate(cloud, dy, dx, fill=0)
    cooling = np.clip((field("satellite", -2) - field("satellite")) / 10, -2, 2)
    recent = neighborhood((fields["lightning"].sum(axis=0) > 0).astype(float)) if present["lightning"] else zero
    la = translate(recent, dy, dx, fill=0)
    cape = field("nwp") / 3000
    arrays = [np.ones(shape), ra, r, rg, ca, cooling, la, recent, cape]
    arrays += [np.full(shape, float(present[s])) for s in SOURCES]
    arrays += [ra**2, ca**2]
    return np.stack(arrays, axis=-1).astype(np.float32), velocity


def targets(event, step, horizon):
    end = step + horizon // 5
    if end >= len(event.timestamps):
        raise ValueError("Future truth is unavailable")
    lightning = neighborhood((event.lightning[end - 2:end + 1].sum(axis=0) > 0).astype(float))
    return {"storm": (event.radar[end] >= 35).astype(float), "lightning": lightning}


def predict(observations: Snapshot, horizon: int, artifact: dict) -> dict:
    x, velocity = features(observations, horizon)
    spatial_support = any(observations.available[s] for s in ("radar", "satellite", "lightning"))
    outputs = {}
    for hazard in ("storm", "lightning"):
        model = artifact["heads"][f"{hazard}-{horizon}"]
        outputs[hazard] = sigmoid((x @ np.array(model["weights"])) / model["temperature"]) if spatial_support else np.full(x.shape[:2], np.nan)
    fields = observations.fields
    dy, dx = (v * horizon / 5 for v in velocity)
    if observations.available["radar"]:
        persisted_storm = (fields["radar"][-1] >= 35).astype(float)
        advected_storm = (translate(fields["radar"][-1], dy, dx) >= 35).astype(float)
        advected_storm[~np.isfinite(translate(fields["radar"][-1], dy, dx))] = np.nan
    else:
        persisted_storm = advected_storm = np.full(x.shape[:2], np.nan)
    if observations.available["lightning"]:
        persisted_lightning = neighborhood((fields["lightning"].sum(axis=0) > 0).astype(float))
        advected_lightning = translate(persisted_lightning, dy, dx)
    else:
        persisted_lightning = advected_lightning = np.full(x.shape[:2], np.nan)
    return {"fusion": outputs, "persistence": {"storm": persisted_storm, "lightning": persisted_lightning},
            "advection": {"storm": advected_storm, "lightning": advected_lightning},
            "velocity": velocity, "abstained": not spatial_support}


def load_model():
    if not ARTIFACT.exists():
        raise RuntimeError("Run python -m nowcast.training before starting the app")
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def model_digest(artifact):
    return hashlib.sha256(json.dumps(artifact, sort_keys=True).encode()).hexdigest()

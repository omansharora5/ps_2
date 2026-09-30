from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import numpy as np


SOURCES = ("radar", "satellite", "lightning", "nwp")
HORIZONS = (15, 30, 60)
GRID_SIZE = 48
CELL_KM = 4.0
STEP_MINUTES = 5


@dataclass(frozen=True)
class Event:
    seed: int
    radar: np.ndarray
    satellite: np.ndarray
    lightning: np.ndarray
    nwp: np.ndarray
    timestamps: tuple[str, ...]


@dataclass(frozen=True)
class Snapshot:
    fields: dict[str, np.ndarray]
    available: dict[str, bool]
    issued_at: str
    status: list[dict]


def mosaic_dbz(fields: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Combine reflectivity in linear Z; missing returns NaN, never clear sky."""
    valid = np.isfinite(fields) & np.isfinite(weights) & (weights > 0)
    weight = np.where(valid, weights, 0.0)
    linear_z = np.power(10.0, np.where(valid, fields, 0.0) / 10.0)
    denominator = weight.sum(axis=0)
    numerator = (linear_z * weight).sum(axis=0)
    average = np.divide(numerator, denominator, out=np.full_like(numerator, np.nan), where=denominator > 0)
    return 10.0 * np.log10(average)


@lru_cache(maxsize=6)
def synthetic_event(seed: int) -> Event:
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[:GRID_SIZE, :GRID_SIZE]
    time = np.arange(30)[:, None, None]
    radar = np.zeros((30, GRID_SIZE, GRID_SIZE))
    cloud = np.zeros_like(radar)
    rate = np.zeros_like(radar)
    cells = 2 + seed % 2
    for _ in range(cells):
        x0, y0 = rng.uniform(5, 22), rng.uniform(7, 33)
        vx, vy = rng.uniform(0.25, 0.8), rng.uniform(-0.2, 0.4)
        peak = rng.uniform(9, 22)
        duration = rng.uniform(7, 15)
        radius = rng.uniform(2.5, 4.8)
        distance = (xx - x0 - vx * time) ** 2 + (yy - y0 - vy * time) ** 2
        shape = np.exp(-distance / (2 * radius**2))
        lifecycle = np.exp(-((time - peak) / duration) ** 2)
        core = shape * lifecycle
        radar = np.maximum(radar, core * rng.uniform(47, 61))
        early_lifecycle = np.exp(-((time - (peak - 2)) / duration) ** 2)
        cloud = np.maximum(cloud, np.exp(-distance / (2 * (radius + 2) ** 2)) * early_lifecycle)
        rate += np.maximum(core - 0.46, 0.0) * 2.3
    # Independently noisy overlapping instruments on a common grid.
    da = np.sqrt((xx - 7) ** 2 + (yy - 18) ** 2)
    db = np.sqrt((xx - 40) ** 2 + (yy - 28) ** 2)
    weights = np.stack([np.where(da < 42, 1 / (1 + da / 20), 0),
                        np.where(db < 42, 1 / (1 + db / 20), 0)])[:, None]
    instruments = np.stack([radar + rng.normal(0, 0.5, radar.shape),
                            radar + rng.normal(0, 0.7, radar.shape)])
    radar = np.clip(mosaic_dbz(instruments, np.broadcast_to(weights, instruments.shape)), 0, 65)
    satellite = 285 - 70 * cloud + rng.normal(0, 0.5, radar.shape)
    lightning = rng.poisson(rate).astype(float)
    environment = rng.uniform(900, 1900) + 400 * np.sin(xx / 17) + 250 * np.cos(yy / 13)
    nwp = np.broadcast_to(environment, radar.shape).copy()
    start = datetime(2025, 5, 12, 8, tzinfo=timezone.utc)
    timestamps = tuple((start + timedelta(minutes=STEP_MINUTES * t)).isoformat() for t in range(30))
    for array in (radar, satellite, lightning, nwp):
        array.setflags(write=False)
    return Event(seed, radar, satellite, lightning, nwp, timestamps)


def snapshot(event: Event, step: int, disabled=(), stale=()) -> Snapshot:
    if not 2 <= step < len(event.timestamps):
        raise ValueError("At least three observation frames are required")
    unknown = (set(disabled) | set(stale)) - set(SOURCES)
    if unknown:
        raise ValueError(f"Unknown source: {sorted(unknown)}")
    available = {name: name not in disabled and name not in stale for name in SOURCES}
    fields = {}
    status = []
    for name in SOURCES:
        present = available[name]
        values = getattr(event, name)[step - 2:step + 1].copy()
        if not present:
            values[:] = np.nan
        values.setflags(write=False)
        fields[name] = values
        state = "missing" if name in disabled else "stale" if name in stale else "available"
        status.append({"source": name, "state": state, "age_minutes": 45 if name in stale else None if name in disabled else 0,
                       "valid_at": event.timestamps[step] if present else None,
                       "available_at": event.timestamps[step] if present else None,
                       "provenance": "Synthetic observation", "instruments": 2 if name == "radar" else 1})
    return Snapshot(fields, available, event.timestamps[step], status)


def select_as_of(records: list[dict], issue_time: datetime, max_age_minutes: int) -> dict | None:
    """Reject future observations and observations that had not arrived at issue time."""
    if issue_time.tzinfo is None:
        raise ValueError("Issue time must have a timezone")
    eligible = []
    for record in records:
        valid = datetime.fromisoformat(record["valid_at"])
        received = datetime.fromisoformat(record["available_at"])
        if valid.tzinfo is None or received.tzinfo is None:
            raise ValueError("Observation times must have timezones")
        age = (issue_time - valid).total_seconds() / 60
        if 0 <= age <= max_age_minutes and received <= issue_time:
            eligible.append(record)
    return max(eligible, key=lambda r: datetime.fromisoformat(r["valid_at"]), default=None)

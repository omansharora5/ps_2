"""Coverage-aware research methods; no model admission, dispatch or Torch dependency."""

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from .probability_evaluation import EventPredictions, fit_temperature


PHASES = ("onset", "active", "break", "unknown")


def utc(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValueError("Timestamps must explicitly identify UTC")
    return result


def validate_survival(logits, event_bin, observed_bins, coverage):
    """Last axis is time; -1 means no event observed before censoring, never guaranteed dry."""
    z = np.asarray(logits, dtype=float)
    event, observed, mask = map(np.asarray, (event_bin, observed_bins, coverage))
    if z.ndim < 1 or not 1 <= z.shape[-1] <= 24:
        raise ValueError("Hazards require 1 to 24 ordered time bins on the last axis")
    if any(a.shape != z.shape[:-1] for a in (event, observed, mask)):
        raise ValueError("Survival target shapes must match the non-time logit dimensions")
    if not np.isin(mask, [0, 1]).all():
        raise ValueError("Survival coverage must be boolean")
    mask = mask.astype(bool)
    if not np.isfinite(z[mask]).all():
        raise ValueError("Covered hazard logits must be finite")
    for array in (event, observed):
        if not np.isfinite(array[mask]).all() or not np.equal(array[mask], np.floor(array[mask])).all():
            raise ValueError("Survival targets must be integer bins")
    event = np.where(mask, event, -1).astype(np.int64)
    observed = np.where(mask, observed, 0).astype(np.int64)
    if ((observed[mask] < 1) | (observed[mask] > z.shape[-1])).any():
        raise ValueError("Covered examples need a positive observed prefix within the horizon")
    if ((event[mask] < -1) | (event[mask] >= observed[mask])).any():
        raise ValueError("Events must occur inside the observed prefix")
    return z, event, observed, mask


def survival_nll(logits, event_bin, observed_bins, coverage):
    z, event, observed, mask = validate_survival(logits, event_bin, observed_bins, coverage)
    if not mask.any():
        raise ValueError("No covered onset labels")
    z, event, observed = z[mask], event[mask], observed[mask]
    bins = np.arange(z.shape[-1])
    survived = bins < np.where(event >= 0, event, observed)[..., None]
    struck = (event[..., None] == bins) & (event[..., None] >= 0)
    losses = np.where(survived, np.logaddexp(0, z), 0) + np.where(struck, np.logaddexp(0, -z), 0)
    return float(losses.sum(axis=-1).mean())


def hazard_distribution(logits, bin_edges_minutes=(5, 10, 15, 20, 25, 30)):
    z = np.asarray(logits, dtype=float)
    edges = np.asarray(bin_edges_minutes, dtype=float)
    if (z.ndim < 1 or edges.shape != (z.shape[-1],) or not 1 <= edges.size <= 24
            or not np.isfinite(z).all() or not np.isfinite(edges).all()
            or edges[0] <= 0 or edges[-1] > 120 or (np.diff(edges) <= 0).any()):
        raise ValueError("Finite hazard logits need matching positive ordered bin edges up to 120 minutes")
    log_survival = -np.logaddexp(0, z)
    prior = np.concatenate([np.zeros(z.shape[:-1] + (1,)), np.cumsum(log_survival, axis=-1)[..., :-1]], axis=-1)
    mass = np.exp(prior - np.logaddexp(0, -z))
    no_event = np.exp(log_survival.sum(axis=-1))
    return {"bin_edges_minutes": edges.tolist(), "event_mass": mass,
            "event_cdf": np.cumsum(mass, axis=-1), "no_event_probability": no_event}


def eligible_onset_distribution(logits, bin_edges_minutes, at_risk):
    """An onset is defined only where the event-free initial state is positively known."""
    eligibility = np.asarray(at_risk)
    if eligibility.shape != np.asarray(logits).shape[:-1] or not np.isin(eligibility, [0, 1]).all():
        raise ValueError("Onset eligibility requires an explicit boolean mask matching every pixel")
    eligibility = eligibility.astype(bool)
    result = hazard_distribution(logits, bin_edges_minutes)
    return {"bin_edges_minutes": result["bin_edges_minutes"], "eligible": eligibility,
            "event_mass": np.where(eligibility[..., None], result["event_mass"], np.nan),
            "event_cdf": np.where(eligibility[..., None], result["event_cdf"], np.nan),
            "no_event_probability": np.where(eligibility, result["no_event_probability"], np.nan),
            "eligibility_definition": "Known event-free state at issue under the training target definition; unknown or ongoing events are ineligible."}


def onset_summary(logits, bin_edges_minutes=(5, 10, 15, 20, 25, 30), *, central_mass=.8):
    """Single cell, conditional interval if an event occurs; no precise minute or end time."""
    if np.asarray(logits).ndim != 1 or not 0 < central_mass < 1:
        raise ValueError("Onset summary requires one cell and a central mass in (0,1)")
    result = hazard_distribution(logits, bin_edges_minutes)
    probability = float(result["event_mass"].sum())
    interval = None
    if probability > 1e-12:
        conditional = result["event_cdf"] / probability
        tail = (1 - central_mass) / 2
        lower, upper = np.searchsorted(conditional, [tail, 1 - tail]).clip(0, len(bin_edges_minutes) - 1)
        edges = [0.] + result["bin_edges_minutes"]
        interval = [edges[int(lower)], edges[int(upper) + 1]]
    return {"event_probability": probability, "no_event_probability": float(result["no_event_probability"]),
            "conditional_onset_interval_minutes": interval, "conditional_central_mass": central_mass,
            "bin_event_probabilities": result["event_mass"].tolist(), "heavy_rain_end": None,
            "status": "research_uncalibrated", "note": "Interval is conditional on an event within the horizon; it is not an exact onset time."}


@dataclass(frozen=True)
class PhaseEvent:
    predictions: EventPredictions
    phase: str
    issue_time: str
    phase_available_at: str
    role: str = "calibration"

    def __post_init__(self):
        if self.phase not in PHASES:
            raise ValueError("Phase must be onset, active, break or unknown")
        if utc(self.phase_available_at) > utc(self.issue_time):
            raise ValueError("Phase annotation was not available at issue time")
        if self.role not in ("train", "validation", "calibration", "test"):
            raise ValueError("Unknown event role")


def fit_phase_calibration(events, *, min_events=4, min_each_class=20):
    events = list(events)
    if not events or type(min_events) is not int or min_events < 2 or type(min_each_class) is not int or min_each_class < 1:
        raise ValueError("Calibration needs events and positive minimum support")
    if any(e.role != "calibration" for e in events):
        raise ValueError("Only calibration events may fit phase temperatures")
    if len({e.predictions.event_id for e in events}) != len(events):
        raise ValueError("Phase calibration requires unique independent event groups")
    pooled = fit_temperature([e.predictions for e in events])
    phases = {}
    for phase in PHASES:
        subset = [e.predictions for e in events if e.phase == phase and e.predictions.coverage.any()]
        labels = np.concatenate([e.targets[e.coverage] for e in subset]) if subset else np.array([])
        enough = phase != "unknown" and len(subset) >= min_events and all((labels == y).sum() >= min_each_class for y in (0, 1))
        phases[phase] = {"source": "phase" if enough else "pooled_fallback", "event_count": len(subset),
                         "calibrator": fit_temperature(subset) if enough else pooled}
    return {"method": "phase_temperature_v1", "pooled": pooled, "phases": phases,
            "min_events": min_events, "min_each_class": min_each_class,
            "fit_event_ids": [e.predictions.event_id for e in events]}


def apply_phase_calibration(logits, phase, artifact, *, issue_time, phase_available_at):
    if phase not in PHASES or utc(phase_available_at) > utc(issue_time):
        raise ValueError("Phase must be recognized and available at issue time")
    if artifact.get("method") != "phase_temperature_v1":
        raise ValueError("Unsupported phase calibration artifact")
    selected = artifact["phases"][phase]
    temperature = float(selected["calibrator"]["temperature"])
    z = np.asarray(logits, dtype=float)
    if not np.isfinite(z).all() or not np.isfinite(temperature) or not .05 <= temperature <= 20:
        raise ValueError("Finite logits and a valid fitted temperature are required")
    return {"probabilities": np.exp(-np.logaddexp(0, -z / temperature)), "source": selected["source"],
            "phase": phase, "temperature": temperature}


def _zr_rows(rows, role):
    rows = list(rows)
    if not rows or any(r.get("role") != role for r in rows):
        raise ValueError(f"Z-R requires only {role} rows")
    accepted = []
    for row in rows:
        if row.get("reflectivity_unit") != "dBZ" or row.get("rain_unit") != "mm/h":
            raise ValueError("Z-R requires dBZ and mm/h; accumulation totals must be converted explicitly")
        if not isinstance(row.get("event_id"), str) or not row["event_id"] or not isinstance(row.get("season"), str) or not row["season"]:
            raise ValueError("Z-R rows require event and season identities")
        if not isinstance(row.get("quality_passed"), bool):
            raise ValueError("Z-R quality decisions must be explicit booleans")
        if not row["quality_passed"]:
            continue
        if not isinstance(row.get("matched_support"), str) or not row["matched_support"] or abs(float(row["time_delta_seconds"])) > 300:
            raise ValueError("Z-R needs matched gauge/radar support and timestamps within five minutes")
        dbz, rain = float(row["dbz"]), float(row["rain_mm_h"])
        if not np.isfinite([dbz, rain, float(row["time_delta_seconds"])]).all() or rain < 0 or not -40 <= dbz <= 90:
            raise ValueError("Z-R pairs must be finite, nonnegative rain and bounded reflectivity")
        accepted.append(dict(row, dbz=dbz, rain_mm_h=rain))
    if not accepted:
        raise ValueError("No quality-controlled Z-R pairs")
    return accepted


def _fit_zr(rows, min_events):
    wet = [r for r in rows if r["rain_mm_h"] > 0]
    events = sorted({r["event_id"] for r in wet})
    if len(events) < min_events or len(wet) < 6:
        return None
    x = np.log([r["rain_mm_h"] for r in wet])
    y = np.asarray([r["dbz"] for r in wet]) * np.log(10) / 10
    if np.ptp(x) < 1e-6:
        return None
    intercept, slope = np.linalg.lstsq(np.column_stack([np.ones(x.size), x]), y, rcond=None)[0]
    a, b = float(np.exp(intercept)), float(slope)
    if not 1 <= a <= 10000 or not .1 <= b <= 5:
        raise ValueError("Fitted Z-R coefficients exceed the declared research admission bounds")
    return {"a": a, "b": b, "fit_event_ids": events, "positive_pairs": len(wet)}


def fit_seasonal_zr(training_pairs, *, min_events=3):
    if type(min_events) is not int or min_events < 2:
        raise ValueError("At least two independent events are required")
    rows = _zr_rows(training_pairs, "train")
    pooled = _fit_zr(rows, min_events)
    if pooled is None:
        raise ValueError("Insufficient independent wet pairs or rain variation to fit Z-R")
    seasons = {}
    for season in sorted({r["season"] for r in rows}):
        fitted = _fit_zr([r for r in rows if r["season"] == season], min_events)
        seasons[season] = {"source": "season" if fitted else "pooled_fallback", "coefficients": fitted or pooled}
    return {"method": "seasonal_log_zr_v1", "formula": "Z=a*R**b; Z=10**(dBZ/10); R in mm/h",
            "pooled": pooled, "seasons": seasons, "fit_event_ids": sorted({r["event_id"] for r in rows}),
            "excluded_zero_rain_pairs": sum(r["rain_mm_h"] == 0 for r in rows), "min_events": min_events,
            "status": "research_fit_requires_held_out_validation"}


def evaluate_seasonal_zr(test_pairs, artifact, *, baseline_a=200., baseline_b=1.6):
    rows = _zr_rows(test_pairs, "test")
    if artifact.get("method") != "seasonal_log_zr_v1" or not np.isfinite([baseline_a, baseline_b]).all() or min(baseline_a, baseline_b) <= 0:
        raise ValueError("A supported fitted artifact and positive baseline coefficients are required")
    if {r["event_id"] for r in rows} & set(artifact["fit_event_ids"]):
        raise ValueError("Held-out Z-R events overlap fitting events")
    predicted, baseline, truth = [], [], []
    for row in rows:
        coefficients = artifact["seasons"].get(row["season"], {"coefficients": artifact["pooled"]})["coefficients"]
        if not np.isfinite([coefficients["a"], coefficients["b"]]).all() or not 1 <= coefficients["a"] <= 10000 or not .1 <= coefficients["b"] <= 5:
            raise ValueError("Invalid fitted Z-R coefficients")
        z = 10 ** (row["dbz"] / 10)
        predicted.append((z / coefficients["a"]) ** (1 / coefficients["b"]))
        baseline.append((z / baseline_a) ** (1 / baseline_b))
        truth.append(row["rain_mm_h"])
    def scores(values):
        errors = np.asarray(values) - truth
        return {"mae_mm_h": float(np.abs(errors).mean()), "rmse_mm_h": float(np.sqrt((errors ** 2).mean()))}
    return {"fitted": scores(predicted), "baseline": scores(baseline), "pairs": len(rows),
            "event_count": len({r["event_id"] for r in rows}), "baseline_a": baseline_a, "baseline_b": baseline_b,
            "note": "Paired held-out samples; event count is not pixel count. No general NCR skill claim."}


def quality_diagnostics(*, cloud_top_k=None, rain_observed=None, dust_reported=False, radar_covered=False):
    if cloud_top_k is not None and (not np.isfinite(cloud_top_k) or not 150 <= cloud_top_k <= 350):
        raise ValueError("Cloud-top temperature must be finite kelvin")
    if (rain_observed is not None and type(rain_observed) is not bool) or type(dust_reported) is not bool or type(radar_covered) is not bool:
        raise ValueError("Quality evidence uses explicit boolean/unknown states")
    flags = []
    if not radar_covered:
        flags.append("radar_coverage_missing")
    if rain_observed is True and cloud_top_k is not None and cloud_top_k >= 273.15:
        flags.append("rain_reported_with_above_freezing_cloud_top")
    if dust_reported:
        flags.append("dust_report_requires_precipitation_qc")
    return {"flags": flags, "status": "descriptive_evidence_only", "validated_warm_rain_detector": False,
            "validated_dust_detector": False, "note": "Missing radar is not dry. Warm cloud tops do not exclude rain; dust can contaminate radar evidence."}

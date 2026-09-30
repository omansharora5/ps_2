"""Covered binary probabilities, held-out temperature fitting and event uncertainty."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EventPredictions:
    event_id: str
    logits: np.ndarray
    targets: np.ndarray
    coverage: np.ndarray

    def __post_init__(self):
        logits, targets, coverage = np.asarray(self.logits, dtype=float), np.asarray(self.targets, dtype=float), np.asarray(self.coverage)
        if not isinstance(self.event_id, str) or not self.event_id:
            raise ValueError("A nonempty event ID is required")
        if logits.shape != targets.shape or targets.shape != coverage.shape:
            raise ValueError("Logits, targets and coverage must have the same shape")
        if not np.isin(coverage, [0, 1]).all():
            raise ValueError("coverage must be boolean or 0/1")
        coverage = coverage.astype(bool)
        if not np.isfinite(logits[coverage]).all():
            raise ValueError("Covered logits must be finite")
        if not np.isin(targets[coverage], [0, 1]).all():
            raise ValueError("Covered targets must be binary")
        object.__setattr__(self, "logits", logits)
        object.__setattr__(self, "targets", targets)
        object.__setattr__(self, "coverage", coverage)


def _covered(events):
    if not events or len({e.event_id for e in events}) != len(events):
        raise ValueError("Predictions require unique event groups")
    usable = [e for e in events if e.coverage.any()]
    if not usable:
        raise ValueError("No covered predictions are available")
    return usable


def _sigmoid(logits):
    return np.exp(-np.logaddexp(0., -logits))


def fit_temperature(events):
    """Fit on calibration events only; a convex, regularized inverse temperature."""
    events = _covered(events)
    z = np.concatenate([e.logits[e.coverage] for e in events])
    y = np.concatenate([e.targets[e.coverage] for e in events])
    regularization = .001
    params = {"method": "regularized_temperature_v1", "temperature": 1., "fit_status": "fitted",
              "fit_event_ids": [e.event_id for e in events], "covered_pixels": int(y.size),
              "regularization": regularization, "inverse_temperature_bounds": [.05, 20.],
              "weighting": "covered pixel-example weighted; events are not equally weighted"}
    if len(np.unique(y)) < 2:
        params["fit_status"] = "identity_single_class"
    elif np.ptp(z) <= 1e-12:
        params["fit_status"] = "identity_constant_logits"
    else:
        # NLL is convex in a positive inverse temperature. The L2 term is centred on identity.
        def derivative(scale):
            return float(np.mean((_sigmoid(z * scale) - y) * z) + regularization * (scale - 1))
        low, high = params["inverse_temperature_bounds"]
        if derivative(low) >= 0:
            scale = low
        elif derivative(high) <= 0:
            scale = high
        else:
            for _ in range(80):
                middle = (low + high) / 2
                if derivative(middle) > 0:
                    high = middle
                else:
                    low = middle
            scale = (low + high) / 2
        params["temperature"] = float(1 / scale)
    return params


def _divide(numerator, denominator):
    return float(numerator / denominator) if denominator else None


def _loss(p, y):
    clipped = np.clip(p, 1e-7, 1 - 1e-7)
    return -(y * np.log(clipped) + (1 - y) * np.log1p(-clipped))


def probability_metrics(probabilities, targets, training_rate, threshold=.5, bins=10):
    p, y = np.asarray(probabilities, dtype=float).ravel(), np.asarray(targets, dtype=float).ravel()
    if p.shape != y.shape or not p.size:
        raise ValueError("Metrics require nonempty matching probability/target arrays")
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any() or not np.isin(y, [0, 1]).all():
        raise ValueError("Metrics require finite probabilities in [0,1] and binary targets")
    if not np.isfinite(training_rate) or not 0 <= training_rate <= 1:
        raise ValueError("Training climatology must be a finite probability")
    if not 0 <= threshold <= 1 or not isinstance(bins, int) or bins < 1:
        raise ValueError("Threshold must be in [0,1] and bins must be positive")
    predicted, observed = p >= threshold, y == 1
    hits, misses = int((predicted & observed).sum()), int((~predicted & observed).sum())
    alarms = int((predicted & ~observed).sum())
    reliability = []
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        members = (p >= lower) & ((p <= upper) if index == bins - 1 else (p < upper))
        reliability.append({"lower": lower, "upper": upper, "count": int(members.sum()),
                            "mean_probability": float(p[members].mean()) if members.any() else None,
                            "observed_frequency": float(y[members].mean()) if members.any() else None})
    average_precision = None
    if observed.any():
        order = np.argsort(-p, kind="stable")
        sorted_p, sorted_y = p[order], y[order]
        ends = np.r_[np.flatnonzero(np.diff(sorted_p) != 0), p.size - 1]
        true_positives = np.cumsum(sorted_y)[ends]
        recall = true_positives / y.sum()
        precision = true_positives / (ends + 1)
        average_precision = float(np.sum(np.diff(np.r_[0., recall]) * precision))
    brier = float(np.mean((p - y) ** 2))
    baseline = float(np.mean((training_rate - y) ** 2))
    return {"covered_pixels": int(p.size), "brier": brier, "log_loss": float(_loss(p, y).mean()),
            "log_loss_probability_clip": [1e-7, 1 - 1e-7], "observed_rate": float(y.mean()),
            "average_precision": average_precision,
            "average_precision_definition": "Non-interpolated precision-recall area: sum of recall increments times precision; tied scores share one threshold. Not ROC AUC or trapezoidal PR AUC. Null when no positives.",
            "single_class": len(np.unique(y)) < 2, "threshold": threshold,
            "hits": hits, "misses": misses, "false_alarms": alarms,
            "correct_negatives": int((~predicted & ~observed).sum()),
            "pod": _divide(hits, hits + misses), "far": _divide(alarms, hits + alarms),
            "csi": _divide(hits, hits + misses + alarms), "reliability": reliability,
            "training_climatology": float(training_rate), "training_climatology_brier": baseline,
            "brier_skill": 1 - brier / baseline if baseline > 0 else None,
            "independence_note": "Covered pixels/windows are pooled and dependent; independent event count is reported separately."}


def evaluate_events(events, training_rate, calibrator=None):
    """Score frozen predictions. No fitting or model selection occurs here."""
    events = _covered(events)
    temperature = 1.
    if calibrator is not None:
        temperature = float(calibrator["temperature"])
        if calibrator.get("method") != "regularized_temperature_v1" or not np.isfinite(temperature) or not .05 <= temperature <= 20:
            raise ValueError("Unsupported or invalid temperature calibrator")
    raw_parts, calibrated_parts, labels, statistics = [], [], [], []
    for e in events:
        z, y = e.logits[e.coverage], e.targets[e.coverage]
        raw, calibrated = _sigmoid(z), _sigmoid(z / temperature)
        raw_parts.append(raw); calibrated_parts.append(calibrated); labels.append(y)
        statistics.append([y.size, ((raw - y) ** 2).sum(), _loss(raw, y).sum(),
                           ((calibrated - y) ** 2).sum(), _loss(calibrated, y).sum(), ((training_rate - y) ** 2).sum()])
    y = np.concatenate(labels)
    raw = probability_metrics(np.concatenate(raw_parts), y, training_rate)
    calibrated = probability_metrics(np.concatenate(calibrated_parts), y, training_rate) if calibrator is not None else None
    bootstrap = {"status": "unavailable", "event_count": len(events), "replicates": 200, "seed": 17,
                 "confidence_level": .95, "method": "Percentile cluster bootstrap of whole event groups, with replacement; models and calibrator fixed",
                 "note": "At least two test event groups are required. Few groups give unstable intervals; these exclude training/calibrator-fit uncertainty.", "intervals": {}}
    if len(events) >= 2:
        rng = np.random.default_rng(17)
        totals = np.asarray(statistics)[rng.integers(0, len(events), size=(200, len(events)))].sum(axis=1)
        rb, rl, cb, cl, baseline = (totals[:, i] / totals[:, 0] for i in range(1, 6))
        skills = np.full(200, np.nan)
        np.divide(rb, baseline, out=skills, where=baseline > 0)
        scores = {"raw_brier": rb, "raw_log_loss": rl, "raw_brier_skill": 1 - skills}
        if calibrator is not None:
            cal_skills = np.full(200, np.nan)
            np.divide(cb, baseline, out=cal_skills, where=baseline > 0)
            scores.update(calibrated_brier=cb, calibrated_log_loss=cl, calibrated_brier_skill=1-cal_skills,
                          calibrated_minus_raw_brier=cb-rb)
        for name, values in scores.items():
            finite = values[np.isfinite(values)]
            interval = np.quantile(finite, [.025, .975]) if finite.size else [None, None]
            bootstrap["intervals"][name] = {"lower": float(interval[0]) if finite.size else None,
                                              "upper": float(interval[1]) if finite.size else None,
                                              "valid_replicates": int(finite.size)}
        bootstrap["status"] = "available"
    return {"raw": raw, "calibrated": calibrated, "calibration": calibrator,
            "event_count": len(events), "event_ids": [e.event_id for e in events], "event_bootstrap": bootstrap}

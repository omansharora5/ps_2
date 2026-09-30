"""Train a reproducible simulator-only baseline; do not infer Indian forecast skill."""
import json
import time
from pathlib import Path

import numpy as np

from .forecast import ARTIFACT, FEATURE_NAMES, features, predict, sigmoid, targets
from .observations import HORIZONS, snapshot, synthetic_event
from .verification import verify


def fit(x, y, seed):
    rng = np.random.default_rng(seed)
    weights = np.zeros(x.shape[1])
    prevalence = np.clip(y.mean(), 0.001, 0.999)
    weights[0] = np.log(prevalence / (1 - prevalence))
    for _ in range(550):
        idx = rng.integers(0, len(x), 2048)
        xb, yb = x[idx], y[idx]
        gradient = xb.T @ (sigmoid(xb @ weights) - yb) / len(idx)
        gradient[1:] += 0.0005 * weights[1:]
        weights -= 0.5 * gradient
    return weights


def dataset(seeds, horizon, training=False):
    arrays, labels = [], {"storm": [], "lightning": []}
    for seed in seeds:
        event = synthetic_event(seed)
        for step in (5, 10):
            truth = targets(event, step, horizon)
            configurations = [()]
            if training:
                configurations += [("radar",), ("satellite",), ("lightning",), ("nwp",), ("radar", "lightning")]
            for disabled in configurations:
                x, _ = features(snapshot(event, step, disabled), horizon)
                idx = np.random.default_rng(seed * 100 + step).choice(x.shape[0] * x.shape[1], 384, replace=False)
                arrays.append(x.reshape(-1, x.shape[-1])[idx])
                for hazard in labels:
                    labels[hazard].append(truth[hazard].ravel()[idx])
    return np.concatenate(arrays), {k: np.concatenate(v) for k, v in labels.items()}


def main():
    started = time.perf_counter()
    artifact = {"version": "synthetic-logistic-v1", "scope": "Synthetic simulator only; no Indian weather validation",
                "features": FEATURE_NAMES, "heads": {}, "splits": {"train": list(range(24)), "validation": list(range(40, 46)), "test": list(range(60, 66))},
                "target_definitions": {"storm": "Reflectivity >=35 dBZ at t+h, a simulated convective proxy",
                                       "lightning": "Any simulated flash within 8 km in (t+h-15 min,t+h]; not cumulative"},
                "calibration": "Temperature selected on complete-source synthetic validation events; outage subsets are not separately calibrated"}
    for horizon in HORIZONS:
        x, y = dataset(artifact["splits"]["train"], horizon, training=True)
        xv, yv = dataset(artifact["splits"]["validation"], horizon)
        for hazard in ("storm", "lightning"):
            weights = fit(x, y[hazard], horizon)
            logits = xv @ weights
            temperature = min((0.5, 0.75, 1.0, 1.5, 2.0, 3.0), key=lambda t: float(np.mean((sigmoid(logits / t) - yv[hazard]) ** 2)))
            artifact["heads"][f"{hazard}-{horizon}"] = {"weights": weights.tolist(), "temperature": temperature,
                                                               "training_samples": len(x), "validation_samples": len(xv)}
        print(f"Fitted +{horizon} minutes", flush=True)
    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    report = {"scope": artifact["scope"], "splits": artifact["splits"], "scores": [], "training_seconds": round(time.perf_counter() - started, 3),
              "comparison": "All available methods scored on identical finite-prediction and truth intersections per case. Undefined models remain unavailable."}
    for horizon in HORIZONS:
        for disabled in ((), ("radar",), ("lightning",), ("radar", "satellite", "lightning", "nwp")):
            predictions = {model: {hazard: [] for hazard in ("storm", "lightning")} for model in ("fusion", "persistence", "advection")}
            truths = {hazard: [] for hazard in ("storm", "lightning")}
            masks = {hazard: [] for hazard in truths}
            for seed in artifact["splits"]["test"]:
                event = synthetic_event(seed)
                result = predict(snapshot(event, 8, disabled), horizon, artifact)
                truth = targets(event, 8, horizon)
                for hazard in truths:
                    truths[hazard].append(truth[hazard])
                    common = np.isfinite(truth[hazard])
                    for name in predictions:
                        candidate = result[name][hazard]
                        if np.isfinite(candidate).any():
                            common &= np.isfinite(candidate)
                    masks[hazard].append(common)
                    for model in predictions:
                        predictions[model][hazard].append(result[model][hazard])
            for hazard in truths:
                for model in predictions:
                    # Stacking cases vertically is only for pixel metrics, not neighborhood scores.
                    p = np.concatenate(predictions[model][hazard], axis=0)
                    y = np.concatenate(truths[hazard], axis=0)
                    score = verify(p, y, mask=np.concatenate(masks[hazard], axis=0))
                    score.pop("fss")
                    score.pop("reliability")
                    report["scores"].append({"horizon": horizon, "hazard": hazard, "model": model,
                                              "disabled": list(disabled), **score})
    path = Path(__file__).resolve().parents[1] / "data" / "evaluation.json"
    path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Saved model and test report in {time.perf_counter() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()

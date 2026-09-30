import numpy as np

from .numerics import neighborhood


def verify(prediction: np.ndarray, truth: np.ndarray, threshold=0.5, mask=None) -> dict:
    valid = np.isfinite(prediction) & np.isfinite(truth)
    if mask is not None:
        valid &= mask
    p, y = prediction[valid], truth[valid]
    if np.any((p < 0) | (p > 1)) or np.any((y != 0) & (y != 1)):
        raise ValueError("Predictions must be probabilities and labels must be binary")
    forecast, observed = p >= threshold, y > 0
    hits = int(np.sum(forecast & observed))
    misses = int(np.sum(~forecast & observed))
    false_alarms = int(np.sum(forecast & ~observed))
    correct_negatives = int(np.sum(~forecast & ~observed))
    def divide(a, b):
        return float(a / b) if b else None
    reliability = []
    for index in range(10):
        lo, hi = index / 10, (index + 1) / 10
        members = (p >= lo) & ((p <= hi) if index == 9 else (p < hi))
        reliability.append({"bin": round((lo + hi) / 2, 2), "count": int(members.sum()),
                            "forecast": float(p[members].mean()) if members.any() else None,
                            "observed": float(y[members].mean()) if members.any() else None})
    if valid.any():
        # Restrict neighborhood verification to completely observed neighborhoods.
        support = neighborhood(valid.astype(float), radius=2, mode="mean") > 0.999
        fp = neighborhood(np.where(valid, prediction >= threshold, 0).astype(float), mode="mean")
        fo = neighborhood(np.where(valid, truth, 0), mode="mean")
        denominator = np.sum(fp[support] ** 2 + fo[support] ** 2)
        fss = float(1 - np.sum((fp[support] - fo[support]) ** 2) / denominator) if denominator > 0 else None
    else:
        fss = None
    return {"samples": int(len(p)), "hits": hits, "misses": misses, "false_alarms": false_alarms,
            "correct_negatives": correct_negatives, "csi": divide(hits, hits + misses + false_alarms),
            "pod": divide(hits, hits + misses), "far": divide(false_alarms, hits + false_alarms),
            "brier": float(np.mean((p - y) ** 2)) if len(p) else None,
            "base_rate": float(y.mean()) if len(y) else None, "fss": fss,
            "threshold": threshold, "reliability": reliability}

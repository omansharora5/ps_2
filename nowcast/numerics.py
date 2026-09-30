import numpy as np


def translate(field: np.ndarray, dy: float, dx: float, fill: float = np.nan) -> np.ndarray:
    """Bilinear backtracking with an explicit unknown boundary, without toroidal wrap."""
    yy, xx = np.indices(field.shape, dtype=float)
    y, x = yy - dy, xx - dx
    y0, x0 = np.floor(y).astype(int), np.floor(x).astype(int)
    ay, ax = y - y0, x - x0
    result = np.zeros(field.shape, dtype=float)
    weight_sum = np.zeros(field.shape, dtype=float)
    for oy, ox, weight in [(0, 0, (1 - ay) * (1 - ax)), (1, 0, ay * (1 - ax)),
                           (0, 1, (1 - ay) * ax), (1, 1, ay * ax)]:
        sy, sx = y0 + oy, x0 + ox
        inside = (sy >= 0) & (sy < field.shape[0]) & (sx >= 0) & (sx < field.shape[1])
        values = field[np.clip(sy, 0, field.shape[0] - 1), np.clip(sx, 0, field.shape[1] - 1)]
        valid = inside & np.isfinite(values)
        result += np.where(valid, values, 0) * weight
        weight_sum += valid * weight
    return np.where(weight_sum > 0.999, result, fill)


def motion(previous: np.ndarray, current: np.ndarray, radius: int = 3) -> tuple[float, float]:
    best = (float("-inf"), 0.0, 0.0)
    # Correlation reduces sensitivity to uniform echo growth and decay.
    def score(dy, dx):
        shifted = translate(previous, dy, dx)
        valid = np.isfinite(shifted) & np.isfinite(current)
        if valid.sum() < 16:
            return float("-inf")
        a, b = shifted[valid], current[valid]
        a, b = a - a.mean(), b - b.mean()
        norm = np.sqrt(np.sum(a * a) * np.sum(b * b))
        return float(np.sum(a * b) / norm) if norm > 1e-10 else float("-inf")
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            candidate = (score(dy, dx) - 1e-8 * (dy * dy + dx * dx), float(dy), float(dx))
            if candidate[0] > best[0]:
                best = candidate
    if not np.isfinite(best[0]):
        return 0.0, 0.0
    cy, cx = best[1:]
    for dy in (cy - 0.5, cy, cy + 0.5):
        for dx in (cx - 0.5, cx, cx + 0.5):
            candidate = (score(dy, dx) - 1e-8 * (dy * dy + dx * dx), dy, dx)
            if candidate[0] > best[0]:
                best = candidate
    return best[1], best[2]


def neighborhood(field: np.ndarray, radius: int = 2, mode="max") -> np.ndarray:
    values = []
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dy * dy + dx * dx <= radius * radius:
                values.append(translate(field, dy, dx, fill=0))
    stacked = np.stack(values)
    return stacked.max(axis=0) if mode == "max" else stacked.mean(axis=0)


def components(field: np.ndarray, threshold: float, minimum_pixels=4) -> list[dict]:
    active = np.isfinite(field) & (field >= threshold)
    visited = np.zeros_like(active)
    found = []
    for y, x in zip(*np.where(active)):
        if visited[y, x]:
            continue
        stack, points = [(int(y), int(x))], []
        visited[y, x] = True
        while stack:
            py, px = stack.pop()
            points.append((py, px))
            for ny, nx in ((py - 1, px), (py + 1, px), (py, px - 1), (py, px + 1)):
                if 0 <= ny < active.shape[0] and 0 <= nx < active.shape[1] and active[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    stack.append((ny, nx))
        if len(points) >= minimum_pixels:
            coords = np.array(points)
            found.append({"x": float(coords[:, 1].mean()), "y": float(coords[:, 0].mean()),
                          "pixels": len(points), "peak": float(field[coords[:, 0], coords[:, 1]].max())})
    return sorted(found, key=lambda c: c["pixels"], reverse=True)

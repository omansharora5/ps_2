"""Preview a bounded, public MOSDAC INSAT catalogue query; no login or downloads.

Search parameters follow the official mdapi.py search_results function:
https://www.mosdac.gov.in/software/mdapi.zip
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlencode
import urllib.request

ENDPOINT = "https://mosdac.gov.in/apios/datasets.json"
DATASET = "3SIMG_L1B_STD"
DEFAULT_BBOX = "76.5,28,78,29.3"
MAX_RESPONSE_BYTES = 1024 * 1024
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "data/ncr/mosdac"


def parameters(day: str, count: int, bbox: str) -> dict:
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError("Use an ISO YYYY-MM-DD date")
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 10:
        raise ValueError("Catalogue count must be between 1 and 10")
    try:
        west, south, east, north = [float(value) for value in bbox.split(",")]
    except (ValueError, TypeError) as error:
        raise ValueError("Bounding box needs west,south,east,north") from error
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Invalid geographic bounding box")
    if east - west > 5 or north - south > 5:
        raise ValueError("This pilot query limits the bounding box to five degrees per axis")
    return {"datasetId": DATASET, "startTime": day, "endTime": day, "count": count, "boundingBox": bbox}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("MOSDAC catalogue redirect refused")


def fetch_catalogue(url: str) -> bytes:
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "SIH26072-research/1.0", "Accept": "application/json"})
    with opener.open(request, timeout=30) as response:
        declared = response.headers.get("Content-Length")
        if declared is not None and (int(declared) < 0 or int(declared) > MAX_RESPONSE_BYTES):
            raise ValueError("MOSDAC catalogue response exceeds byte budget")
        if "json" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("MOSDAC catalogue returned a non-JSON response")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("MOSDAC catalogue response exceeds byte budget")
        return raw


def validate_response(raw: bytes, requested_count: int) -> dict:
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("MOSDAC catalogue response exceeds byte budget")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        raise ValueError("MOSDAC response lacks catalogue entries")
    entries = payload["entries"]
    total = payload.get("totalResults")
    if not isinstance(total, int) or isinstance(total, bool) or total < len(entries):
        raise ValueError("MOSDAC response has invalid result count")
    if len(entries) > requested_count:
        raise ValueError("MOSDAC response exceeded requested count")
    for entry in entries:
        if not isinstance(entry, dict) or not all(isinstance(entry.get(key), str) and entry[key] for key in ("id", "identifier", "dcDate")):
            raise ValueError("MOSDAC entry lacks identity or observation interval")
        if not entry["identifier"].startswith("3SIMG_") or "_L1B_STD_" not in entry["identifier"]:
            raise ValueError("Unexpected MOSDAC product returned")
        try:
            start, end = [datetime.fromisoformat(part.replace("Z", "+00:00")) for part in entry["dcDate"].split("/")]
            if start.tzinfo is None or end.tzinfo is None or end <= start:
                raise ValueError("Invalid observation interval")
        except (ValueError, TypeError) as error:
            raise ValueError("Invalid MOSDAC observation interval") from error
    return payload


def encode(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".mosdac-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(raw)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def query(root: Path, day: str, count=2, bbox=DEFAULT_BBOX, fetch=None) -> dict:
    request = parameters(day, count, bbox)
    url = ENDPOINT + "?" + urlencode(request)
    raw = (fetch or fetch_catalogue)(url)
    payload = validate_response(raw, count)
    digest = hashlib.sha256(encode(request) + raw).hexdigest()
    directory = root / "previews" / digest
    manifest = {
        "id": digest, "status": "catalogue_preview_only", "provider": "ISRO MOSDAC",
        "request": request, "source_url": url,
        "official_sdk_url": "https://www.mosdac.gov.in/software/mdapi.zip",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "response_sha256": hashlib.sha256(raw).hexdigest(), "response_bytes": len(raw),
        "provider_response_updated_verbatim": payload.get("updated"),
        "total_matches": payload["totalResults"], "provider_total_size_mb": payload.get("totalSizeMB"),
        "returned_entries": len(payload["entries"]), "observation_intervals": [entry["dcDate"] for entry in payload["entries"]],
        "scientific_payloads_downloaded": 0, "credentials_used": False, "training_ready": False,
        "limitations": ["Public catalogue metadata only; approved MOSDAC credentials required for scientific downloads", "Bounding-box search can return full-scene granules rather than cropped NCR files", "Provider catalogue update time is not observation time or retrieval time", "This query does not establish rain/no-rain labels"],
    }
    existing = directory / "manifest.json"
    if existing.exists():
        previous = json.loads(existing.read_text(encoding="utf-8"))
        if previous.get("id") != digest:
            raise ValueError("MOSDAC preview identity conflict")
        manifest["retrieved_at_utc"] = previous.get("retrieved_at_utc", manifest["retrieved_at_utc"])
    atomic_write(directory / "response.json", raw)
    atomic_write(existing, encode(manifest))
    atomic_write(root / "latest.json", encode({"id": digest, "manifest": str(existing.relative_to(root)).replace("\\", "/")}))
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--count", type=int, default=2)
    parser.add_argument("--bbox", default=DEFAULT_BBOX)
    parser.add_argument("--output", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    try:
        try:
            import truststore
            truststore.inject_into_ssl()
        except ImportError:
            pass
        result = query(args.output, args.date, args.count, args.bbox)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(f"MOSDAC public catalogue query failed: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

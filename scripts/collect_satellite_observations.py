"""Collect one public IMD satellite-derived BUFR product, not satellite imagery."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
import urllib.request


HOST = "wis2box.imd.gov.in"
DATASET = "urn:wmo:md:in-imd:satellite"
NOTIFICATIONS_URL = (
    f"https://{HOST}/oapi/collections/messages/items?f=json&limit=1"
    f"&metadata_id={DATASET}&sortby=-pubtime"
)
MAX_TOTAL_BYTES = 5 * 1024 * 1024
MAX_METADATA_BYTES = 512 * 1024
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "data/ncr/satellite"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_download_url(url: str) -> str:
    parts = urlsplit(url)
    if (
        parts.scheme != "https" or parts.hostname != HOST
        or parts.username is not None or parts.password is not None
        or parts.port not in (None, 443) or parts.query or parts.fragment
        or not parts.path.startswith(f"/data/")
        or "%" in parts.path or ".." in parts.path.split("/")
        or "\\" in url
    ):
        raise ValueError("Satellite payload URL must be an HTTPS IMD /data/ URL")
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Provider redirect refused; verify the new route separately")


class BoundedFetcher:
    def __init__(self):
        self.remaining = MAX_TOTAL_BYTES
        self.opener = urllib.request.build_opener(NoRedirect())

    def __call__(self, url: str, max_bytes: int) -> bytes:
        allowance = min(max_bytes, self.remaining)
        if allowance <= 0:
            raise ValueError("Satellite response budget exhausted")
        request = urllib.request.Request(url, headers={"User-Agent": "SIH26072-research/1.0"})
        with self.opener.open(request, timeout=30) as response:
            length = response.headers.get("Content-Length")
            if length is not None and (int(length) < 0 or int(length) > allowance):
                raise ValueError("Satellite response exceeds byte budget")
            result = bytearray()
            while len(result) < allowance:
                chunk = response.read(min(65536, allowance - len(result)))
                if not chunk:
                    break
                result.extend(chunk)
            # Read one guard byte only when capacity permits within the total budget.
            if len(result) == allowance:
                if allowance >= self.remaining or response.read(1):
                    raise ValueError("Satellite response reached byte budget")
            self.remaining -= len(result)
            return bytes(result)


def bufr_header(payload: bytes) -> dict:
    """Read edition-4 sections 0/1/3; this does not unpack observations."""
    start = payload.find(b"BUFR")
    if start < 0 or len(payload) < start + 8:
        raise ValueError("Satellite payload contains no BUFR message")
    length = int.from_bytes(payload[start + 4:start + 7], "big")
    message = payload[start:start + length]
    if length < 38 or len(message) != length or message[-4:] != b"7777":
        raise ValueError("Truncated or invalid BUFR framing")
    if message[7] != 4:
        raise ValueError("Only BUFR edition 4 header inspection is supported")
    section1_length = int.from_bytes(message[8:11], "big")
    section1 = message[8:8 + section1_length]
    if section1_length < 22 or len(section1) != section1_length:
        raise ValueError("Invalid BUFR identification section")
    try:
        typical = datetime(
            int.from_bytes(section1[15:17], "big"), section1[17], section1[18],
            section1[19], section1[20], section1[21], tzinfo=timezone.utc,
        ).isoformat()
    except ValueError as error:
        raise ValueError("Invalid BUFR typical timestamp") from error
    section3_offset = 8 + section1_length
    if section1[9] & 128:
        optional_length = int.from_bytes(message[section3_offset:section3_offset + 3], "big")
        if optional_length < 4:
            raise ValueError("Invalid optional BUFR section")
        section3_offset += optional_length
    section3_length = int.from_bytes(message[section3_offset:section3_offset + 3], "big")
    section3 = message[section3_offset:section3_offset + section3_length]
    if section3_length < 7 or len(section3) != section3_length or (section3_length - 7) % 2:
        raise ValueError("Invalid BUFR descriptor section")
    section4_offset = section3_offset + section3_length
    section4_length = int.from_bytes(message[section4_offset:section4_offset + 3], "big")
    if section4_length < 4 or section4_offset + section4_length != length - 4:
        raise ValueError("Invalid BUFR data section length")
    descriptors = []
    for index in range(7, len(section3), 2):
        word = int.from_bytes(section3[index:index + 2], "big")
        descriptors.append((word >> 14) * 100000 + ((word >> 8) & 63) * 1000 + (word & 255))
    return {
        "edition": 4, "data_category": section1[10],
        "master_table_version": section1[13], "typical_at_utc": typical,
        "unexpanded_descriptors": descriptors,
        "number_of_subsets_first_message": int.from_bytes(section3[4:6], "big"),
        "first_message_offset": start, "first_message_bytes": length,
        "scope": "First message header only; individual observation times/coordinates not decoded",
    }


def validate_payload(payload: bytes, notification: dict) -> dict:
    links = notification.get("links", [])
    link = next((item for item in links if item.get("rel") == "canonical"), None)
    if link is None:
        raise ValueError("Satellite notification lacks canonical download")
    validate_download_url(link.get("href", ""))
    if link.get("length") != len(payload):
        raise ValueError("Satellite payload length differs from notification")
    integrity = notification.get("properties", {}).get("integrity", {})
    if integrity.get("method") != "sha512":
        raise ValueError("Satellite notification lacks supported SHA-512 integrity")
    try:
        expected = base64.b64decode(integrity["value"], validate=True)
    except (ValueError, KeyError) as error:
        raise ValueError("Invalid satellite notification checksum") from error
    if hashlib.sha512(payload).digest() != expected:
        raise ValueError("Satellite payload checksum mismatch")
    return bufr_header(payload)


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".satellite-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def verify(root: Path) -> dict:
    pointer = json.loads((root / "latest.json").read_text(encoding="utf-8"))
    digest = pointer.get("sha256", "")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError("Invalid satellite snapshot identifier")
    directory = root / "snapshots" / digest
    manifest_bytes = (directory / "manifest.json").read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != pointer.get("manifest_sha256"):
        raise ValueError("Satellite manifest checksum mismatch")
    manifest = json.loads(manifest_bytes)
    raw = (directory / "payload.bufr").read_bytes()
    notification_bytes = (directory / "notification.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Satellite snapshot payload checksum mismatch")
    if hashlib.sha256(notification_bytes).hexdigest() != manifest.get("notification_sha256"):
        raise ValueError("Satellite notification checksum mismatch")
    notification = json.loads(notification_bytes)
    if notification.get("properties", {}).get("metadata_id") != DATASET:
        raise ValueError("Unexpected satellite dataset")
    header = validate_payload(raw, notification)
    if header != manifest.get("bufr_header"):
        raise ValueError("Satellite header differs from manifest")
    if manifest.get("training_ready") is not False or manifest.get("ncr_coverage") != "unknown_pending_decode":
        raise ValueError("Satellite snapshot incorrectly claims training readiness")
    return manifest


def collect(root: Path, fetch=None) -> dict:
    fetch = fetch or BoundedFetcher()
    body = fetch(NOTIFICATIONS_URL, MAX_METADATA_BYTES)
    if len(body) > MAX_METADATA_BYTES:
        raise ValueError("Notification response exceeds budget")
    response = json.loads(body)
    features = response.get("features", [])
    if not features:
        raise ValueError("No IMD satellite notifications returned")
    notification = features[0]
    properties = notification.get("properties", {})
    if properties.get("metadata_id") != DATASET:
        raise ValueError("Unexpected satellite dataset")
    link = next((item for item in notification.get("links", []) if item.get("rel") == "canonical"), None)
    if not link:
        raise ValueError("Satellite notification lacks canonical download")
    url = validate_download_url(link.get("href", ""))
    length = link.get("length")
    if not isinstance(length, int) or isinstance(length, bool) or length <= 0 or length > MAX_TOTAL_BYTES - len(body):
        raise ValueError("Satellite payload advertised length exceeds budget")
    payload = fetch(url, length)
    if len(body) + len(payload) > MAX_TOTAL_BYTES:
        raise ValueError("Satellite collection exceeds total byte budget")
    header = validate_payload(payload, notification)
    digest = hashlib.sha256(payload).hexdigest()
    directory = root / "snapshots" / digest
    notification_bytes = json_bytes(notification)
    manifest = {
        "sha256": digest, "provider": "India Meteorological Department",
        "dataset": DATASET, "source_url": url, "notifications_url": NOTIFICATIONS_URL,
        "retrieved_at_utc": utc_now(), "published_at_utc": properties.get("pubtime"),
        "notification_datetime": properties.get("datetime"), "bufr_header": header,
        "payload_bytes": len(payload), "notification_sha256": hashlib.sha256(notification_bytes).hexdigest(),
        "kind": "satellite_derived_winds_bufr" if header["data_category"] == 5 else "satellite_derived_bufr_unclassified",
        "imagery": False, "training_ready": False, "ncr_coverage": "unknown_pending_decode",
        "limitations": ["Full BUFR measurements not decoded", "NCR coverage and individual observation timestamps unverified", "Not calibrated satellite image arrays or rain/lightning training labels"],
    }
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("sha256") != digest:
            raise ValueError("Existing snapshot identity conflict")
        # Preserve first successful retrieval; content-derived paths converge on reruns.
        manifest["retrieved_at_utc"] = existing.get("retrieved_at_utc", manifest["retrieved_at_utc"])
    manifest_bytes = json_bytes(manifest)
    atomic_write(directory / "payload.bufr", payload)
    atomic_write(directory / "notification.json", notification_bytes)
    atomic_write(manifest_path, manifest_bytes)
    atomic_write(root / "latest.json", json_bytes({"sha256": digest, "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest()}))
    return verify(root)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--verify-only", action="store_true", help="Verify saved bytes without any HTTP request")
    args = parser.parse_args(argv)
    try:
        if args.verify_only:
            result = verify(args.output)
        else:
            try:
                import truststore
                truststore.inject_into_ssl()
            except ImportError:
                pass
            result = collect(args.output)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(f"Satellite collection failed: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

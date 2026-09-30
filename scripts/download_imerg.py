"""Download one discovered IMERG file after local Earthdata credentials are configured.

This writes a raw scientific file, not aligned/quality-screened NCR training labels.
The public catalogue collector must run first. No credentials are written to disk.
"""
import argparse
import json
import logging
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nowcast import supplemental_data as data

LIMIT = 64_000_000
NASA_HOSTS = {"data.gesdisc.earthdata.nasa.gov", "gpm1.gesdisc.eosdis.nasa.gov"}


def data_url(row):
    candidates = []
    for link in row["links"]:
        parsed = urlsplit(link["href"])
        if (parsed.scheme == "https" and parsed.hostname in NASA_HOSTS and not parsed.query
                and not parsed.username and not parsed.password and parsed.path.endswith(".HDF5")
                and link.get("rel", "").endswith("/data#")):
            candidates.append(link["href"])
    if len(candidates) != 1:
        raise ValueError("Expected exactly one supported NASA HTTPS scientific file link")
    return candidates[0]


def authenticated_session():
    if not (os.environ.get("EARTHDATA_TOKEN") or
            (os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD"))):
        raise ValueError("Configure local Earthdata environment credentials first; never commit or paste them")
    try:
        import earthaccess
    except ImportError:
        raise ValueError("Install the optional earthaccess package in your data environment") from None
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass
    # Some SDK error logs contain authentication response bodies. Our CLI prints only a safe error type.
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        try:
            auth = earthaccess.login(strategy="environment", persist=False)
            if not auth.authenticated:
                raise RuntimeError("Earthdata authentication was not accepted")
            return earthaccess.get_requests_https_session()
        except Exception:
            raise RuntimeError("Earthdata authentication failed; check local setup") from None
    finally:
        logging.disable(previous)


def download(row, output_root: Path, session_factory=authenticated_session):
    url = data_url(row)
    granule_id = row["granule_id"]
    if not re.fullmatch(r"G[0-9]+-GES_DISC", granule_id):
        raise ValueError("Unexpected GES DISC granule identity")
    destination = output_root / granule_id
    if destination.exists():
        manifest = json.loads((destination / "manifest.json").read_bytes())
        payload = (destination / "precipitation.HDF5").read_bytes()
        if manifest["url"] != url or manifest["sha256"] != data.sha(payload):
            raise ValueError("Existing IMERG file failed integrity verification")
        return manifest
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".imerg-stage-", dir=output_root) as name:
        stage = Path(name) / "snapshot"
        stage.mkdir()
        session = session_factory()
        try:
            with session.get(url, stream=True, timeout=(15, 120), allow_redirects=False) as response:
                if response.status_code != 200:
                    raise ValueError(f"NASA download returned HTTP {response.status_code}; check application authorization or changed download service")
                size = 0
                with (stage / "precipitation.HDF5").open("wb") as stream:
                    for chunk in response.iter_content(65536):
                        size += len(chunk)
                        if size > LIMIT:
                            raise ValueError("IMERG file exceeds the 64 MB sample limit")
                        stream.write(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
        finally:
            session.close()
        payload = (stage / "precipitation.HDF5").read_bytes()
        if not payload.startswith(b"\x89HDF\r\n\x1a\n"):
            raise ValueError("NASA response is not an HDF5 scientific file")
        manifest = {"granule_id": granule_id, "url": url, "sha256": data.sha(payload), "bytes": len(payload),
                    "retrieved_at_utc": data.utc_now(), "interval_start_utc": row["interval_start_utc"],
                    "interval_end_utc": row["interval_end_utc"], "scope": "global native IMERG granule intersecting NCR",
                    "scientific_payload_downloaded": True, "quality_screened": False,
                    "label_eligible": False, "note": "HDF5 container signature checked; scientific field decoding and quality screening still required."}
        (stage / "manifest.json").write_bytes(data.encode(manifest))
        try:
            stage.rename(destination)
        except OSError:
            if not destination.exists():
                raise
            return download(row, output_root, session_factory)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogue-root", type=Path, default=data.DEFAULT_ROOT)
    parser.add_argument("--index", type=int, default=0, help="One item from latest bounded IMERG catalogue")
    parser.add_argument("--output-root", type=Path, default=data.ROOT / "data/ncr/imerg")
    args = parser.parse_args()
    try:
        manifest = data.latest(args.catalogue_root, "imerg")
        if not manifest:
            raise ValueError("Run the public IMERG catalogue collector first")
        rows = data.read_rows(args.catalogue_root, manifest)
        if not 0 <= args.index < len(rows):
            raise ValueError("Requested catalogue index is unavailable")
        result = download(rows[args.index], args.output_root)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"status": "unavailable", "error_type": type(error).__name__,
                          "reason": str(error) if isinstance(error, ValueError) else "NASA access failed; verify local credentials, authorization and SDK installation"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

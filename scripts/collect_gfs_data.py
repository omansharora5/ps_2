"""Collect a bounded NOAA GFS field subset and decode a Bihar-area example.

Run with Python and requests. On Windows --decode downloads the official NOAA
wgrib2 3.1.3 executable and its DLLs into tools/wgrib2; no system install occurs.
On other systems provide a compatible wgrib2 executable on PATH.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/government/gfs"
URL = "https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.20250512/06/atmos/gfs.t06z.pgrb2.0p25.f003"
DOC = "https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast"
TERMS = "https://www.weather.gov/disclaimer"
SELECT = [("TMP", "2 m above ground"), ("RH", "2 m above ground"),
          ("UGRD", "10 m above ground"), ("VGRD", "10 m above ground"),
          ("CAPE", "surface"), ("CIN", "surface"),
          ("PWAT", "entire atmosphere (considered as a single layer)")]
UNITS = {"TMP": "K", "RH": "%", "UGRD": "m/s", "VGRD": "m/s",
         "CAPE": "J/kg", "CIN": "J/kg", "PWAT": "kg/m^2"}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".part")
    temp.write_bytes(payload)
    temp.replace(path)


def fetch(url, limit, byte_range=None):
    headers = {"User-Agent": "VAJRA-research-starter-pack/1.0"}
    if byte_range:
        headers["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"
    with requests.get(url, headers=headers, stream=True, timeout=(15, 45)) as response:
        response.raise_for_status()
        if byte_range:
            expected = f"bytes {byte_range[0]}-{byte_range[1]}/"
            if response.status_code != 206 or not response.headers.get("Content-Range", "").startswith(expected):
                raise ValueError("Server did not honor exact bounded Range request")
        payload = bytearray()
        for chunk in response.iter_content(65536):
            payload.extend(chunk)
            if len(payload) > limit:
                raise ValueError("Download exceeds declared limit")
        return bytes(payload), dict(response.headers)


def validate_grib(payload, expected_messages=7):
    pos = 0
    count = 0
    while pos < len(payload):
        if pos + 16 > len(payload):
            raise ValueError("Truncated GRIB header")
        if payload[pos:pos + 4] != b"GRIB" or payload[pos + 7] != 2:
            raise ValueError("Expected complete GRIB edition 2 message")
        size = int.from_bytes(payload[pos + 8:pos + 16], "big")
        if size < 20 or pos + size > len(payload) or payload[pos + size - 4:pos + size] != b"7777":
            raise ValueError("Truncated GRIB message")
        pos += size
        count += 1
    if pos != len(payload) or count != expected_messages:
        raise ValueError(f"Expected {expected_messages} complete messages, found {count}")
    return count


def record(path, url, role, retrieved, **extras):
    payload = path.read_bytes()
    return {"id": "gfs-" + path.stem, "path": path.relative_to(ROOT).as_posix(),
            "source_url": url, "provider": "NOAA/NCEP", "documentation_url": DOC,
            "retrieved_at_utc": retrieved, "bytes": len(payload), "sha256": sha(payload),
            "format": path.suffix.lstrip("."), "data_role": role,
            "licence_terms_url": TERMS,
            "licence_note": "NOAA/NWS government information; acknowledge provider, no endorsement. See source disclaimer.",
            "model_reference_time_utc": "2025-05-12T06:00:00Z", "forecast_lead_hours": 3,
            "valid_time_utc": "2025-05-12T09:00:00Z", "historical_available_at_utc": None,
            "not_training_ready_reason": "One forecast time, no matched Indian storm/flash labels; historic operational availability not established.",
            **extras}


def collect():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in manifest["files"]:
            path = ROOT / item["path"]
            if not path.exists() or sha(path.read_bytes()) != item["sha256"]:
                raise ValueError(f"Existing pinned file missing/corrupt: {path}")
        print("Verified existing GFS snapshot")
        return manifest
    index, index_headers = fetch(URL + ".idx", 100_000)
    lines = [line.split(":") for line in index.decode("utf-8").splitlines()]
    chunks, ranges = [], []
    for variable, level in SELECT:
        matches = [(i, parts) for i, parts in enumerate(lines) if parts[3:5] == [variable, level]]
        if len(matches) != 1:
            raise ValueError(f"Ambiguous inventory entry: {variable}, {level}")
        i, parts = matches[0]
        start, end = int(parts[1]), int(lines[i + 1][1]) - 1
        if end - start > 2_000_000:
            raise ValueError("Unexpectedly large field")
        payload, headers = fetch(URL, 2_000_000, (start, end))
        validate_grib(payload, 1)
        chunks.append(payload)
        ranges.append({"variable": variable, "level": level, "units": UNITS[variable],
                       "byte_start": start, "byte_end_inclusive": end, "sha256": sha(payload),
                       "archive_last_modified_header": headers.get("Last-Modified"),
                       "etag": headers.get("ETag")})
        print(f"Downloaded {variable}: {len(payload):,} bytes", flush=True)
    combined = b"".join(chunks)
    validate_grib(combined)
    retrieved = now()
    index_path = OUT / "gfs_20250512_06_f003.idx"
    raw_path = OUT / "gfs_20250512_06_f003_selected.grib2"
    save(index_path, index)
    save(raw_path, combined)
    manifest = {"schema_version": 1, "collection": "NOAA GFS selected-field starter sample",
                "created_at_utc": retrieved,
                "notes": ["Seven original GRIB messages concatenated in listed order; no values changed.",
                          "HTTP Last-Modified is archive-object metadata, not proof of historical real-time availability.",
                          "GFS forecast values are model output, not direct surface observations."],
                "files": [record(index_path, URL + ".idx", "provider_inventory", retrieved,
                                 archive_last_modified_header=index_headers.get("Last-Modified")),
                          record(raw_path, URL, "raw_nwp_forecast", retrieved, fields=ranges,
                                 geography={"coverage": "global including India", "grid_degrees": 0.25},
                                 acquisition="HTTP byte ranges specified by provider inventory")],
                "derived_files": []}
    save(manifest_path, json.dumps(manifest, indent=2).encode("utf-8"))
    return manifest


def wgrib2():
    if os.name != "nt":
        result = shutil.which("wgrib2")
        if not result:
            raise RuntimeError("Install wgrib2 to decode the already downloaded GRIB files")
        return result
    folder = ROOT / "tools/wgrib2"
    folder.mkdir(parents=True, exist_ok=True)
    meta_path = folder / "provenance.json"
    metadata = json.loads(meta_path.read_text()) if meta_path.exists() else {"files": []}
    existing = {x["name"]: x for x in metadata["files"]}
    for name in ["wgrib2.exe", "cyggcc_s-seh-1.dll", "cyggfortran-5.dll", "cyggomp-1.dll", "cygquadmath-0.dll", "cygwin1.dll"]:
        path = folder / name
        if name in existing and path.exists() and sha(path.read_bytes()) == existing[name]["sha256"]:
            continue
        url = "https://ftp.cpc.ncep.noaa.gov/wd51we/wgrib2/Windows10/v3.1.3/" + name
        payload, _ = fetch(url, 6_000_000)
        if not payload.startswith(b"MZ"):
            raise ValueError("Expected Windows executable/library")
        if name in existing and sha(payload) != existing[name]["sha256"]:
            raise ValueError("Official decoder differs from previously pinned version")
        save(path, payload)
        existing[name] = {"name": name, "source_url": url, "sha256": sha(payload),
                          "bytes": len(payload), "retrieved_at_utc": now()}
        metadata["files"] = list(existing.values())
        save(meta_path, json.dumps(metadata, indent=2).encode())
    return str(folder / "wgrib2.exe")


def decode(manifest):
    if manifest.get("derived_files"):
        for item in manifest["derived_files"]:
            path = ROOT / item["path"]
            if not path.exists() or sha(path.read_bytes()) != item["sha256"]:
                raise ValueError(f"Existing derived file missing/corrupt: {path}")
        print("Verified existing regional GRIB and CSV; no files rewritten")
        return
    binary = wgrib2()
    raw = OUT / "gfs_20250512_06_f003_selected.grib2"
    region = OUT / "gfs_20250512_06_f003_bihar.grib2"
    csv_path = OUT / "gfs_20250512_06_f003_bihar.csv"
    # Cygwin wgrib2 runs with project-relative paths from the project directory.
    env = dict(os.environ, OMP_NUM_THREADS="2")
    def run(args):
        result = subprocess.run([binary, *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120, check=True)
        return result.stdout
    def relative(path):
        return path.relative_to(ROOT).as_posix()
    inventory = run([relative(raw), "-s", "-grid"])
    run([relative(raw), "-small_grib", "82:89", "23:28", relative(region)])
    validate_grib(region.read_bytes())
    run([relative(region), "-csv", relative(csv_path)])
    rows = list(csv.reader(io.StringIO(csv_path.read_text())))
    if len(rows) != 7 * 29 * 21 or {r[2] for r in rows} != {v for v, _ in SELECT}:
        raise ValueError(f"Unexpected decoded dimensions/variables: {len(rows)} rows")
    summary = {}
    for var, level in SELECT:
        group = [r for r in rows if r[2] == var]
        values = [float(r[6]) for r in group]
        if any(not (23 <= float(r[5]) <= 28 and 82 <= float(r[4]) <= 89) for r in group):
            raise ValueError("Subset outside requested bounds")
        nearest = min(group, key=lambda r: (float(r[5]) - 25.594)**2 + (float(r[4]) - 85.138)**2)
        summary[var] = {"level": level, "units": UNITS[var], "rows": len(group), "min": min(values),
                        "max": max(values), "patna_nearest_grid_point": {"lat": float(nearest[5]),
                        "lon": float(nearest[4]), "value": float(nearest[6])}}
    info = {"decoder": "NOAA wgrib2 3.1.3", "grid_shape_lat_lon": [21, 29], "csv_rows": len(rows),
            "csv_has_header": False, "csv_columns": ["reference_time_UTC", "valid_time_UTC", "variable", "level", "longitude", "latitude", "value"],
            "geography": {"west": 82, "east": 89, "south": 23, "north": 28, "spacing_degrees": 0.25},
            "variables": summary, "source_inventory": inventory}
    save(OUT / "inspection.json", json.dumps(info, indent=2).encode())
    manifest["derived_files"] = [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
                                  "sha256": sha(p.read_bytes()), "derived_from": relative(raw),
                                  "transformation": "wgrib2 -small_grib 82:89 23:28, then -csv; no unit conversion",
                                  "generated_at_utc": now()} for p in [region, csv_path]]
    save(OUT / "manifest.json", json.dumps(manifest, indent=2).encode())
    print(json.dumps({"decoded_rows": len(rows), "variables": summary}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decode", action="store_true")
    parser.add_argument("--verify-only", action="store_true", help="Verify saved raw and derived files without network or writes")
    args = parser.parse_args()
    if args.verify_only:
        manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
        for item in manifest["files"] + manifest.get("derived_files", []):
            path = ROOT / item["path"]
            payload = path.read_bytes()
            if len(payload) != item["bytes"] or sha(payload) != item["sha256"]:
                raise ValueError(f"Checksum/size failure: {path}")
            if path.suffix == ".grib2":
                validate_grib(payload)
        with (OUT / "gfs_20250512_06_f003_bihar.csv").open(newline="") as stream:
            rows = list(csv.reader(stream))
        if len(rows) != 4263 or {r[2] for r in rows} != {v for v, _ in SELECT}:
            raise ValueError("Regional CSV cardinality/variables changed")
        if any(r[0] != "2025-05-12 06:00:00" or r[1] != "2025-05-12 09:00:00" for r in rows):
            raise ValueError("Unexpected forecast reference/valid times")
        print("Verified GFS raw/derived hashes, 7 complete messages and 4,263 decoded rows")
        raise SystemExit(0)
    manifest = collect()
    if args.decode:
        decode(manifest)

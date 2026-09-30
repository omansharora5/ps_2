"""Collect a fixed, small NOAA parser/reference sample; never trains a model.

Run with .venv-data/Scripts/python.exe after installing netCDF4==1.7.4
and metpy==1.7.1. --verify-only performs no network requests or writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/government/noaa"
MANIFEST = DEST / "manifest.json"
BUDGET = 40_000_000
ABI_CATALOG = "https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C01502"
GLM_CATALOG = "https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc:C01527/html"
RADAR_CATALOG = "https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C00708"
TERMS = "https://www.ncei.noaa.gov/sites/default/files/2023-12/NCEI%20PD-10-2-02%20-%20Open%20Data%20Policy%20Signed.pdf"
GOES_BASE = "https://noaa-goes16.s3.amazonaws.com/"
SPECS = [
    ("abi_c13", "ABI-L2-CMIPC/2024/167/18/OR_ABI-L2-CMIPC-M6C13_G16_s20241671801178_e20241671803563_c20241671804099.nc", 4_089_488),
    ("glm_180200", "GLM-L2-LCFA/2024/167/18/OR_GLM-L2-LCFA_G16_s20241671802000_e20241671802200_c20241671802222.nc", 188_220),
    ("glm_180220", "GLM-L2-LCFA/2024/167/18/OR_GLM-L2-LCFA_G16_s20241671802200_e20241671802400_c20241671802416.nc", 202_556),
    ("glm_180240", "GLM-L2-LCFA/2024/167/18/OR_GLM-L2-LCFA_G16_s20241671802400_e20241671803000_c20241671803014.nc", 198_460),
    ("radar_ktlx_n0b", "TLX_N0B_2024_06_15_18_05_28", 255_950),
]
SHA256_PINS = {
    "abi_c13": "1edd2c976c83a64635a6ff4a7374e1a8e1354696714dfadd965f9cc9716d5752",
    "glm_180200": "0638d2efbf87c28880e9e84bdc1e52fa692cce822242db500d9354bf9e027086",
    "glm_180220": "2f7b7194f5581c9499a103f5959d1545d27615a316ca43035a11bd09a91561f5",
    "glm_180240": "d3794a3c37203d2355f6e70f1b6777686ce9b0550cae8f84cfdd943e674c9705",
    "radar_ktlx_n0b": "9ee062530322b3cee3b974b36a1d0e39ed5d3895ec4c742625bc1875df05b9ea",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_json(path, value):
    content = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    fd, temp = tempfile.mkstemp(prefix=path.name, suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def plain(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def stats(array):
    import numpy as np
    values = np.ma.asarray(array).compressed()
    values = values[np.isfinite(values)]
    return {"shape": list(array.shape), "finite_unmasked_count": int(values.size),
            "min": float(values.min()) if values.size else None,
            "max": float(values.max()) if values.size else None}


def inspect_netcdf(path, identifier):
    import netCDF4
    import numpy as np
    with path.open("rb") as stream:
        if stream.read(8) != b"\x89HDF\r\n\x1a\n":
            raise ValueError("Not an HDF5-backed NetCDF4 file")
    with netCDF4.Dataset(path) as data:
        if data.getncattr("platform_ID") != "G16":
            raise ValueError("Unexpected satellite")
        start = str(data.getncattr("time_coverage_start"))
        end = str(data.getncattr("time_coverage_end"))
        if not start.startswith("2024-06-15T18:"):
            raise ValueError("Unexpected observation day/hour")
        variables = {}
        names = ["CMI", "DQF", "x", "y", "band_id", "band_wavelength", "t"] if identifier == "abi_c13" else [
            "event_lat", "event_lon", "event_energy", "event_time_offset", "event_parent_group_id",
            "group_id", "group_parent_flash_id", "group_quality_flag", "group_energy",
            "flash_id", "flash_lat", "flash_lon", "flash_energy", "flash_area",
            "flash_time_offset_of_first_event", "flash_time_offset_of_last_event", "flash_quality_flag"]
        for name in names:
            var = data.variables[name]
            variables[name] = {"stored_dtype": str(var.dtype), "dimensions": list(var.dimensions),
                               "units": str(getattr(var, "units", "1")), **stats(var[:])}
            for attr in ["scale_factor", "add_offset", "_Unsigned", "_FillValue", "flag_values", "flag_meanings"]:
                if attr in var.ncattrs():
                    variables[name][attr] = plain(var.getncattr(attr))
        result = {"format": data.data_model, "observation_time_start_utc": start,
                  "observation_time_end_utc": end,
                  "historical_available_at_utc": None,
                  "creation_time_utc": str(getattr(data, "date_created", "")),
                  "dimensions": {k: len(v) for k, v in data.dimensions.items()},
                  "variables": variables,
                  "decoding": "netCDF4 automatic masking and scale/offset enabled; raw files unchanged"}
        if identifier == "abi_c13":
            if int(data.variables["band_id"][:].item()) != 13 or data.variables["CMI"].shape != (1500, 2500):
                raise ValueError("Unexpected ABI channel/CONUS dimensions")
            projection = data.variables["goes_imager_projection"]
            result["projection"] = {k: plain(projection.getncattr(k)) for k in projection.ncattrs()}
            result["geography"] = {"region": "GOES-16 ABI CONUS scene; United States and surrounding area, not India",
                                   "grid": "geostationary fixed grid; x/y scanning angles in radians"}
            quality = data.variables["DQF"][:].compressed()
            result["quality_counts"] = {str(int(v)): int((quality == v).sum()) for v in np.unique(quality)}
        else:
            events = data.variables["event_parent_group_id"][:]
            groups = data.variables["group_id"][:]
            parents = data.variables["group_parent_flash_id"][:]
            flashes = data.variables["flash_id"][:]
            if not np.isin(events, groups).all() or not np.isin(parents, flashes).all():
                raise ValueError("Broken event/group/flash parent reference")
            result["parent_relationships_valid"] = True
            result["counts"] = {"events": int(events.size), "groups": int(groups.size), "flashes": int(flashes.size)}
            result["geography"] = {"region": "GOES-16 GLM hemispheric field of view; Americas and adjacent oceans, not India",
                                   "actual_event_latitude_range_degrees_north": [variables["event_lat"]["min"], variables["event_lat"]["max"]],
                                   "actual_event_longitude_range_degrees_east": [variables["event_lon"]["min"], variables["event_lon"]["max"]]}
        return result


def inspect_radar(path):
    import numpy as np
    from metpy.io import Level3File
    data = Level3File(path)
    if data.siteID != "TLX":
        raise ValueError(f"Unexpected radar site {data.siteID!r}")
    if data.header.code != 153:
        raise ValueError(f"Unexpected radar product code {data.header.code}")
    packet = data.sym_block[0][0]
    raw = np.asarray(packet["data"])
    decoded = np.asarray(data.map_data(raw))
    scan = data.metadata["vol_time"].isoformat() + "Z"
    return {"format": "NEXRAD Level III binary NIDS, product 153 N0B",
            "observation_time_start_utc": scan, "observation_time_end_utc": None,
            "time_note": "Header volume start; complete scan end not asserted",
            "historical_available_at_utc": None,
            "product_time_utc": data.metadata["prod_time"].isoformat() + "Z",
            "geography": {"region": "KTLX radar around Oklahoma City, Oklahoma, United States; not India",
                           "station_latitude_degrees_north": data.lat, "station_longitude_degrees_east": data.lon,
                           "maximum_range_km": float(data.max_range)},
            "variables": {"reflectivity": {"units": "dBZ", "stored_dtype": str(raw.dtype), **stats(decoded)},
                          "start_az": {"units": "degrees", **stats(np.asarray(packet["start_az"]))},
                          "end_az": {"units": "degrees", **stats(np.asarray(packet["end_az"]))}},
            "decoding": "MetPy Level3File.map_data converts encoded levels; finite min/max exclude missing/range-fold values"}


def inspect(path, identifier):
    return inspect_radar(path) if identifier.startswith("radar") else inspect_netcdf(path, identifier)


def download(url, destination, expected_size, identifier):
    fd, temp = tempfile.mkstemp(prefix=destination.name, suffix=".part", dir=destination.parent)
    os.close(fd)
    size = 0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SIH26072-NOAA-reference-collector/1.0", "Accept-Encoding": "identity"})
        with urllib.request.urlopen(req, timeout=45) as response, open(temp, "wb") as stream:
            content_type = response.headers.get("Content-Type", "")
            if "html" in content_type.lower():
                raise ValueError("Server returned HTML instead of data")
            length = response.headers.get("Content-Length")
            if length is not None and int(length) != expected_size:
                raise ValueError(f"Unexpected HTTP content length: {length}")
            while chunk := response.read(256 * 1024):
                size += len(chunk)
                if size > expected_size:
                    raise ValueError("Download exceeds fixed per-file budget")
                stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        if size != expected_size:
            raise ValueError(f"Incomplete download: {size}/{expected_size}")
        if checksum(Path(temp)) != SHA256_PINS[identifier]:
            raise ValueError("Downloaded bytes differ from the pinned original sample")
        parsed = inspect(Path(temp), identifier)
        if destination.exists():
            raise FileExistsError(f"Refusing to replace raw data: {destination}")
        os.replace(temp, destination)
        return parsed
    finally:
        Path(temp).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if sum(size for _, _, size in SPECS) > BUDGET:
        raise ValueError("Fixed collection exceeds 40 MB")
    if args.verify_only and not MANIFEST.exists():
        raise FileNotFoundError("No prior manifest to verify")
    if not args.verify_only:
        DEST.mkdir(parents=True, exist_ok=True)
        (DEST / "raw").mkdir(exist_ok=True)
    prior = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    existing = {row["id"]: row for row in prior.get("files", [])}
    lock = DEST / ".collector.lock"
    if not args.verify_only:
        with lock.open("x") as stream:
            stream.write(str(os.getpid()))
    rows = []
    created_at = prior.get("created_at_utc", utc_now())
    current_url = None
    try:
        for identifier, key, expected_size in SPECS:
            radar = identifier.startswith("radar")
            current_url = ("https://unidata-nexrad-level3.s3.amazonaws.com/" if radar else GOES_BASE) + key
            target = DEST / "raw" / Path(key).name
            old = existing.get(identifier)
            if target.exists():
                if (old is None or target.stat().st_size != expected_size
                        or checksum(target) != old["sha256"] or old["sha256"] != SHA256_PINS[identifier]):
                    raise ValueError(f"Untracked or changed raw data: {target.name}; refusing overwrite")
                parsed = inspect(target, identifier)
                retrieved_at = old["retrieved_at_utc"]
                print(f"Verified existing {identifier}")
            else:
                if args.verify_only:
                    raise FileNotFoundError(target)
                parsed = download(current_url, target, expected_size, identifier)
                retrieved_at = utc_now()
                print(f"Downloaded and parsed {identifier} ({expected_size:,} bytes)", flush=True)
            catalog = RADAR_CATALOG if radar else (ABI_CATALOG if identifier == "abi_c13" else GLM_CATALOG)
            rows.append({"id": identifier, "path": target.relative_to(ROOT).as_posix(),
                         "source_url": current_url, "provider": "NOAA/NWS" if radar else "NOAA/NESDIS/OSPO",
                         "distribution": "UCAR Unidata AWS mirror of NOAA NEXRAD" if radar else "NOAA GOES-16 AWS public archive",
                         "official_catalog_url": catalog, "retrieved_at_utc": retrieved_at,
                         "bytes": target.stat().st_size, "sha256": checksum(target),
                         "licence_terms_url": TERMS,
                         "licence_note": "NOAA-produced data public domain in the United States; retain attribution and dataset-specific use constraints; no NOAA endorsement",
                         "dataset_use_constraints_url": catalog,
                         "units": {k: v["units"] for k, v in parsed["variables"].items()},
                         "data_role": "parser_reference_only",
                         "not_training_ready_reason": "Tiny historical non-Indian sample; missing continuous causal inputs, future labels, regional alignment, storm splits and operational availability history",
                         **parsed})
            if not args.verify_only:
                checkpoints = {**existing, **{row["id"]: row for row in rows}}
                atomic_json(MANIFEST, {"schema_version": 1, "collection_id": "noaa_20240615_parser_reference",
                                      "created_at_utc": created_at, "status": "incomplete",
                                      "files": [checkpoints[name] for name, _, _ in SPECS if name in checkpoints]})
        result = {"schema_version": 1, "collection_id": "noaa_20240615_parser_reference",
                  "created_at_utc": created_at, "status": "complete", "max_raw_bytes": BUDGET,
                  "total_raw_bytes": sum(r["bytes"] for r in rows), "training_ready": False,
                  "historical_availability_note": "Retrieval time and product creation time are not proof of original operational availability",
                  "files": rows}
        if args.verify_only:
            if result != prior:
                raise ValueError("Decoded metadata differs from recorded manifest")
        else:
            atomic_json(MANIFEST, result)
        print(f"PASS: {len(rows)} authentic numeric files, {result['total_raw_bytes']:,} bytes; training_ready=false")
    except Exception as error:
        if not args.verify_only:
            failure_path = DEST / "download_failures.json"
            failures = json.loads(failure_path.read_text(encoding="utf-8")) if failure_path.exists() else []
            failures.append({"at_utc": utc_now(), "source_url": current_url, "error": f"{type(error).__name__}: {error}"})
            atomic_json(failure_path, failures)
        raise
    finally:
        if not args.verify_only:
            lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

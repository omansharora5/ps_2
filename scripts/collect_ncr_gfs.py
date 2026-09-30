"""Collect seven NCR GFS context fields, preserving forecast and retrieval times.

Example: python scripts/collect_ncr_gfs.py --date 2026-09-30 --cycle 12 --lead 3
Requires requests and an existing wgrib2 installation; no decoder is downloaded.
Re-running verifies and reuses the same snapshot. --verify-only performs no I/O
outside the selected local snapshot and does not contact a provider.
"""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.collect_gfs_data import SELECT, UNITS, fetch, sha, validate_grib

BOUNDS = {"west": 76.5, "east": 78.25, "south": 28.0, "north": 29.5}
GRID_STEP = 0.25
CSV_COLUMNS = ["model_reference_time_utc", "valid_time_utc", "variable", "level",
               "longitude", "latitude", "value"]
OUTPUT_LIMIT = 2_000_000
FIELD_LIMIT = 2_000_000
EXPECTED_ROWS = len(SELECT) * 8 * 7


def forecast_spec(date, cycle, lead):
    day = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if day.strftime("%Y-%m-%d") != date or cycle not in (0, 6, 12, 18):
        raise ValueError("Use an ISO date and a GFS cycle of 00, 06, 12 or 18 UTC")
    if not isinstance(lead, int) or isinstance(lead, bool) or not 0 <= lead <= 120:
        raise ValueError("This bounded hourly collector supports lead hours 0–120")
    reference = day.replace(hour=cycle)
    valid = reference + timedelta(hours=lead)
    day_text = reference.strftime("%Y%m%d")
    filename = f"gfs.t{cycle:02d}z.pgrb2.0p25.f{lead:03d}"
    return {"date": date, "cycle": cycle, "forecast_lead_hours": lead,
            "model_reference_time_utc": reference.isoformat().replace("+00:00", "Z"),
            "valid_time_utc": valid.isoformat().replace("+00:00", "Z"),
            "snapshot_id": f"gfs_{day_text}_{cycle:02d}_f{lead:03d}_ncr",
            "source_url": f"https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{day_text}/{cycle:02d}/atmos/{filename}"}


def select_ranges(index, spec):
    lines = [line.split(":") for line in index.decode("utf-8").splitlines() if line.strip()]
    if not lines or any(len(line) < 6 for line in lines):
        raise ValueError("Malformed GFS inventory")
    offsets = [int(line[1]) for line in lines]
    if offsets[0] < 0 or any(b <= a for a, b in zip(offsets, offsets[1:])):
        raise ValueError("GFS inventory offsets are not strictly increasing")
    date_code = "d=" + spec["model_reference_time_utc"][:13].replace("-", "").replace("T", "")
    forecast = "anl" if spec["forecast_lead_hours"] == 0 else f"{spec['forecast_lead_hours']} hour fcst"
    result = []
    for variable, level in SELECT:
        matches = [i for i, line in enumerate(lines) if line[3:5] == [variable, level]]
        if len(matches) != 1 or matches[0] + 1 >= len(lines):
            raise ValueError(f"Missing, ambiguous or unbounded inventory field: {variable}")
        i = matches[0]
        if lines[i][2] != date_code or lines[i][5] != forecast:
            raise ValueError("Inventory initialization/forecast time does not match request")
        start, end = offsets[i], offsets[i + 1] - 1
        if end - start + 1 > FIELD_LIMIT:
            raise ValueError("GFS field exceeds bounded download size")
        result.append({"variable": variable, "level": level, "units": UNITS[variable],
                       "byte_start": start, "byte_end_inclusive": end})
    return result


def decoder_path():
    local = ROOT / "tools/wgrib2/wgrib2.exe"
    provenance = local.parent / "provenance.json"
    if os.name == "nt" and local.exists() and provenance.exists():
        entries = json.loads(provenance.read_text(encoding="utf-8"))["files"]
        if not any(item["name"] == "wgrib2.exe" for item in entries):
            raise ValueError("Decoder executable lacks pinned provenance")
        for item in entries:
            path = local.parent / item["name"]
            if path.parent != local.parent or not path.is_file() or sha(path.read_bytes()) != item["sha256"]:
                raise ValueError("Existing NOAA decoder or dependency failed checksum verification")
        return str(local)
    binary = shutil.which("wgrib2")
    if not binary:
        raise RuntimeError("An existing wgrib2 is required; install it or use the project's tools/wgrib2 installation")
    return binary


def validate_csv(payload, spec):
    rows = list(csv.reader(io.StringIO(payload.decode("utf-8"))))
    if len(rows) != EXPECTED_ROWS or any(len(row) != 7 for row in rows):
        raise ValueError("Unexpected NCR CSV dimensions")
    reference = spec["model_reference_time_utc"].replace("T", " ").rstrip("Z")
    valid = spec["valid_time_utc"].replace("T", " ").rstrip("Z")
    expected_fields = set(SELECT)
    seen = set()
    for row in rows:
        if row[0] != reference or row[1] != valid or tuple(row[2:4]) not in expected_fields:
            raise ValueError("Decoded field or forecast times do not match the selected run")
        lon, lat, value = map(float, row[4:7])
        if not all(map(math.isfinite, (lon, lat, value))) or abs(value) >= 9e19:
            raise ValueError("Missing or nonfinite GFS sample")
        if not (BOUNDS["west"] <= lon <= BOUNDS["east"] and BOUNDS["south"] <= lat <= BOUNDS["north"]):
            raise ValueError("Decoded sample lies outside NCR pilot bounds")
        if abs(lon / GRID_STEP - round(lon / GRID_STEP)) > 1e-6 or abs(lat / GRID_STEP - round(lat / GRID_STEP)) > 1e-6:
            raise ValueError("Decoded sample is not on the expected 0.25-degree grid")
        cell = (row[2], row[3], lon, lat)
        if cell in seen:
            raise ValueError("Duplicate NCR field/grid cell")
        seen.add(cell)
    return rows


def decode(binary, folder, spec):
    def run(args):
        subprocess.run([binary, *args], cwd=folder, env=dict(os.environ, OMP_NUM_THREADS="2"),
                       capture_output=True, text=True, timeout=120, check=True)
    run(["selected_global.grib2", "-small_grib", "76.5:78.25", "28:29.5", "ncr.grib2"])
    validate_grib((folder / "ncr.grib2").read_bytes(), len(SELECT))
    run(["ncr.grib2", "-csv", "ncr.csv"])
    validate_csv((folder / "ncr.csv").read_bytes(), spec)


def verify(snapshot, spec):
    snapshot = Path(snapshot)
    manifest_bytes = (snapshot / "manifest.json").read_bytes()
    expected_hash = (snapshot / "manifest.sha256").read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash) or sha(manifest_bytes) != expected_hash:
        raise ValueError("GFS manifest checksum verification failed")
    manifest = json.loads(manifest_bytes)
    if manifest.get("forecast") != spec or manifest.get("data_role") != "nwp_context" or manifest.get("is_observation_or_label") is not False:
        raise ValueError("Snapshot forecast identity or data role differs from request")
    if {item["path"] for item in manifest["files"]} != {"provider.idx", "ncr.grib2", "ncr.csv"} or len(manifest["files"]) != 3:
        raise ValueError("Unexpected GFS snapshot files")
    for item in manifest["files"]:
        path = snapshot / item["path"]
        payload = path.read_bytes()
        if len(payload) != item["bytes"] or sha(payload) != item["sha256"]:
            raise ValueError(f"Checksum/size failure: {path}")
    validate_grib((snapshot / "ncr.grib2").read_bytes(), len(SELECT))
    validate_csv((snapshot / "ncr.csv").read_bytes(), spec)
    select_ranges((snapshot / "provider.idx").read_bytes(), spec)
    if sum(path.stat().st_size for path in snapshot.iterdir() if path.is_file()) > OUTPUT_LIMIT:
        raise ValueError("Snapshot exceeds bounded output size")
    return manifest


def read_latest(output_root=ROOT / "data/ncr/gfs"):
    """Verify the newest initialization/lead snapshot; fail if that snapshot is corrupt."""
    output_root = Path(output_root)
    if not output_root.exists():
        return None
    candidates = []
    for path in output_root.iterdir():
        match = re.fullmatch(r"gfs_(\d{8})_(00|06|12|18)_f(\d{3})_ncr", path.name)
        if not path.is_dir() or not match:
            continue
        day, cycle, lead = match.groups()
        spec = forecast_spec(f"{day[:4]}-{day[4:6]}-{day[6:]}", int(cycle), int(lead))
        candidates.append((spec["model_reference_time_utc"], spec["forecast_lead_hours"], path, spec))
    if not candidates:
        return None
    _, _, path, spec = max(candidates, key=lambda item: item[:2])
    return verify(path, spec)


def collect(date, cycle, lead, output_root=ROOT / "data/ncr/gfs", verify_only=False):
    spec = forecast_spec(date, cycle, lead)
    output_root = Path(output_root).resolve()
    snapshot = output_root / spec["snapshot_id"]
    if verify_only or snapshot.exists():
        return verify(snapshot, spec)
    binary = decoder_path()
    index, _ = fetch(spec["source_url"] + ".idx", 150_000)
    fields = select_ranges(index, spec)
    chunks = []
    for field in fields:
        payload, headers = fetch(spec["source_url"], FIELD_LIMIT,
                                 (field["byte_start"], field["byte_end_inclusive"]))
        expected_size = field["byte_end_inclusive"] - field["byte_start"] + 1
        if len(payload) != expected_size:
            raise ValueError("Returned GRIB field does not match inventory byte range")
        validate_grib(payload, 1)
        chunks.append(payload)
        field.update({"sha256": sha(payload), "bytes": len(payload),
                      "archive_last_modified": headers.get("Last-Modified"),
                      "archive_etag": headers.get("ETag")})
    combined = b"".join(chunks)
    validate_grib(combined, len(SELECT))
    retrieved = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".gfs-stage-", dir=output_root) as temporary:
        stage = Path(temporary) / "snapshot"
        stage.mkdir()
        (stage / "selected_global.grib2").write_bytes(combined)
        (stage / "provider.idx").write_bytes(index)
        decode(binary, stage, spec)
        (stage / "selected_global.grib2").unlink()
        files = [{"path": name, "bytes": (stage / name).stat().st_size,
                  "sha256": sha((stage / name).read_bytes())}
                 for name in ("provider.idx", "ncr.grib2", "ncr.csv")]
        manifest = {"schema_version": 1, "provider": "NOAA/NCEP", "data_role": "nwp_context",
                    "is_observation_or_label": False, "forecast": spec,
                    "retrieved_at_utc": retrieved, "historical_available_at_utc": None,
                    "geography": {**BOUNDS, "grid_degrees": GRID_STEP,
                                  "scope": "Delhi metro pilot rectangle, not statutory NCR boundary"},
                    "fields": fields, "files": files, "csv_rows": EXPECTED_ROWS,
                    "csv_has_header": False, "csv_columns": CSV_COLUMNS,
                    "decoder": "wgrib2", "transformation": "crop numeric GRIB fields; no unit conversion or interpolation",
                    "documentation_url": "https://registry.opendata.aws/noaa-gfs-bdp-pds/",
                    "notes": ["Model output is environmental context, not observed rain or lightning.",
                              "Initialization and archive Last-Modified do not establish historical operational availability.",
                              "Only regional GRIB and CSV are retained; original global field checksums and ranges remain in this manifest."]}
        manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
        (stage / "manifest.json").write_bytes(manifest_bytes)
        (stage / "manifest.sha256").write_text(sha(manifest_bytes) + "\n", encoding="ascii")
        verify(stage, spec)
        try:
            stage.rename(snapshot)
        except OSError:
            if not snapshot.exists():
                raise
            return verify(snapshot, spec)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="Model initialization date, YYYY-MM-DD UTC")
    parser.add_argument("--cycle", required=True, type=int, choices=(0, 6, 12, 18))
    parser.add_argument("--lead", required=True, type=int, help="Forecast lead hours, 0–120")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data/ncr/gfs")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    manifest = collect(args.date, args.cycle, args.lead, args.output_root, args.verify_only)
    print(json.dumps({"snapshot": str(args.output_root / manifest["forecast"]["snapshot_id"]),
                      "csv_rows": manifest["csv_rows"], "data_role": manifest["data_role"],
                      "retrieved_at_utc": manifest["retrieved_at_utc"], "forecast": manifest["forecast"]}, indent=2))


if __name__ == "__main__":
    main()

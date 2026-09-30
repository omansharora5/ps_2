"""Verify government starter-pack checksums, declared data counts and file boundaries."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

from collect_gfs_data import validate_grib

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/government"


def verify(scientific=False):
    inventory = json.loads((DATA / "inventory.json").read_text(encoding="utf-8"))
    verified = []
    for item in inventory["files"] + inventory["derived_files"]:
        path = (ROOT / item["path"]).resolve()
        if not path.is_relative_to(DATA.resolve()):
            raise ValueError("Path outside government collection")
        payload = path.read_bytes()
        if len(payload) != item["bytes"] or hashlib.sha256(payload).hexdigest() != item["sha256"]:
            raise ValueError(f"Mismatch: {path}")
        verified.append(item["path"])
    for collection in inventory["collections"]:
        payload = (ROOT / collection["manifest_path"]).read_bytes()
        if hashlib.sha256(payload).hexdigest() != collection["manifest_sha256"]:
            raise ValueError("Provider manifest changed after inventory preparation")
    imd = json.loads((DATA / "india/imd_synop_bihar_region_20260929.geojson").read_text())
    features = imd["features"]
    numeric = [f for f in features if isinstance(f["properties"]["value"], (int, float)) and math.isfinite(f["properties"]["value"])]
    reports = {f["properties"]["reportId"] for f in features}
    stations = {f["properties"]["wigos_station_identifier"] for f in features}
    if (len(features), len(numeric), len(reports), len(stations)) != (607, 353, 32, 7):
        raise ValueError("IMD sample cardinality differs from inspection")
    with (DATA / "derived/imd_synop_bihar_region_20260929.csv").open(encoding="utf-8", newline="") as stream:
        imd_csv = list(csv.DictReader(stream))
    if len(imd_csv) != 607 or sum(x["numeric_value_missing"] == "True" for x in imd_csv) != 254:
        raise ValueError("IMD CSV lost features/missingness")
    nasa = json.loads((DATA / "india/nasa_power_patna_20240601_20240607.json").read_text())
    parameters = nasa["properties"]["parameter"]
    if nasa["header"]["time_standard"] != "UTC" or len(parameters) != 6 or any(len(x) != 168 for x in parameters.values()):
        raise ValueError("NASA hourly coverage mismatch")
    if any(v == nasa["header"]["fill_value"] for values in parameters.values() for v in values.values()):
        raise ValueError("Unexpected NASA missing sentinel")
    grib = (DATA / "gfs/gfs_20250512_06_f003_selected.grib2").read_bytes()
    validate_grib(grib)
    rejected = 0
    for invalid in [grib[:-1], b"<html>Not a weather file</html>", grib + b"garbage"]:
        try:
            validate_grib(invalid)
        except ValueError:
            rejected += 1
    if rejected != 3:
        raise ValueError("GRIB structural rejection checks failed")
    commands = [[sys.executable, "scripts/collect_gfs_data.py", "--verify-only"]]
    if scientific:
        commands.extend([[sys.executable, f"scripts/collect_{name}_data.py", "--verify-only"] for name in ["india", "noaa"]])
    outputs = []
    for cmd in commands:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
        outputs.append({"command": " ".join(cmd[1:]), "exit_code": result.returncode, "stdout": result.stdout.strip()})
    report = {"status": "passed", "verified_data_files": len(verified), "raw_files": inventory["raw_file_count"],
              "raw_bytes": inventory["raw_bytes"], "derived_files": inventory["derived_file_count"],
              "imd": {"features": 607, "numeric_values": 353, "null_or_coded": 254, "reports": 32, "stations": 7},
              "nasa": {"hours": 168, "variables": 6, "values": 1008}, "gfs": {"fields": 7, "regional_csv_rows": 4263},
              "grib_invalid_inputs_rejected": rejected, "deep_scientific_parsers": scientific, "commands": outputs,
              "limitations": ["Not a training or calibration corpus", "New files are not integrated into the simulator-trained model", "Historic operational availability remains unknown"]}
    destination = ROOT / "artifacts/government_data_validation.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["status", "verified_data_files", "raw_bytes", "deep_scientific_parsers"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scientific", action="store_true", help="Also parse all local NOAA/IMD samples; use the isolated .venv-data environment")
    verify(parser.parse_args().scientific)

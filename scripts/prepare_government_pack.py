"""Create convenient CSV views and a consolidated inventory from verified raw files."""
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/government"
DERIVED = DATA / "derived"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == payload:
        return
    temp = path.with_name(path.name + ".part")
    temp.write_bytes(payload)
    temp.replace(path)


def csv_view(name, columns, rows, source, transformation, units):
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    path = DERIVED / name
    save(path, output.getvalue().encode("utf-8"))
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
            "sha256": digest(path), "rows": len(rows), "columns": columns,
            "derived_from": source.relative_to(ROOT).as_posix(), "source_sha256": digest(source),
            "transformation": transformation, "units": units,
            "historical_available_at_utc": None, "training_ready": False}


def main():
    files, existing_derived, collections = [], [], []
    for name in ["india", "noaa", "gfs"]:
        path = DATA / name / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for item in manifest["files"] + manifest.get("derived_files", []):
            local = (ROOT / item["path"]).resolve()
            if not local.is_relative_to(DATA.resolve()):
                raise ValueError("Manifest path outside collection")
            if local.stat().st_size != item["bytes"] or digest(local) != item["sha256"]:
                raise ValueError(f"Changed collection file: {local}")
        files.extend(manifest["files"])
        existing_derived.extend(manifest.get("derived_files", []))
        collections.append({"name": name, "manifest_path": path.relative_to(ROOT).as_posix(),
                            "manifest_sha256": digest(path), "raw_files": len(manifest["files"]),
                            "raw_bytes": sum(x["bytes"] for x in manifest["files"])})

    imd_path = DATA / "india/imd_synop_bihar_region_20260929.geojson"
    imd = json.loads(imd_path.read_text())
    fields = ["wigos_station_identifier", "reportId", "reportTime", "phenomenonTime", "name", "units", "value", "description"]
    rows = []
    for feature in sorted(imd["features"], key=lambda x: x["id"]):
        p = feature["properties"]
        rows.append([feature["id"], *feature["geometry"]["coordinates"], *[p.get(k) for k in fields], p.get("value") is None])
    imd_view = csv_view("imd_synop_bihar_region_20260929.csv", ["feature_id", "longitude", "latitude", *fields, "numeric_value_missing"],
                        rows, imd_path, "One row per original feature, sorted by feature ID; null remains blank plus explicit missing flag; no unit conversion or deduplication.",
                        "Per-row units column, exactly from IMD")

    nasa_path = DATA / "india/nasa_power_patna_20240601_20240607.json"
    nasa = json.loads(nasa_path.read_text())
    if nasa["header"]["time_standard"] != "UTC":
        raise ValueError("NASA sample must use UTC")
    parameters = nasa["properties"]["parameter"]
    names = list(parameters)
    stamps = sorted(parameters[names[0]])
    if any(sorted(parameters[n]) != stamps for n in names):
        raise ValueError("NASA variables do not have identical time coverage")
    rows = [[datetime.strptime(stamp, "%Y%m%d%H").replace(tzinfo=timezone.utc).isoformat(),
             *[parameters[n][stamp] for n in names]] for stamp in stamps]
    nasa_view = csv_view("nasa_power_patna_20240601_20240607.csv", ["time_utc", *names], rows, nasa_path,
                         "One row per hourly timestamp; time key rendered ISO8601 UTC; all values and units retained unchanged.",
                         {n: nasa["parameters"][n]["units"] for n in names})
    derived = existing_derived + [imd_view, nasa_view]
    inventory = {"schema_version": 1, "title": "VAJRA government data starter pack",
                 "collection_date": "2026-09-30", "training_ready": False,
                 "scope": "Historical parser and environmental-context samples; different regions/dates, not a matched training corpus",
                 "raw_file_count": len(files), "raw_bytes": sum(f["bytes"] for f in files),
                 "raw_file_note": "8 weather-data payloads plus 10 source inventories, catalogs or documentation files; excludes manifests and derived outputs",
                 "derived_file_count": len(derived), "derived_bytes": sum(f["bytes"] for f in derived),
                 "collections": collections, "files": files, "derived_files": derived}
    save(DATA / "inventory.json", (json.dumps(inventory, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
    print(json.dumps({k: inventory[k] for k in ["raw_file_count", "raw_bytes", "derived_file_count", "derived_bytes"]}))


if __name__ == "__main__":
    main()

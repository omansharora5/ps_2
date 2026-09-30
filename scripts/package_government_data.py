"""Package collected data, design and source notes without environments or binaries."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
paths = {p for p in (ROOT / "data/government").rglob("*") if p.is_file() and p.suffix != ".part"}
for pattern in ["research/*.md", "research/design/*.md"]:
    paths.update(ROOT.glob(pattern))
for name in ["DETAILED_TECHNICAL_ARCHITECTURE.md", "SIH26072_PROPOSAL_AND_EVIDENCE.md",
             "PRODUCT_FLOW_AND_ALGORITHMS.md", "SIH26072_RESEARCH_AND_BLUEPRINT.md", "VALIDATION.md",
             "artifacts/government_data_validation.json", "artifacts/architecture_document_check.json",
             "tools/wgrib2/provenance.json"]:
    paths.add(ROOT / name)
for name in ["collect_india_data.py", "collect_noaa_data.py", "collect_gfs_data.py",
             "prepare_government_pack.py", "verify_government_data.py", "package_government_data.py"]:
    paths.add(ROOT / "scripts" / name)

destination = ROOT / "artifacts/VAJRA_GOVERNMENT_DATA_STARTER_PACK.zip"
temporary = destination.with_suffix(".zip.part")
with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
    for path in sorted(paths):
        if not path.exists():
            raise FileNotFoundError(path)
        bundle.write(path, path.relative_to(ROOT).as_posix())
with zipfile.ZipFile(temporary) as bundle:
    bad = bundle.testzip()
    if bad:
        raise ValueError(f"ZIP integrity failure: {bad}")
    for path in paths:
        if bundle.read(path.relative_to(ROOT).as_posix()) != path.read_bytes():
            raise ValueError(f"Packaged content mismatch: {path}")
temporary.replace(destination)
record = {"path": destination.relative_to(ROOT).as_posix(), "files": len(paths),
          "bytes": destination.stat().st_size, "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
          "zip_crc_check": "passed", "all_member_content_comparisons": "passed",
          "entrypoint": "data/government/README.md"}
(ROOT / "artifacts/government_pack_archive.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record))

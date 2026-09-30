"""Download only the pinned official MétéoNet sample, validating content hashes."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


root = Path(__file__).resolve().parents[1]
folder = root / "data" / "external"
manifest = json.loads((folder / "meteonet_manifest.json").read_text(encoding="utf-8-sig"))
for item in manifest["files"]:
    path = folder / item["file"]
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]:
        print(f"Verified {path.name}")
        continue
    with urlopen(Request(item["source_url"], headers={"User-Agent": "VAJRA-research/0.1"}), timeout=60) as response:
        payload = response.read(10_000_001)
    if len(payload) > 10_000_000 or hashlib.sha256(payload).hexdigest() != item["sha256"]:
        raise ValueError(f"Download content differs from pinned manifest: {item['file']}")
    path.write_bytes(payload)
    print(f"Downloaded and verified {path.name}")

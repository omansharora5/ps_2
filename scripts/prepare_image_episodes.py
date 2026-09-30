"""Package already aligned, labelled source arrays into validated episode NPZ files.

Provider-specific decoding, spatial alignment and observed outcome construction
must precede this step. No timezone, coverage or lightning labels are invented.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

from train_images import load_episode, corpus

ARRAYS = ("values", "masks", "times_utc", "available_at_utc", "targets", "coverage", "target_end_utc")


def prepare(source, output, history):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or output.is_relative_to(source):
        raise ValueError("Output must be separate from the source episode tree")
    folders = sorted(path for path in source.iterdir() if path.is_dir())
    if not folders:
        raise ValueError("No matched episode folders. Government starter files are not aligned, labelled episodes.")
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for folder in folders:
        required = [folder / (key + ".npy") for key in ARRAYS] + [folder / "metadata.json"]
        if any(not path.is_file() for path in required):
            raise ValueError(f"{folder.name}: requires {', '.join(path.name for path in required)}")
        data = {key: np.load(folder / (key + ".npy"), allow_pickle=False) for key in ARRAYS}
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        destination = output / (folder.name + ".npz")
        if destination.exists():
            raise ValueError(f"Refusing to overwrite {destination}; choose a new preparation directory")
        temporary = destination.with_suffix(".npz.part")
        try:
            with temporary.open("wb") as handle:
                np.savez_compressed(handle, **data, metadata_json=np.array(json.dumps(metadata, sort_keys=True)))
            episode = load_episode(temporary, history)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        records.append({"path": destination.name, "event_id": metadata["event_id"], "sha256": episode["sha256"],
                        "source_files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in required}})
    _, splits = corpus(output, history)
    manifest = {"files": records, "splits": splits, "training_ready": False,
                "validation": "Episode schema and splits validated; scientific adequacy requires independent review"}
    (output / "preparation.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"episodes": len(records), "splits": splits, "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--history", type=int, default=3)
    args = parser.parse_args()
    try:
        prepare(args.source, args.output, args.history)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, f"Episode preparation failed: {error}\n")

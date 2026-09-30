"""Validate a local benchmark and export metadata/recipes without copying raw data."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nowcast.public_verification import prepare_benchmark


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Local artifact-manifest JSON configuration")
    parser.add_argument("--base-dir", type=Path, required=True, help="Root containing every listed artifact")
    parser.add_argument("--output", type=Path, required=True, help="New immutable JSON envelope")
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        manifest = prepare_benchmark(config, args.base_dir, args.output)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"Benchmark was not prepared: {error}\n")
    print(json.dumps({"benchmark_id": manifest["benchmark_id"], "export_mode": manifest["export_mode"],
                      "release_ready": manifest["release_ready"], "release_blockers": manifest["release_blockers"],
                      "artifact_count": manifest["artifact_count"]}, indent=2))


if __name__ == "__main__":
    main()

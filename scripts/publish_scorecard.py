"""Publish one immutable, checksum-verified monthly scorecard from frozen cases."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nowcast.public_verification import publish_scorecard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Local frozen-case JSON configuration")
    parser.add_argument("--root", type=Path, default=ROOT / "data/community/publications")
    parser.add_argument("--revision", type=int, default=1)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        card = publish_scorecard(args.root, config, args.revision)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"Scorecard was not published: {error}\n")
    print(json.dumps({"month": card["month"], "revision": card["revision"], "status": card["status"],
                      "admitted_cases": card["admitted_case_count"], "excluded": card["excluded"]}, indent=2))


if __name__ == "__main__":
    main()

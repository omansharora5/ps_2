"""Collect a bounded IMD Delhi metro snapshot; no API key needed for this endpoint."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nowcast.ncr_data import DEFAULT_ROOT, collect, latest, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--latest", action="store_true", help="Refresh the latest three UTC calendar days")
    parser.add_argument("--refresh", action="store_true", help="Query again; retain earlier snapshot")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    try:
        if args.verify_only:
            result = latest(args.output)
            if result is None:
                raise ValueError("No NCR collection exists")
            verify(args.output, result)
        else:
            if args.latest:
                if args.start or args.end:
                    raise ValueError("Use --latest or --start/--end, not both")
                today = datetime.now(timezone.utc).date()
                args.start, args.end = str(today - timedelta(days=2)), str(today)
            if not args.start or not args.end:
                raise ValueError("Supply --latest or both --start and --end")
            result = collect(args.output, args.start, args.end, refresh=args.refresh or args.latest)
        print(json.dumps({key: result[key] for key in ("id", "status", "counts", "latest_observed_at_utc", "training_ready_30_minutes", "failures")}, indent=2))
        return 0 if args.verify_only or result["status"] == "complete" else 2
    except (ValueError, OSError) as error:
        print(f"NCR collection failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

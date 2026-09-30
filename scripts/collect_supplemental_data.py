"""Collect small public NCR source snapshots, never forecasts disguised as observations."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nowcast import supplemental_data as data


def main():
    today = datetime.now(timezone.utc).date()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["all", *data.CATALOG], default="all")
    parser.add_argument("--start", default=(today - timedelta(days=7)).isoformat())
    parser.add_argument("--end", default=today.isoformat(), help="Exclusive UTC end date; POWER may contain missing recent hours")
    parser.add_argument("--output-root", type=Path, default=data.DEFAULT_ROOT)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    data.interval(args.start, args.end)
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass
    failures = 0
    for source in data.CATALOG if args.source == "all" else [args.source]:
        try:
            if args.verify_only:
                result = data.latest(args.output_root, source)
                if result is None:
                    raise ValueError("No collected snapshot")
                for name in ("raw.bin", "rows.json"):
                    data.checked(args.output_root, result, name)
            else:
                result = data.collect(source, args.output_root, args.start, args.end)
            print(json.dumps({"source": source, "status": result["status"], "rows": result["row_count"],
                              "id": result["id"], "retrieved_at_utc": result["retrieved_at_utc"]}))
        except Exception as error:
            failures += 1
            # Keep raw network errors and possible credential-bearing provider bodies out of logs.
            print(json.dumps({"source": source, "status": "failed", "error_type": type(error).__name__,
                              "reason": str(error) if isinstance(error, ValueError) else "Collection failed; previous snapshots retained"}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Live HTTP check against an explicitly isolated local demonstration store."""
import argparse
from datetime import timedelta
import json
from pathlib import Path
import sys
from unittest.mock import patch
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nowcast import community_store as data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8140)
    args = parser.parse_args()
    base = f"http://127.0.0.1:{args.port}"
    demo_root = ROOT / "data/community/demo-verification"
    store = data.CommunityStore(demo_root / "reports.sqlite")

    def request(path, body=None):
        payload = json.dumps(body).encode() if body is not None else None
        with urlopen(Request(base + path, data=payload, headers={"Content-Type": "application/json"}), timeout=20) as response:
            return json.load(response)

    moment = data.now()
    observed = moment - timedelta(minutes=45)
    old_start, _ = data.window(observed)
    bodies = [{"request_id": str(uuid4()), "installation_id": str(uuid4()), "cell_id": "palam", "answer": "yes",
               "observed_at_utc": data.utc(observed), "consent_training": True} for _ in range(5)]
    # Fabricated software fixtures only; never merge this store with operational evidence.
    with patch.object(data, "now", return_value=observed):
        for body in bodies:
            store.submit(body)
    candidate = store.aggregate("palam", old_start)
    queue = request("/api/community/review-queue")
    assert any(item["revision"] == candidate["revision"] for item in queue["windows"]), "API is not using the isolated demo store"
    assert candidate["window_closed"]
    review = {"cell_id": "palam", "window_start_utc": old_start, "expected_revision": candidate["revision"],
              "decision": "approve", "reason": "SYNTHETIC SOFTWARE TEST: no actual weather observation or scientific corroboration.",
              "evidence_url": "https://example.org/synthetic-software-fixture"}
    first_review = request("/api/community/review", review)
    assert request("/api/community/review", review) == first_review
    exported = request("/api/community/export")
    item = next(row for row in exported["items"] if row["revision"] == candidate["revision"])
    assert not item["ground_truth"] and not item["eligible_for_lightning"] and not exported["automatic_retraining"]
    assert "installation" not in json.dumps(exported)
    fresh = {**bodies[0], "request_id": str(uuid4()), "installation_id": str(uuid4()), "cell_id": "noida",
             "observed_at_utc": data.utc(moment), "answer": "unsure", "consent_training": False}
    receipt = request("/api/community/reports", fresh)
    assert request("/api/community/reports", fresh)["duplicate"]
    assert receipt["aggregate"]["counts_withheld"] and "yes" not in receipt["aggregate"]
    state = request("/api/community/state?cell_id=noida")
    assert state["evidence_card"]["lightning_probability"] is None
    assert state["scorecard"]["status"] == "unavailable" and not state["benchmark"]["raw_release_allowed"]
    for doc in ("REGIONAL_FEATURES.md", "REGIONAL_SCIENCE_GUIDE.md", "PUBLIC_VERIFICATION_GUIDE.md", "REGIONAL_FEATURE_EVIDENCE.md"):
        with urlopen(base + "/research/" + doc, timeout=20) as response:
            assert response.status == 200 and len(response.read()) > 100
    result = {"scope": "Synthetic software workflow in isolated demo-verification store; not observed weather",
              "tested_at_utc": data.utc(data.now()), "checks": ["live HTTP neutral report", "identical retry",
              "public counts withheld", "closed-window review", "idempotent review", "private weak-label export",
              "unavailable forecast/score claims", "four research document routes"], "passed": True}
    (ROOT / "artifacts/community-workflow-check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

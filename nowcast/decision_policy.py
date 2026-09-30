"""Explicit research decision rules. These rules do not authorize public dispatch."""

from dataclasses import dataclass
from datetime import datetime
import math


POLICY_VERSION = "research-evidence-gates-v1"
SPATIAL_SOURCES = ("radar", "satellite", "lightning")


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Decision timestamps need an explicit timezone")
    return parsed


@dataclass(frozen=True)
class ResearchPolicy:
    threshold: float = .5
    preparation_minutes: int = 20
    min_recent_spatial_sources: int = 2
    max_source_age_minutes: int = 10

    def __post_init__(self):
        if not math.isfinite(self.threshold) or not 0 < self.threshold < 1:
            raise ValueError("Probability threshold must be strictly between zero and one")
        for value, low, high in ((self.preparation_minutes, 0, 120), (self.min_recent_spatial_sources, 1, 3), (self.max_source_age_minutes, 0, 120)):
            if type(value) is not int or not low <= value <= high:
                raise ValueError("Policy counts and minutes are outside their supported bounds")


def assess_research_decision(run, site, policy):
    if run["mode"] != "simulation":
        raise ValueError("This policy supports simulation review only")
    issued = timestamp(run["issued_at"])
    probability = site["probability"]
    if probability is not None and (not math.isfinite(probability) or not 0 <= probability <= 1):
        raise ValueError("Probability must be unavailable or finite within [0,1]")
    sources = {item["source"]: item for item in run["sources"]}
    checks = []
    for name in SPATIAL_SOURCES:
        source = sources.get(name, {})
        reason, age = "usable", None
        if source.get("state") != "available":
            reason = "missing_or_stale"
        else:
            try:
                valid, available = timestamp(source["valid_at"]), timestamp(source["available_at"])
                age = (issued - valid).total_seconds() / 60
                if age < 0 or available < valid or available > issued:
                    reason = "not_available_at_issue"
                elif age > policy.max_source_age_minutes:
                    reason = "over_age_limit"
            except (KeyError, TypeError, ValueError, AttributeError):
                reason = "invalid_timestamps"
        checks.append({"source": name, "usable": reason == "usable", "reason": reason, "age_minutes": age})
    usable = [item["source"] for item in checks if item["usable"]]
    support_met = len(usable) >= policy.min_recent_spatial_sources
    threshold_met = probability is not None and probability >= policy.threshold
    status = ("unavailable" if probability is None else "hold_for_evidence" if not support_met
              else "review" if threshold_met else "below_demo_threshold")
    window_start = run["horizon"] - 15 if run["request"]["hazard"] == "lightning" else run["horizon"]
    deadline = window_start - policy.preparation_minutes if status == "review" else None
    probability_reason = ("The model withheld a probability; no all-clear can be inferred." if probability is None else
                          f"The simulated probability is {probability:.1%}; the selected review threshold is {policy.threshold:.1%}.")
    support_reason = (f"{len(usable)} of 3 spatial source types meet the {policy.max_source_age_minutes}-minute age limit; "
                      f"the policy requires {policy.min_recent_spatial_sources}. This is an input-support check, not a confidence percentage.")
    reasons = [probability_reason, support_reason]
    if status == "hold_for_evidence":
        reasons.append("Review the evidence gap before using this result, even if its probability is high.")
    if status == "below_demo_threshold":
        reasons.append("Below the selected review threshold does not mean safe or all-clear.")
    if deadline is not None:
        reasons.append(f"The illustrative preparation deadline is {deadline} minutes relative to issue time, using the forecast window start, not an exact strike ETA.")
    if any(item.get("state") != "available" for item in run["sources"]):
        reasons.append("This is a source-outage experiment; no separate outage calibration has been established.")
    reasons.append("Synthetic research output only. Indian regional validation, authenticated approval and public dispatch are not connected.")
    return {"policy_version": POLICY_VERSION, "status": status, "threshold_met": threshold_met,
            "evidence_support_met": support_met, "source_checks": checks, "usable_spatial_sources": usable,
            "min_recent_spatial_sources": policy.min_recent_spatial_sources,
            "max_source_age_minutes": policy.max_source_age_minutes, "decision_deadline_minutes": deadline,
            "model_validation": "synthetic_only", "public_dispatch_eligible": False, "reasons": reasons}

# Candidate B: evidence ledger with independent scientific artifacts

## Usage (written first)
```python
# Phone/browser: record an observation without granting it scientific authority.
receipt = evidence.submit(report, client_submission_id="device-generated-uuid")
candidate = evidence.review(window, policy)  # agreement, conflicts and coverage; never automatic truth
# Research worker: consumes immutable, explicitly approved evidence releases.
release = evidence.release(candidate.id, review_decision)
operations.register_dataset(release.dataset_record)
# Research scientist: numerical methods do not write state or load application services.
calibrator = science.fit_phase_calibration(calibration_events, phase_labels)
card = science.evidence_card(prediction, sensor_evidence, tracked_echoes)
scorecard = science.monthly_scorecard(frozen_cases, month="2026-09", comparator=imd_cases)
benchmark = evidence.export_manifest(release.id, redistribution_policy)
```

## Problem
Existing operations own approved datasets, candidate training and promotion boundaries; extending their job database with public reports would mix trusted research metadata and arbitrary client claims. The existing NCR API correctly has no operational forecast, and scalar ConvLSTM targets cannot express first-event time. New functionality must work as methods and evidence workflows while observational coverage still gates NCR predictions.

## Shape
```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class TargetWindow:
    block_id: str; geometry_version: str; issued_at: str
    start: str; end: str; hazard: Literal["rain", "lightning"]

@dataclass(frozen=True)
class Report:
    block_id: str; observed_at: str; received_at: str
    answer: Literal["yes", "no", "unsure"]; hazard: str
    location_accuracy_m: float; consent: bool; challenge_id: str | None

@dataclass(frozen=True)
class CoveredSequence:
    event_id: str; target: TargetWindow
    features: "Array"; outcomes: "Array"; observed: "BoolArray"
    available_at: tuple[str, ...]; phase: str; season: str

@dataclass(frozen=True)
class ReviewDecision:
    reviewer_id: str; disposition: Literal["reject", "supporting_evidence", "admit_weak_label"]
    independent_evidence_ids: tuple[str, ...]; reason: str

class EvidenceLedger:
    def submit(self, report: Report, client_submission_id: str) -> "Receipt": raise NotImplementedError
    def review(self, window: TargetWindow, policy: "ReviewPolicy") -> "Candidate": raise NotImplementedError
    def release(self, candidate_id: str, decision: ReviewDecision) -> "ReviewedRelease": raise NotImplementedError
    def export_manifest(self, release_id: str, policy: "RedistributionPolicy") -> "Manifest": raise NotImplementedError

def lightning_loss(logits: "Array", targets: "Array", coverage: "BoolArray") -> float: raise NotImplementedError
def onset_loss(hazard_logits: "Array", first_event_bin: "Array", censored_at: "Array") -> float: raise NotImplementedError
def onset_distribution(hazard_logits: "Array", bins_minutes: tuple[int, ...]) -> "Distribution": raise NotImplementedError
def fit_phase_calibration(events: tuple[CoveredSequence, ...], phase_labels: "PhaseLabels") -> "Calibrator": raise NotImplementedError
def fit_seasonal_zr(paired: "RadarGaugePairs", season: str) -> "ZRModel": raise NotImplementedError
def evidence_card(prediction: "PredictionOrUnavailable", sensors: "SensorEvidence", tracks: "Tracks") -> "Card": raise NotImplementedError
def monthly_scorecard(cases: "FrozenCases", month: str, comparator: "FrozenCases | None") -> "Scorecard": raise NotImplementedError
```

`nowcast/evidence_ledger.py` owns one separate SQLite ledger: immutable reports indexed by block/hazard/observed time, idempotency identities, authenticated review events and content-addressed release manifests. Same key plus same payload returns the existing receipt; conflicting payload rejects. Atomic transactions commit each mutation; readers derive candidates from immutable events. Reports retain coarse block location, not a public list of person coordinates. Client identifiers reduce accidental repeats but do not establish independent people; challenge signing/rate bounds belong to the HTTP boundary, and deployment needs real authentication before trusted reviews. Per-source correlation and prompt sampling remain visible.

`nowcast/regional_science.py` owns pure numeric methods and their validated domain inputs. Lightning learns covered strike-event targets, never rain proxies. Discrete hazards model first event in six five-minute bins; survival products yield a no-event mass and a conditional onset interval. Right censoring contributes only through observed bins; missing detection coverage is not a negative. A new `nowcast/image_models.py` extracts the current inline `scripts/train_images.py` model factory and adds task-selected lightning and hazard heads, with checkpoint schemas declaring head shape, label definition and time bins. Torch remains outside the HTTP import path. Existing training scripts reuse event partitions and calibration separation.

Phase calibration fits only adequately supported known-phase calibration groups, otherwise uses a documented pooled fallback; onset/active/break classification needs an issue-time phase source, not month guessing or retrospective future rain. Seasonal Z-R fits positive, collocated, equal-duration gauge/radar pairs in log space with held-out event comparisons and applicability metadata; clutter, attenuation, sampling and zero rainfall require separate masks. Warm rain is not vetoed by warm infrared tops; dust flags require surface visibility/wind evidence and remain qualified diagnostics.

`nowcast/evidence_api.py` parses bounded requests into ledger types and presents public aggregate cards/scorecards. Operator review reuses existing local research authorization. Thin web/native clients share the same API. Cards reveal actual frame timestamps, coverage and trajectory provenance; unavailable NCR forecasts show reasons, without invented paths or onset times. A rain-onset interval does not imply heavy-rain end time: duration requires its own trained intensity/cessation target.

Scorecards join exact hazard, geometry version, issue/valid window, threshold and covered truth; scores compare identical eligible cases or explicitly decline comparison. Existing probability metrics supply POD/FAR/CSI/reliability and event uncertainty. A versioned month artifact records excluded cases, publication cutoff and verification availability, so delayed labels cannot silently revise an already published score. Benchmark export verifies licensing, source hashes, redaction, availability times, independent event splits and coverage before releasing redistributable bytes; otherwise exports provenance plus download instructions only.

## Synthesis decision
Pending parent comparison. Candidate B concentrates trust and durable evidence in one ledger; numerical research stays independently executable and hands artifacts to existing operations.

## Tradeoffs accepted
- We accept a separate small ledger in exchange for keeping public input outside trusted job state.
- We accept reviewed weak labels and slower candidate admission in exchange for preventing majority votes and prompt selection bias from becoming truth.
- We accept unavailable operational outputs while implementing trainable heads and reproducible evaluation in exchange for honest data gates.

## Alternatives considered
One expanded operations store hides fewer concepts from callers: every report would need job/dataset state semantics and public write authorization would touch research invariants. A general event bus with report, review, training and publishing services adds distributed coordination without present scale evidence; a transactional ledger plus pure functions hides the same policy behind fewer entry points.

## Open questions and risks
Can licensed 2019 strike data provide event times, geometry and detection coverage aligned with radar/satellite archives? Which issue-time phase definition and independent gauge source can establish NCR calibration? These are dataset admission questions, not reasons to postpone code methods.

## Next implementation step
Implement the report ledger's idempotent submission/review/release path and coverage-aware onset mathematics, then wire task heads and shared client evidence views with explicit availability states.

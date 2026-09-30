# Candidate A: extend the research ledger and bounded recipes
## Usage (caller's view)
```python
# Website and mobile adapters submit the same bounded domain command.
receipt = ledger.record_report(report, challenge=challenge, actor=actor, request_id=request_id)
# Local operator review produces a candidate, never a verified observation by vote count.
candidate = ledger.review_reports(window_id, decision, expected_revision=revision)
job = submit_recipe(ledger, "fit_regional_heads", dataset_id=registered_dataset.id)
# A single immutable artifact contains scores, evidence and an export eligibility decision.
report = evaluate_month(forecasts, outcomes, month, comparator=archived_imd)
```
These are research operations. NCR user cards remain unavailable until an admitted model and observed input history exist. A user can always report current rain, no rain or uncertainty; the prompt must not tell them the model's answer first.

## Problem
The current ConvLSTM learns one scalar event map; the operations ledger already owns immutable dataset identities, disjoint event roles and bounded jobs. Extend these authorities instead of introducing another training scheduler or a second model registry. The missing pieces are explicit task/time labels, qualified public evidence and transparent evaluation artifacts, not a new generic agent framework.

## Shape
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Phase = Literal["onset", "active", "break", "unknown"]
Task = Literal["rain_event", "lightning_event", "rain_onset", "lightning_onset"]
@dataclass(frozen=True)
class TargetContract:
    task: Task
    lead_minutes: tuple[int, ...]  # Ordered edges, e.g. (5, 10, 15, 20, 25, 30).
    spatial_support: str          # Registered grid/block geometry identity, not a GPS claim.
    label_source: str
    coverage_definition: str
@dataclass(frozen=True)
class RegionalEpisode:
    event_id: str
    contract: TargetContract
    inputs: "CausalImageHistory"  # Existing values/masks/available-at convention.
    targets: "CoveredEventOrCensoredTime"
    phase: Phase
    phase_available_at: datetime  # Reject retrospective phase leakage.
@dataclass(frozen=True)
class CitizenReport:
    block_id: str
    observed_at: datetime
    answer: Literal["rain", "no_rain", "unsure"]
    location_accuracy_m: float
    consent_training: bool
@dataclass(frozen=True)
class ReviewDecision:
    disposition: Literal["exclude", "weak_candidate"]
    reason: str
    corroborating_evidence_ids: tuple[str, ...]

# operation_store.py: own transactions, uniqueness and report/review state.
def record_report(report: CitizenReport, *, challenge, actor, request_id: str):
    raise NotImplementedError
def review_reports(window_id: str, decision: ReviewDecision, *, expected_revision: int):
    raise NotImplementedError
# regional_science.py: pure NumPy methods; optional Torch heads loaded only by workers.
def fit_heads(train: tuple[RegionalEpisode, ...], validation, *, initialization):
    raise NotImplementedError
def fit_phase_calibration(calibration_events, *, min_events: int, min_each_class: int):
    raise NotImplementedError
def fit_seasonal_zr(training_pairs, *, min_events: int):
    raise NotImplementedError
def evaluate_month(forecasts, outcomes, month: str, *, comparator=None):
    raise NotImplementedError
def evidence_card(forecast, observations, *, now: datetime):
    raise NotImplementedError
def benchmark_manifest(dataset, *, license_records, public_metadata):
    raise NotImplementedError
```
`operation_recipes.py` adds bounded numerical recipes and dataset admission for the new explicit schema; v1 episodes keep their original contract. Reuse attempt directories, source hashing and artifact serving. Numerical code returns fitted artifacts and predictions; it never dispatches alerts or promotes checkpoints.

The shared encoder receives radar/satellite/environment channels with age and coverage masks. Distinct lightning logits learn only from detection labels with network coverage; missing detections without coverage are unknown. Discrete hazard logits use a masked survival likelihood: event at bin k contributes previous survival plus kth hazard; right-censored examples contribute only observed survival. Cumulative event probability and interval forecasts follow from hazards; a binary rain head cannot invent start or stop minutes.

Phase calibration reuses temperature fitting per sufficiently populated calibration stratum, otherwise a declared pooled fallback. Unknown phase remains explicit. Learn log Z = log a + b log R from paired, positive, quality-controlled training gauges/radar per season; retain units, sampling support, event IDs and coefficient bounds. Compare held-out rain errors to the configured baseline. Warm-top rain and dust are evaluation strata and quality flags until labelled models exist, never universal cloud-temperature rules.

Citizen records live in new ledger tables indexed by block/time and unique actor/challenge; immutable request identity rejects conflicting retries. Server-issued pseudonymous actors and expiring challenges reduce repeats but cannot establish independent humans. Public access gets only a narrow bounded report endpoint, separate from local-only research mutation authorization. Store coarse blocks, not exact location traces. A review transaction versions the candidate and provenance; only approved weak candidates enter a subsequent dataset snapshot with consent. Never convert a majority into gauge truth or contaminate locked test events. Sample wet and predicted-dry blocks to expose misses and response bias.

Evidence cards derive sensor ages, coverage, track geometry and onset intervals from actual registered records; missing paths stay missing. Monthly evaluation joins immutable forecasts and outcomes on issue/window, hazard definition and geographic support before computing POD/FAR/CSI, Brier/reliability and event bootstrap. IMD comparison requires an archived forecast issued by the same deadline on the same cohort; otherwise show unavailable. A categorical IMD warning is not a probability suitable for Brier scoring.

Benchmark export emits a reproducible manifest first. Raw export requires per-file redistribution rights, checksums, actual label coverage, event-separated split rosters, causal availability and privacy review. Export refusal lists unmet gates; no claim of a completed Indian corpus or national first. The operational API imports only the store and lightweight artifact readers, never PyTorch. Clients consume one evidence/reporting contract through existing service clients.

## Synthesis decision
Pending parent synthesis. This candidate makes the existing ledger the authority; numerical methods own scientific invariants and clients render declared availability.
## Tradeoffs accepted
- Accept explicit research unavailability in exchange for avoiding invented block-level lead times and unverified safety claims.
- Accept one additional schema version and ledger migration in exchange for stable original training/checkpoint semantics.
- Accept pooled calibration for sparse phases in exchange for avoiding misleading phase-specific fitted probabilities.
- Accept reviewed weak labels and anonymous duplicate risk in exchange for a usable pilot without collecting personal identity.

## Alternatives considered
A new regional orchestration service could hide model fitting but would duplicate dataset admission, retries and artifacts and make callers reconcile registries. A single enlarged ConvLSTM output tensor hides fewer details: each caller would still need to know channel positions, censoring and label coverage. Explicit task contracts keep that knowledge in science admission.

## Open questions and risks
Can approved radar/lightning archives and phase annotations establish NCR coverage and lawful redistribution? Can a deployment supply authenticated staff review and abuse controls beyond the local pilot? Which minimum phase sample counts and event definitions survive held-out sensitivity analysis? These data questions leave methods runnable while deployment remains gated.

## Next implementation step
Implement typed regional targets and censored-hazard evaluation with deterministic fixtures, then add the idempotent report/review ledger and artifact-only client routes.

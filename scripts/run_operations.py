"""Run bounded local research work separately from the HTTP server."""

import argparse
from contextlib import AbstractContextManager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import threading
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nowcast.operation_store import OperationsStore
from nowcast.operation_recipes import execute_recipe, freeze_dataset, prepare_demo_dataset, submit_recipe


def operation_root():
    return Path(os.environ.get("VAJRA_OPERATIONS_ROOT", ROOT / "data/operations")).resolve()


class WorkerLock(AbstractContextManager):
    """OS-owned lifetime lock. A slow live worker cannot lose it to a timer."""

    def __init__(self, root):
        self.path = Path(root) / "worker.lock"
        self.stream = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("a+b")
        try:
            if self.path.stat().st_size == 0:
                self.stream.write(b"0")
                self.stream.flush()
            self.stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.stream.close()
            self.stream = None
            raise RuntimeError("Another research worker owns this store") from error
        return self

    def __exit__(self, *_):
        if self.stream:
            self.stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
            self.stream.close()
            self.stream = None


def learning_tick(store, *, now=None, force=False):
    """Reconcile admitted observations, never manufacture new training truth."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Learning time requires a timezone")
    policy = store.learning()
    if not policy["enabled"]:
        return policy
    checked = policy.get("checked_at")
    if not force and checked and datetime.fromisoformat(checked.replace("Z", "+00:00")).astimezone(timezone.utc).date() == now.astimezone(timezone.utc).date():
        return policy
    datasets = store.datasets()
    eligible = [d for d in datasets if d.get("learning_eligible") and
                datetime.fromisoformat(d["labels_available_at"].replace("Z", "+00:00")) <= now]
    if not eligible:
        return store.record_learning("waiting_for_labels",
            "No admitted observed dataset has mature covered labels. Synthetic examples are excluded.",
            checked_at=now.isoformat())
    # Only the newest admitted version in each series is considered.
    latest = {}
    for dataset in sorted(eligible, key=lambda d: (d["created_at"], d["id"])):
        latest[dataset["series"]] = dataset
    jobs = store.jobs(limit=1000)
    held_candidates = []
    for dataset in sorted(latest.values(), key=lambda d: (d["created_at"], d["id"]), reverse=True):
        prior = [j for j in jobs if j["kind"] == "train_candidate" and j["status"] == "succeeded"
                 and j.get("dataset_id")]
        consumed = set()
        for job in prior:
            previous = store.dataset(job["dataset_id"])
            if previous["series"] == dataset["series"]:
                consumed.update(previous["event_ids"])
        if not set(dataset["event_ids"]) - consumed:
            continue
        job = submit_recipe(store, "train_candidate", dataset["id"])
        if job["status"] in ("failed", "cancelled"):
            held_candidates.append(job["id"])
            continue
        note = "One candidate per frozen dataset and recipe. Successful execution does not promote a model."
        if held_candidates:
            note += f" {len(held_candidates)} other series need review; their failed or cancelled candidates remain unchanged."
        return store.record_learning("candidate_queued" if job["status"] == "queued" else "candidate_running" if job["status"] == "running" else "candidate_recorded",
                                     note,
                                     job_id=job["id"], checked_at=now.isoformat())
    if held_candidates:
        return store.record_learning("needs_review",
            "Failed or cancelled candidates remain unchanged. Review their records before an explicit retry; no other series has new eligible events.",
            job_id=held_candidates[0], checked_at=now.isoformat())
    return store.record_learning("waiting_for_new_events", "No new independent observed events beyond the recorded successful candidates.",
                                 checked_at=now.isoformat())


def work_once(store):
    job = store.claim()
    if job is None:
        return None
    attempt = store.root / "attempts" / job["id"] / job["attempt_token"]
    try:
        attempt.mkdir(parents=True, exist_ok=False)
        result = execute_recipe(job, attempt, store)
        if not store.finish(job["id"], job["attempt_token"], result):
            print(json.dumps({"job_id": job["id"], "publication": "discarded_cancelled_or_superseded"}), flush=True)
    except Exception as error:
        # Detailed local traceback is useful to a developer; public records stay bounded.
        import traceback
        traceback.print_exc()
        message = str(error).replace(str(ROOT), "[project]").replace(str(store.root), "[operations]")
        store.fail(job["id"], job["attempt_token"], f"{type(error).__name__}: {message[:700]}")
    return store.get(job["id"])


def run_worker(store, *, once=False, poll_seconds=2):
    with WorkerLock(store.root):
        store.recover_interrupted()
        worker_id = uuid4().hex
        stop = threading.Event()
        def beat():
            while not stop.is_set():
                running = next((j["id"] for j in store.jobs() if j["status"] == "running"), None)
                store.heartbeat(worker_id, running)
                stop.wait(5)
        heartbeat = threading.Thread(target=beat, name="operations-heartbeat", daemon=True)
        heartbeat.start()
        try:
            while True:
                try:
                    learning_tick(store)
                except (ValueError, RuntimeError, KeyError, OSError) as error:
                    store.record_learning("needs_review",
                        "The learning check could not admit work. Existing queued jobs will continue. " + str(error)[:250])
                job = work_once(store)
                if job:
                    print(json.dumps({"id": job["id"], "status": job["status"], "attempt": job["attempt"]}), flush=True)
                if once:
                    return job
                time.sleep(poll_seconds)
        finally:
            stop.set()
            heartbeat.join(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=operation_root(), help="Trusted local store directory")
    commands = parser.add_subparsers(dest="command", required=True)
    worker = commands.add_parser("worker")
    worker.add_argument("--once", action="store_true")
    commands.add_parser("prepare-demo")
    registration = commands.add_parser("register-dataset")
    registration.add_argument("--source", type=Path, required=True)
    registration.add_argument("--name", required=True)
    registration.add_argument("--series", required=True)
    registration.add_argument("--labels-available-at", required=True)
    registration.add_argument("--coverage-evidence", required=True)
    submit = commands.add_parser("enqueue")
    submit.add_argument("--kind", choices=["starter_audit", "radar_replay", "train_candidate"], required=True)
    submit.add_argument("--dataset-id")
    commands.add_parser("status")
    commands.add_parser("learning-tick")
    args = parser.parse_args()
    store = OperationsStore(args.root)
    try:
        if args.command == "worker":
            run_worker(store, once=args.once)
            return
        if args.command == "prepare-demo":
            result = store.register_dataset(prepare_demo_dataset(store.root))
        elif args.command == "register-dataset":
            result = store.register_dataset(freeze_dataset(args.source, store.root, name=args.name, series=args.series,
                                                          labels_available_at=args.labels_available_at, coverage_evidence=args.coverage_evidence))
        elif args.command == "enqueue":
            result = submit_recipe(store, args.kind, args.dataset_id)
        elif args.command == "learning-tick":
            with WorkerLock(store.root):
                result = learning_tick(store, force=True)
        else:
            result = {"jobs": store.jobs(), "datasets": store.datasets(), "learning": store.learning(), "worker": store.worker()}
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, KeyError, RuntimeError, OSError) as error:
        parser.exit(2, f"Operations error: {error}\n")


if __name__ == "__main__":
    main()

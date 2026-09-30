"""Durable, bounded research jobs and immutable dataset identities.

The worker's OS lifetime lock owns execution exclusion and crash recovery.
Heartbeats here are informational: age alone never authorizes another worker.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
from uuid import uuid4


MAX_PENDING = 20
MAX_JOBS = 1000
MAX_DATASETS = 100
MAX_ATTEMPTS = 3
KINDS = frozenset(("starter_audit", "radar_replay", "train_candidate"))
ROLES = ("train", "validation", "calibration", "test")
TERMINAL = frozenset(("succeeded", "failed", "cancelled"))
HEX64 = re.compile(r"^[a-f0-9]{64}$")


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _text(value, field, limit=256):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise ValueError(f"{field} must be nonempty text of at most {limit} characters")
    return value


def _identifier(value, field="id"):
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 identity")
    return value


def _instant(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an explicit timezone timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be an explicit timezone timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be an explicit timezone timestamp")
    return value


def _json(value, field="value", max_bytes=4_000_000):
    def validate(item):
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise ValueError(f"{field} requires string object keys")
            for nested in item.values():
                validate(nested)
        elif isinstance(item, list):
            for nested in item:
                validate(nested)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise ValueError(f"{field} contains a non-JSON value")

    try:
        validate(value)
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError(f"{field} must contain finite JSON values") from error
    if len(encoded.encode("utf-8")) > max_bytes:
        raise ValueError(f"{field} exceeds its metadata budget")
    return encoded


def _dictionary(value, field, max_bytes=4_000_000):
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return _json(value, field, max_bytes)


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _dataset_record(record):
    # Round-trip once to detach mutable caller containers from stored identity.
    result = json.loads(_dictionary(record, "dataset"))
    for field in ("id", "name", "scope", "series", "event_ids", "splits", "files",
                  "learning_eligible", "labels_available_at", "coverage_evidence", "created_at"):
        if field not in result:
            raise ValueError(f"Dataset is missing {field}")
    _identifier(result["id"], "dataset id")
    for field in ("name", "scope", "series"):
        _text(result[field], field, 512)
    _instant(result["created_at"], "created_at")
    if type(result["learning_eligible"]) is not bool:
        raise ValueError("learning_eligible must be boolean")
    if result["labels_available_at"] is not None:
        _instant(result["labels_available_at"], "labels_available_at")
    events = result["event_ids"]
    if not isinstance(events, list) or not 1 <= len(events) <= 4096:
        raise ValueError("Dataset requires 1 to 4096 event identities")
    for event in events:
        _text(event, "event id", 256)
    if len(events) != len(set(events)):
        raise ValueError("Dataset event identities must be unique")
    splits = result["splits"]
    if not isinstance(splits, dict) or set(splits) != set(ROLES):
        raise ValueError("Dataset requires train, validation, calibration and test split rosters")
    assignments = {}
    for role in ROLES:
        if not isinstance(splits[role], list):
            raise ValueError("Dataset split rosters must be arrays")
        for event in splits[role]:
            _text(event, "split event id", 256)
            if event in assignments:
                raise ValueError("An event cannot appear twice or in multiple splits")
            assignments[event] = role
    if set(assignments) != set(events):
        raise ValueError("Split rosters must cover exactly the dataset event identities")
    files = result["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= 8192:
        raise ValueError("Dataset requires 1 to 8192 file identities")
    event_files = {event: [] for event in events}
    names = set()
    for file in files:
        if not isinstance(file, dict):
            raise ValueError("Dataset files must be objects")
        name = _text(file.get("name"), "file name", 256)
        if "/" in name or "\\" in name or name in (".", "..") or name in names:
            raise ValueError("Dataset file names must be unique basenames")
        names.add(name)
        sha = _identifier(file.get("sha256"), "file sha256")
        size = file.get("bytes")
        if type(size) is not int or size < 0:
            raise ValueError("File bytes must be a nonnegative integer")
        event = file.get("event_id")
        if not isinstance(event, str) or event not in event_files:
            raise ValueError("Every dataset file must identify a registered event")
        event_files[event].append({"sha256": sha, "bytes": size})
    if any(not entries for entries in event_files.values()):
        raise ValueError("Every dataset event requires at least one file identity")
    event_digests = {event: _digest(sorted(entries, key=lambda item: (item["sha256"], item["bytes"])))
                     for event, entries in event_files.items()}
    return result, assignments, event_digests


def _result_record(result):
    value = json.loads(_dictionary(result, "result"))
    if set(value) != {"summary", "artifacts"} or not isinstance(value["summary"], dict):
        raise ValueError("Result must contain summary object and artifacts array")
    artifacts = value["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) > 32:
        raise ValueError("A result may reference at most 32 artifacts")
    identifiers = set()
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"id", "name", "relative_path", "sha256", "bytes"}:
            raise ValueError("Artifact requires id, name, relative_path, sha256 and bytes")
        identifier = _text(item["id"], "artifact id", 128)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", identifier) or identifier in identifiers:
            raise ValueError("Artifact identities must be unique URL-safe identifiers")
        identifiers.add(identifier)
        name = _text(item["name"], "artifact name", 256)
        if "/" in name or "\\" in name or name in (".", ".."):
            raise ValueError("Artifact name must be a basename")
        _identifier(item["sha256"], "artifact sha256")
        if type(item["bytes"]) is not int or item["bytes"] < 0:
            raise ValueError("Artifact bytes must be a nonnegative integer")
        relative = _text(item["relative_path"], "artifact relative_path", 1024)
        path = PurePosixPath(relative)
        if not path.parts or path.is_absolute() or "\\" in relative or ":" in relative or ".." in path.parts or str(path) != relative:
            raise ValueError("Artifact path must be a normalized relative path")
    return value


class OperationsStore:
    """Metadata authority; callers own the worker lock and verify artifact bytes."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "operations.sqlite"
        with self._connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS datasets (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL, identity TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS event_roles (
                    series TEXT NOT NULL, event_id TEXT NOT NULL, role TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL, PRIMARY KEY (series, event_id)
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
                    stage TEXT NOT NULL, scope TEXT NOT NULL, dataset_id TEXT,
                    attempt INTEGER NOT NULL, attempt_token TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    started_at TEXT, finished_at TEXT, error TEXT,
                    summary TEXT, artifacts TEXT NOT NULL,
                    identity TEXT NOT NULL, parameters TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS jobs_queue ON jobs(status, created_at, id);
                CREATE INDEX IF NOT EXISTS jobs_recent ON jobs(updated_at DESC, id);
                CREATE TABLE IF NOT EXISTS attempts (
                    job_id TEXT NOT NULL REFERENCES jobs(id), ordinal INTEGER NOT NULL,
                    token TEXT NOT NULL UNIQUE, status TEXT NOT NULL, stage TEXT NOT NULL,
                    started_at TEXT NOT NULL, finished_at TEXT, error TEXT,
                    PRIMARY KEY(job_id, ordinal)
                );
                CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, payload TEXT NOT NULL);
            """)
        with self._connection(write=True) as db:
            initial = {"enabled": False, "status": "disabled", "note": "Automatic observed-data learning is disabled.",
                       "job_id": None, "checked_at": None, "updated_at": _now()}
            db.execute("INSERT OR IGNORE INTO settings VALUES ('learning', ?)", (_json(initial),))

    @contextmanager
    def _connection(self, write=False):
        db = sqlite3.connect(self.path, timeout=20, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            if write:
                db.commit()
        except BaseException:
            if write:
                db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _job(row):
        if row is None:
            raise KeyError("Unknown operation job")
        result = dict(row)
        for field in ("identity", "parameters", "summary", "artifacts"):
            if result[field] is not None:
                result[field] = json.loads(result[field])
        return result

    @staticmethod
    def _read_job(db, identifier):
        return OperationsStore._job(db.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone())

    @staticmethod
    def _capacity(db):
        if db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0] >= MAX_PENDING:
            raise RuntimeError("Research queue is full; wait for pending work to finish")

    def register_dataset(self, record: dict) -> dict:
        value, assignments, event_digests = _dataset_record(record)
        identity = _json({key: item for key, item in value.items() if key != "created_at"})
        with self._connection(write=True) as db:
            existing = db.execute("SELECT payload, identity FROM datasets WHERE id=?", (value["id"],)).fetchone()
            if existing:
                if existing["identity"] != identity:
                    raise ValueError("Dataset identity already exists with different immutable metadata")
                return json.loads(existing["payload"])
            if db.execute("SELECT COUNT(*) FROM datasets").fetchone()[0] >= MAX_DATASETS:
                raise RuntimeError("Frozen dataset registry is full; archive it before accepting new identities")
            for event, role in assignments.items():
                old = db.execute("SELECT role, content_sha256 FROM event_roles WHERE series=? AND event_id=?",
                                 (value["series"], event)).fetchone()
                if old and old["role"] != role:
                    raise ValueError(f"Event {event} cannot change its protected {old['role']} role to {role}")
                if old and old["content_sha256"] != event_digests[event]:
                    raise ValueError(f"Event {event} cannot change its frozen file identity within a learning series")
                db.execute("INSERT OR IGNORE INTO event_roles VALUES (?,?,?,?)",
                           (value["series"], event, role, event_digests[event]))
            db.execute("INSERT INTO datasets VALUES (?,?,?,?)", (value["id"], _json(value), identity, value["created_at"]))
        return value

    def datasets(self) -> list[dict]:
        with self._connection() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM datasets ORDER BY created_at DESC, id")]

    def dataset(self, identifier: str) -> dict:
        _identifier(identifier)
        with self._connection() as db:
            row = db.execute("SELECT payload FROM datasets WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise KeyError("Unknown frozen dataset")
        return json.loads(row[0])

    def enqueue(self, kind: str, identity: dict, parameters: dict, scope: str) -> dict:
        if not isinstance(kind, str) or kind not in KINDS:
            raise ValueError("Unknown fixed research operation")
        identity_json = _dictionary(identity, "identity", 128_000)
        parameters_json = _dictionary(parameters, "parameters", 128_000)
        _text(scope, "scope", 1024)
        dataset_id = parameters.get("dataset_id")
        if dataset_id is not None:
            _identifier(dataset_id, "dataset_id")
        if kind == "train_candidate" and dataset_id is None:
            raise ValueError("Training requires a registered frozen dataset")
        identifier = _digest({"kind": kind, "identity": identity, "parameters": parameters})
        with self._connection(write=True) as db:
            existing = db.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
            if existing:
                if existing["scope"] != scope:
                    raise ValueError("Identical operation cannot change its scientific scope")
                return self._job(existing)
            if dataset_id:
                dataset_row = db.execute("SELECT payload FROM datasets WHERE id=?", (dataset_id,)).fetchone()
                if dataset_row is None:
                    raise KeyError("Unknown frozen dataset")
                if kind == "train_candidate" and json.loads(dataset_row[0])["scope"] != scope:
                    raise ValueError("Training scope must match its frozen dataset")
            self._capacity(db)
            if db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] >= MAX_JOBS:
                raise RuntimeError("Research job history is full; archive it before accepting new identities")
            timestamp = _now()
            db.execute("""INSERT INTO jobs
                (id,kind,status,stage,scope,dataset_id,attempt,created_at,updated_at,artifacts,identity,parameters)
                VALUES (?,?,'queued','queued',?,?,0,?,?,'[]',?,?)""",
                       (identifier, kind, scope, dataset_id, timestamp, timestamp, identity_json, parameters_json))
            return self._read_job(db, identifier)

    def jobs(self, limit: int = 30) -> list[dict]:
        if type(limit) is not int or not 1 <= limit <= MAX_JOBS:
            raise ValueError(f"Job list limit must be between 1 and {MAX_JOBS}")
        with self._connection() as db:
            return [self._job(row) for row in db.execute("SELECT * FROM jobs ORDER BY updated_at DESC, id LIMIT ?", (limit,))]

    def get(self, identifier: str) -> dict:
        _identifier(identifier)
        with self._connection() as db:
            return self._read_job(db, identifier)

    def claim(self) -> dict | None:
        with self._connection(write=True) as db:
            if db.execute("SELECT 1 FROM jobs WHERE status='running' LIMIT 1").fetchone():
                return None
            row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at,id LIMIT 1").fetchone()
            if row is None:
                return None
            identifier, attempt, token, timestamp = row["id"], row["attempt"] + 1, uuid4().hex, _now()
            db.execute("""UPDATE jobs SET status='running',stage='starting',attempt=?,attempt_token=?,
                updated_at=?,started_at=?,finished_at=NULL,error=NULL WHERE id=?""",
                       (attempt, token, timestamp, timestamp, identifier))
            db.execute("INSERT INTO attempts (job_id,ordinal,token,status,stage,started_at) VALUES (?,?,?,'running','starting',?)",
                       (identifier, attempt, token, timestamp))
            return self._read_job(db, identifier)

    def recover_interrupted(self) -> int:
        """Call only after obtaining the exclusive OS worker lifetime lock."""
        timestamp = _now()
        error = "Worker stopped before completing this attempt; explicit retry is required."
        with self._connection(write=True) as db:
            db.execute("""UPDATE attempts SET status='failed',stage='interrupted',finished_at=?,error=?
                WHERE token IN (SELECT attempt_token FROM jobs WHERE status='running')""", (timestamp, error))
            count = db.execute("""UPDATE jobs SET status='failed',stage='interrupted',updated_at=?,finished_at=?,error=?
                WHERE status='running'""", (timestamp, timestamp, error)).rowcount
        return count

    def stage(self, identifier: str, attempt_token: str, stage: str) -> bool:
        _identifier(identifier)
        _text(attempt_token, "attempt token", 128)
        _text(stage, "stage", 128)
        with self._connection(write=True) as db:
            changed = db.execute("UPDATE jobs SET stage=?,updated_at=? WHERE id=? AND status='running' AND attempt_token=?",
                                 (stage, _now(), identifier, attempt_token)).rowcount
            if changed:
                db.execute("UPDATE attempts SET stage=? WHERE token=?", (stage, attempt_token))
        return bool(changed)

    def finish(self, identifier: str, attempt_token: str, result: dict) -> bool:
        _identifier(identifier)
        _text(attempt_token, "attempt token", 128)
        value = _result_record(result)
        timestamp = _now()
        with self._connection(write=True) as db:
            changed = db.execute("""UPDATE jobs SET status='succeeded',stage='complete',updated_at=?,finished_at=?,
                error=NULL,summary=?,artifacts=? WHERE id=? AND status='running' AND attempt_token=?""",
                (timestamp, timestamp, _json(value["summary"]), _json(value["artifacts"]), identifier, attempt_token)).rowcount
            if changed:
                db.execute("UPDATE attempts SET status='succeeded',stage='complete',finished_at=? WHERE token=?", (timestamp, attempt_token))
        return bool(changed)

    def fail(self, identifier: str, attempt_token: str, error: str) -> bool:
        _identifier(identifier)
        _text(attempt_token, "attempt token", 128)
        _text(error, "error", 6000)
        timestamp = _now()
        with self._connection(write=True) as db:
            changed = db.execute("""UPDATE jobs SET status='failed',stage='failed',updated_at=?,finished_at=?,error=?
                WHERE id=? AND status='running' AND attempt_token=?""", (timestamp, timestamp, error, identifier, attempt_token)).rowcount
            if changed:
                db.execute("UPDATE attempts SET status='failed',stage='failed',finished_at=?,error=? WHERE token=?",
                           (timestamp, error, attempt_token))
        return bool(changed)

    def cancel(self, identifier: str) -> dict:
        _identifier(identifier)
        with self._connection(write=True) as db:
            job = self._read_job(db, identifier)
            if job["status"] in TERMINAL:
                return job
            timestamp = _now()
            db.execute("UPDATE jobs SET status='cancelled',stage='cancelled',updated_at=?,finished_at=? WHERE id=?",
                       (timestamp, timestamp, identifier))
            if job["attempt_token"]:
                db.execute("UPDATE attempts SET status='cancelled',stage='cancelled',finished_at=? WHERE token=?",
                           (timestamp, job["attempt_token"]))
            return self._read_job(db, identifier)

    def retry(self, identifier: str, expected_attempt: int) -> dict:
        _identifier(identifier)
        if type(expected_attempt) is not int or not 0 <= expected_attempt <= MAX_ATTEMPTS:
            raise ValueError("expected_attempt must identify an existing bounded attempt")
        with self._connection(write=True) as db:
            job = self._read_job(db, identifier)
            if expected_attempt != job["attempt"]:
                raise ValueError("Retry refers to a stale attempt; refresh the job before retrying")
            if job["status"] == "queued":
                return job
            if job["status"] not in ("failed", "cancelled"):
                raise ValueError("Only failed or cancelled jobs can be retried")
            if job["attempt"] >= MAX_ATTEMPTS:
                raise ValueError("Research operation has exhausted its three execution attempts")
            self._capacity(db)
            db.execute("""UPDATE jobs SET status='queued',stage='queued',updated_at=?,started_at=NULL,finished_at=NULL,
                attempt_token=NULL,error=NULL,summary=NULL,artifacts='[]' WHERE id=?""", (_now(), identifier))
            return self._read_job(db, identifier)

    def heartbeat(self, worker_id: str, job_id: str | None = None) -> None:
        _text(worker_id, "worker_id", 128)
        if job_id is not None:
            _identifier(job_id, "job_id")
        record = {"worker_id": worker_id, "heartbeat_at": _now(), "job_id": job_id}
        with self._connection(write=True) as db:
            if job_id is not None:
                self._read_job(db, job_id)
            db.execute("INSERT INTO settings VALUES ('worker',?) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload", (_json(record),))

    def worker(self) -> dict:
        with self._connection() as db:
            row = db.execute("SELECT payload FROM settings WHERE name='worker'").fetchone()
        return json.loads(row[0]) if row else {"worker_id": None, "heartbeat_at": None, "job_id": None}

    def set_learning(self, enabled: bool) -> dict:
        if type(enabled) is not bool:
            raise ValueError("Learning enabled must be boolean")
        with self._connection(write=True) as db:
            record = json.loads(db.execute("SELECT payload FROM settings WHERE name='learning'").fetchone()[0])
            if record["enabled"] == enabled:
                return record
            record.update(enabled=enabled, status="waiting_for_worker" if enabled else "disabled",
                          note="Waiting for a worker to check eligible observed datasets." if enabled else "Automatic observed-data learning is disabled.",
                          job_id=None, updated_at=_now())
            if enabled:
                record["checked_at"] = None
            db.execute("UPDATE settings SET payload=? WHERE name='learning'", (_json(record),))
            return record

    def learning(self) -> dict:
        with self._connection() as db:
            return json.loads(db.execute("SELECT payload FROM settings WHERE name='learning'").fetchone()[0])

    def record_learning(self, status: str, note: str, job_id: str | None = None, checked_at: str | None = None) -> dict:
        _text(status, "learning status", 128)
        _text(note, "learning note", 6000)
        if job_id is not None:
            _identifier(job_id, "job_id")
        if checked_at is not None:
            _instant(checked_at, "checked_at")
        with self._connection(write=True) as db:
            record = json.loads(db.execute("SELECT payload FROM settings WHERE name='learning'").fetchone()[0])
            # A concurrent explicit disable wins over a completed scheduler check.
            if not record["enabled"]:
                return record
            if job_id is not None:
                self._read_job(db, job_id)
            timestamp = _now()
            record.update(status=status, note=note, job_id=job_id, checked_at=checked_at or timestamp, updated_at=timestamp)
            db.execute("UPDATE settings SET payload=? WHERE name='learning'", (_json(record),))
            return record

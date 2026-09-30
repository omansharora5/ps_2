"""Unverified citizen evidence, isolated from admitted training datasets and jobs."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit
from uuid import UUID

CELLS = [
    {"id": "delhi-central", "name": "Central Delhi pilot cell", "bbox": [77.1875, 28.5875, 77.2125, 28.6125]},
    {"id": "palam", "name": "Palam pilot cell", "bbox": [77.0875, 28.5625, 77.1125, 28.5875]},
    {"id": "noida", "name": "Noida pilot cell", "bbox": [77.3125, 28.5625, 77.3375, 28.5875]},
    {"id": "gurugram", "name": "Gurugram pilot cell", "bbox": [77.0125, 28.4375, 77.0375, 28.4625]},
]
CELL_IDS = {cell["id"] for cell in CELLS}
MIN_REPORTS = 5
MIN_AGREEMENT = .8
MAX_REPORTS = 100_000


def now():
    return datetime.now(timezone.utc)


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("An explicit UTC timestamp is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("An explicit UTC timestamp is required")
    return parsed


def utc(value):
    return value.isoformat().replace("+00:00", "Z")


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def window(value):
    start = value.replace(minute=value.minute // 15 * 15, second=0, microsecond=0)
    return utc(start), utc(start + timedelta(minutes=15))


class Conflict(ValueError):
    pass


class Capacity(ValueError):
    pass


class CommunityStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def connection(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, installation_hash TEXT NOT NULL,
                    cell_id TEXT NOT NULL, window_start TEXT NOT NULL, observed_at TEXT NOT NULL,
                    received_at TEXT NOT NULL, answer TEXT NOT NULL, consent INTEGER NOT NULL,
                    payload_hash TEXT NOT NULL, UNIQUE(installation_hash, window_start));
                CREATE INDEX IF NOT EXISTS report_windows ON reports(cell_id, window_start);
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY, cell_id TEXT NOT NULL, window_start TEXT NOT NULL,
                    revision TEXT NOT NULL, decision TEXT NOT NULL, reason TEXT NOT NULL,
                    evidence_url TEXT NOT NULL, reviewed_at TEXT NOT NULL,
                    UNIQUE(cell_id, window_start, revision));
            """)
            yield db
        finally:
            db.close()

    @staticmethod
    def _aggregate(db, cell_id, start):
        if cell_id not in CELL_IDS:
            raise ValueError("Unknown pilot cell")
        begin = timestamp(start)
        if window(begin)[0] != start:
            raise ValueError("Reporting window must start on a UTC quarter hour")
        rows = db.execute("SELECT id, answer, consent FROM reports WHERE cell_id=? AND window_start=? ORDER BY id",
                          (cell_id, start)).fetchall()
        counts = {key: sum(row["answer"] == key for row in rows) for key in ("yes", "no", "unsure")}
        consented = {key: sum(row["answer"] == key and row["consent"] == 1 for row in rows) for key in counts}
        decisive = consented["yes"] + consented["no"]
        agreement = max(consented["yes"], consented["no"]) / decisive if decisive else None
        consensus = "insufficient"
        if decisive >= MIN_REPORTS:
            consensus = ("rain_support" if consented["yes"] > consented["no"] else "dry_support") if agreement >= MIN_AGREEMENT else "conflicting"
        revision = digest({"cell_id": cell_id, "window_start": start, "reports": [row["id"] for row in rows]})
        review = db.execute("SELECT * FROM reviews WHERE cell_id=? AND window_start=? AND revision=?",
                            (cell_id, start, revision)).fetchone()
        prior = db.execute("SELECT 1 FROM reviews WHERE cell_id=? AND window_start=? LIMIT 1", (cell_id, start)).fetchone()
        review_status = review["decision"] if review else "stale" if prior else "pending"
        reviewable_after = begin + timedelta(minutes=30)
        closed = now() >= reviewable_after
        return {"cell_id": cell_id, "window_start_utc": start, "window_end_utc": utc(begin + timedelta(minutes=15)),
                "reviewable_after_utc": utc(reviewable_after), "window_closed": closed,
                "revision": revision, **counts, "consenting_reports": sum(consented.values()),
                "consented_counts": consented, "agreement_fraction": agreement, "consensus": consensus,
                "minimum_reports": MIN_REPORTS, "minimum_agreement": MIN_AGREEMENT,
                "review_status": review_status, "training_eligible": bool(closed and review and review["decision"] == "approve"),
                "evidence_class": "unverified_installation_reports", "independent_people_verified": False,
                "note": "Agreement uses consented yes/no reports. It is not a calibrated probability or gauge truth."}

    def aggregate(self, cell_id, start=None):
        with self.connection() as db:
            return self._aggregate(db, cell_id, start or window(now())[0])

    def submit(self, report):
        if set(report) != {"request_id", "installation_id", "cell_id", "answer", "observed_at_utc", "consent_training"}:
            raise ValueError("Unexpected citizen report fields")
        request_id, installation = str(UUID(report["request_id"])), str(UUID(report["installation_id"]))
        if report["cell_id"] not in CELL_IDS or report["answer"] not in {"yes", "no", "unsure"}:
            raise ValueError("Select a pilot cell and yes, no or unsure")
        if type(report["consent_training"]) is not bool:
            raise ValueError("Training consent must be an explicit boolean")
        observed = timestamp(report["observed_at_utc"])
        normalized = {**report, "request_id": request_id, "installation_id": digest(installation), "observed_at_utc": utc(observed)}
        payload_hash = digest(normalized)
        received = now()
        start, _ = window(observed)
        with self.connection() as db, db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM reports WHERE request_id=?", (request_id,)).fetchone()
            if old:
                if old["payload_hash"] != payload_hash:
                    raise Conflict("This request ID already records a different answer")
                return {"report_id": old["id"], "status": "recorded_unverified", "duplicate": True,
                        "aggregate": self._aggregate(db, old["cell_id"], old["window_start"])}
            if not received - timedelta(minutes=15) <= observed <= received:
                raise ValueError("Report what you observed within the last 15 minutes, using the current device time")
            if db.execute("SELECT COUNT(*) FROM reports").fetchone()[0] >= MAX_REPORTS:
                raise Capacity("Research report store is full; operator maintenance is required")
            if db.execute("SELECT 1 FROM reports WHERE installation_hash=? AND window_start=?", (digest(installation), start)).fetchone():
                raise Conflict("This installation already answered in that 15-minute window")
            report_id = digest({"payload": payload_hash, "received_at_utc": utc(received)})
            db.execute("INSERT INTO reports VALUES (?,?,?,?,?,?,?,?,?,?)", (
                report_id, request_id, digest(installation), report["cell_id"], start, utc(observed), utc(received),
                report["answer"], int(report["consent_training"]), payload_hash))
            return {"report_id": report_id, "status": "recorded_unverified", "duplicate": False,
                    "aggregate": self._aggregate(db, report["cell_id"], start)}

    def review(self, cell_id, start, expected_revision, decision, reason, evidence_url):
        if decision not in {"approve", "reject"} or not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 1000:
            raise ValueError("A review needs approve/reject and a reason of 10 to 1000 characters")
        if not isinstance(evidence_url, str) or len(evidence_url) > 1000:
            raise ValueError("A public corroboration URL is required")
        parsed = urlsplit(evidence_url)
        if evidence_url and (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("Corroboration needs a public HTTPS link without credentials, query tokens or fragments")
        if decision == "approve" and not evidence_url:
            raise ValueError("Approval needs a public HTTPS corroboration link")
        content = {"cell_id": cell_id, "window_start_utc": start, "revision": expected_revision,
                   "decision": decision, "reason": reason.strip(), "evidence_url": evidence_url}
        review_id = digest(content)
        with self.connection() as db, db:
            db.execute("BEGIN IMMEDIATE")
            aggregate = self._aggregate(db, cell_id, start)
            if aggregate["revision"] != expected_revision:
                raise Conflict("Reports changed after review started; refresh the evidence")
            old = db.execute("SELECT id FROM reviews WHERE cell_id=? AND window_start=? AND revision=?",
                             (cell_id, start, expected_revision)).fetchone()
            if old and old["id"] != review_id:
                raise Conflict("This exact evidence revision already has a different review")
            if decision == "approve" and aggregate["consensus"] not in {"rain_support", "dry_support"}:
                raise ValueError("Approval requires sufficient consented agreement and independent corroboration")
            if decision == "approve" and not aggregate["window_closed"]:
                raise ValueError("Approval waits until 15 minutes after the reporting window ends, when late submissions close")
            db.execute("INSERT OR IGNORE INTO reviews VALUES (?,?,?,?,?,?,?,?)", (
                review_id, cell_id, start, expected_revision, decision, reason.strip(), evidence_url, utc(now())))
            return {"review_id": review_id, "aggregate": self._aggregate(db, cell_id, start),
                    "corroboration": "declared checked by local reviewer; URL is not automatically verified"}

    def reviewed_export(self):
        with self.connection() as db:
            rows = db.execute("SELECT * FROM reviews WHERE decision='approve' ORDER BY window_start,cell_id LIMIT 1001").fetchall()
            if len(rows) > 1000:
                raise Capacity("Export exceeds 1000 reviewed windows; use a bounded offline archive workflow")
            result = []
            for row in rows:
                aggregate = self._aggregate(db, row["cell_id"], row["window_start"])
                if aggregate["revision"] != row["revision"] or not aggregate["training_eligible"]:
                    continue
                result.append({"review_id": row["id"], "cell_id": row["cell_id"], "geometry_version": "ncr-pilot-cells-v1",
                               "window_start_utc": row["window_start"], "window_end_utc": aggregate["window_end_utc"],
                               "target": "consented_citizen_rain_presence_report", "value": int(aggregate["consensus"] == "rain_support"),
                               "label_class": "reviewed_weak_evidence", "reviewed_at_utc": row["reviewed_at"],
                               "consenting_reports": aggregate["consenting_reports"], "evidence_url": row["evidence_url"],
                               "revision": row["revision"], "ground_truth": False, "eligible_for_30_minute_amount": False,
                               "eligible_for_lightning": False, "independent_people_verified": False})
            return {"schema_version": 1, "scope": "Reviewed weak rain-presence evidence; requires episode alignment before training",
                    "automatic_retraining": False, "contains_person_identifiers": False, "items": result}

    def recent_windows(self, limit=50):
        with self.connection() as db:
            windows = db.execute("SELECT DISTINCT cell_id,window_start FROM reports ORDER BY window_start DESC LIMIT ?", (limit,)).fetchall()
            return [self._aggregate(db, row["cell_id"], row["window_start"]) for row in windows]

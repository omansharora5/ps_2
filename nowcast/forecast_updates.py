"""Bounded metadata scheduling for one regional worker loop, not a live feed service."""

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
import re


def aware(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Scheduling times must be timezone-aware datetimes")
    return value


@dataclass(frozen=True)
class ForecastTicket:
    region: str
    issued_at: datetime
    revision: int
    input_sha256: str
    model_version: str
    valid_until: datetime

    def __post_init__(self):
        if not isinstance(self.region, str) or not 1 <= len(self.region) <= 80:
            raise ValueError("A bounded region identifier is required")
        if type(self.revision) is not int or self.revision < 0:
            raise ValueError("Revision must be a nonnegative integer")
        if not isinstance(self.input_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", self.input_sha256):
            raise ValueError("An input-manifest SHA-256 is required")
        if not isinstance(self.model_version, str) or not 1 <= len(self.model_version) <= 120:
            raise ValueError("A bounded model version is required")
        if aware(self.valid_until) <= aware(self.issued_at):
            raise ValueError("Validity must extend past issue time")

    @property
    def order(self):
        return self.issued_at, self.revision


class LatestForecastQueue:
    """One owner calls synchronous transitions; compute and persistence stay outside.

    Only configured regions are accepted. Each has at most one waiting ticket,
    one running ticket and one latest-request watermark. No arrays are retained.
    """

    def __init__(self, regions, max_running=1):
        regions = tuple(regions)
        if not 1 <= len(regions) <= 2048 or len(set(regions)) != len(regions):
            raise ValueError("Configure 1–2048 unique regions")
        if any(not isinstance(r, str) or not 1 <= len(r) <= 80 for r in regions):
            raise ValueError("Invalid configured region")
        if type(max_running) is not int or not 1 <= max_running <= len(regions):
            raise ValueError("Running limit must fit the configured region count")
        self._regions = frozenset(regions)
        self._max_running = max_running
        self._pending = OrderedDict()
        self._active = {}
        self._latest = {}

    def submit(self, ticket, *, now):
        aware(now)
        if ticket.region not in self._regions:
            raise ValueError("Region is outside this worker's configured coverage")
        if ticket.issued_at > now:
            raise ValueError("A future-issued forecast cannot be queued yet")
        if ticket.valid_until <= now:
            return False
        previous = self._latest.get(ticket.region)
        if previous:
            if ticket.order < previous.order:
                return False
            if ticket.order == previous.order:
                if ticket != previous:
                    raise ValueError("Conflicting manifests/model/validity for one issue and revision")
                return False
        self._latest[ticket.region] = ticket
        self._pending[ticket.region] = ticket
        return True

    def take(self, *, now):
        aware(now)
        if len(self._active) >= self._max_running:
            return None
        for region, ticket in list(self._pending.items()):
            if ticket.valid_until <= now:
                del self._pending[region]
            elif region not in self._active and ticket.issued_at <= now:
                del self._pending[region]
                self._active[region] = ticket
                return ticket
        return None

    def complete(self, ticket, *, now, succeeded=True):
        aware(now)
        if self._active.get(ticket.region) != ticket:
            return False
        del self._active[ticket.region]
        return bool(succeeded and self._latest[ticket.region] == ticket and ticket.issued_at <= now < ticket.valid_until)

    def counts(self):
        return {"configured_regions": len(self._regions), "pending": len(self._pending),
                "running": len(self._active), "watermarks": len(self._latest), "max_running": self._max_running}

"""Instrument-gap ledger: every coverage failure is recorded, never dropped."""
import csv
import datetime as dt
from pathlib import Path

COLUMNS = ["utc", "source", "query_or_id", "failure_kind", "detail"]
KINDS = {"no_token", "rate_limited", "http_error", "not_indexed", "paywalled", "parse_error"}


def utcnow():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class GapLedger:
    def __init__(self, path):
        self.path = Path(path)

    def log(self, source, query_or_id, kind, detail=""):
        if kind not in KINDS:
            raise ValueError("unknown failure_kind %r" % kind)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists() or self.path.stat().st_size == 0
        with self.path.open("a", newline="") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(COLUMNS)
            w.writerow([utcnow(), source, query_or_id, kind, " ".join(str(detail).split())[:500]])

    def read(self, since=None):
        if not self.path.exists():
            return []
        with self.path.open(newline="") as fh:
            rows = list(csv.DictReader(fh))
        if since:
            rows = [r for r in rows if r["utc"] >= since]
        return rows

"""Shared client base: gap logging around every request."""
from nacre.retrieval import gaps
from nacre.retrieval.http import HttpError


class Client:
    name = ""

    def __init__(self, http, config, ledger):
        self.http, self.config, self.ledger = http, config, ledger

    def gap(self, query_or_id, kind, detail=""):
        self.ledger.log(self.name, query_or_id, kind, detail)

    def fetch(self, query_or_id, url, **kw):
        """GET/POST a URL; on any failure log a gap and return None."""
        method = kw.pop("method", "GET")
        try:
            return self.http.request(self.name, method, url, **kw)
        except HttpError as exc:
            self.gap(query_or_id, exc.kind, exc.detail)
            return None

    def json_or_gap(self, query_or_id, resp):
        if resp is None:
            return None
        try:
            return resp.json()
        except HttpError as exc:
            self.gap(query_or_id, exc.kind, exc.detail)
            return None

    def empty_gap(self, query_or_id):
        self.gap(query_or_id, "not_indexed", "no results")

    def now(self):
        return gaps.utcnow()

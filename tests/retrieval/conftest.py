import json

import pytest

from nacre.retrieval.config import Config
from nacre.retrieval.gaps import GapLedger
from nacre.retrieval.http import Http

SECRET = "SECRET-ABSTRACT-TEXT-must-not-be-stored"


class FakeResp:
    def __init__(self, status=200, text="{}", headers=None):
        self.status_code, self.text, self.headers = status, text, headers or {}


class FakeSession:
    """Scripted session: pops one response per request and records the calls."""

    def __init__(self, script):
        self.script, self.calls, self.headers = list(script), [], {}

    def request(self, method, url, params=None, headers=None, json=None, timeout=None):
        self.calls.append((method, url, params, headers, json))
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def cfg(tmp_path):
    c = Config(root=tmp_path, env={})
    c.contact = {"mailto": "tester@example.org", "user_agent": "test-agent"}
    c.sources = {"crossref": {"min_interval": 0.5, "timeout": 5}}
    return c


@pytest.fixture
def ledger(tmp_path):
    return GapLedger(tmp_path / "lit" / "instrument_gaps.csv")


def make_http(cfg, script, sleeps=None, rng=lambda: 0.5, clock=None):
    sleeps = sleeps if sleeps is not None else []
    kw = {"clock": clock} if clock else {}
    http = Http(cfg, session=FakeSession(script), sleep=sleeps.append, rng=rng, **kw)
    return http, sleeps


def ok(payload):
    return FakeResp(200, json.dumps(payload))

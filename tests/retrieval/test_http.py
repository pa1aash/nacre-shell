import json

import pytest
import requests

from retrieval_helpers import FakeResp, cfg, make_http, ok  # noqa: F401
from nacre.retrieval.http import HttpError, parse_retry_after

URL = "https://api.example.org/x"


def test_backoff_429_respects_retry_after(cfg):
    http, sleeps = make_http(cfg, [FakeResp(429, "", {"Retry-After": "7"}), FakeResp(429, "", {"Retry-After": "3"}), ok({"a": 1})])
    resp = http.get("other", URL)
    assert resp.json() == {"a": 1}
    assert sleeps == [7.0, 3.0]


def test_backoff_exponential_with_jitter_on_5xx(cfg):
    http, sleeps = make_http(cfg, [FakeResp(503), FakeResp(502), FakeResp(500), ok({})], rng=lambda: 0.0)
    http.get("other", URL)
    # base 1 s doubling; jitter factor 0.5 + rng/2 = 0.5 with rng 0
    assert sleeps == [0.5, 1.0, 2.0]


def test_exhausted_429_is_rate_limited(cfg):
    http, sleeps = make_http(cfg, [FakeResp(429)] * 3)
    http.max_retries = 2
    with pytest.raises(HttpError) as ei:
        http.get("other", URL)
    assert ei.value.kind == "rate_limited" and len(sleeps) == 2


def test_network_exception_retries_then_http_error(cfg):
    http, sleeps = make_http(cfg, [requests.ConnectionError("down")] * 2)
    http.max_retries = 1
    with pytest.raises(HttpError) as ei:
        http.get("other", URL)
    assert ei.value.kind == "http_error" and "ConnectionError" in ei.value.detail


def test_404_not_indexed_and_4xx_http_error_no_retry(cfg):
    http, sleeps = make_http(cfg, [FakeResp(404)])
    with pytest.raises(HttpError) as ei:
        http.get("other", URL)
    assert ei.value.kind == "not_indexed" and sleeps == []
    http, _ = make_http(cfg, [FakeResp(403)])
    with pytest.raises(HttpError) as ei:
        http.get("other", URL)
    assert ei.value.kind == "http_error" and ei.value.status == 403


def test_cache_hit_skips_network(cfg):
    http, _ = make_http(cfg, [ok({"n": 1})])
    first = http.get("other", URL, params={"q": "a"})
    second = http.get("other", URL, params={"q": "a"})
    assert second.from_cache and second.json() == {"n": 1} and first.cache_key == second.cache_key
    assert len(http.session.calls) == 1
    assert (cfg.cache_dir / first.cache_key[:2] / (first.cache_key + ".json")).exists()


def test_errors_are_not_cached(cfg):
    http, _ = make_http(cfg, [FakeResp(403), ok({"n": 2})])
    with pytest.raises(HttpError):
        http.get("other", URL)
    assert http.get("other", URL).json() == {"n": 2}


def test_per_source_rate_limit_sleeps(cfg):
    now = [100.0]
    http, sleeps = make_http(cfg, [ok({}), ok({})], clock=lambda: now[0])
    http.get("crossref", URL, params={"q": 1})
    now[0] += 0.2
    http.get("crossref", URL, params={"q": 2})
    assert sleeps == [pytest.approx(0.3)]


def test_user_agent_carries_mailto(cfg):
    http, _ = make_http(cfg, [])
    assert "mailto:tester@example.org" in http.session.headers["User-Agent"]


def test_invalid_json_is_parse_error(cfg):
    http, _ = make_http(cfg, [FakeResp(200, "<html>")])
    with pytest.raises(HttpError) as ei:
        http.get("other", URL).json()
    assert ei.value.kind == "parse_error"


def test_retry_after_http_date_and_garbage():
    assert parse_retry_after("12") == 12.0
    assert parse_retry_after(None) is None
    assert parse_retry_after("soon") is None
    assert parse_retry_after("Thu, 01 Jan 1970 00:00:10 GMT", now=4.0) == 6.0


def test_tls_failure_is_not_retried(cfg):
    http, sleeps = make_http(cfg, [requests.exceptions.SSLError("bad cert")])
    with pytest.raises(HttpError) as ei:
        http.get("other", URL)
    assert ei.value.kind == "http_error" and "not retried" in ei.value.detail
    assert sleeps == [] and len(http.session.calls) == 1


class _Clock:
    """Mocked time: sleeping advances the clock, so the retry budget is measured in mocked seconds."""

    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def _capped_http(cfg, script, clock, lines, **kw):
    from nacre.retrieval.http import Http
    from retrieval_helpers import FakeSession
    return Http(cfg, session=FakeSession(script), sleep=clock.sleep, clock=clock, rng=lambda: 1.0,
                log=lines.append, **kw)


def test_retry_wall_time_is_capped(cfg):
    clock, lines = _Clock(), []
    http = _capped_http(cfg, [FakeResp(503)] * 20, clock, lines, max_retries=20, base_delay=10.0, max_delay=40.0,
                        max_total_retry_seconds=120.0)
    with pytest.raises(HttpError) as ei:
        http.get("other", URL)
    assert ei.value.kind == "http_error" and "retry time cap 120 s" in ei.value.detail
    assert clock.now - 1000.0 <= 120.0
    assert len(http.session.calls) < 21
    assert lines[-1].startswith("retry: giving up")


def test_each_retry_logs_one_progress_line(cfg):
    clock, lines = _Clock(), []
    http = _capped_http(cfg, [FakeResp(503), FakeResp(502), ok({"a": 1})], clock, lines)
    assert http.get("other", URL).json() == {"a": 1}
    assert len(lines) == 2 == len(clock.sleeps)
    assert lines[0].startswith("retry 1/5 in") and "HTTP 503" in lines[0] and URL in lines[0]
    assert lines[1].startswith("retry 2/5 in") and "HTTP 502" in lines[1]


def test_retry_after_longer_than_budget_gives_up_without_sleeping(cfg):
    clock, lines = _Clock(), []
    http = _capped_http(cfg, [FakeResp(429, "", {"Retry-After": "300"})] * 3, clock, lines,
                        max_total_retry_seconds=120.0)
    with pytest.raises(HttpError) as ei:
        http.get("other", URL)
    assert ei.value.kind == "rate_limited" and clock.sleeps == []
    assert len(http.session.calls) == 1 and len(lines) == 1


def test_success_path_is_silent_and_default_cap_is_120(cfg):
    clock, lines = _Clock(), []
    http = _capped_http(cfg, [ok({"n": 1})], clock, lines)
    assert http.max_total_retry_seconds == 120.0
    assert http.get("other", URL).json() == {"n": 1}
    assert lines == [] and clock.sleeps == []


def test_cap_none_restores_unbounded_retries(cfg):
    clock, lines = _Clock(), []
    http = _capped_http(cfg, [FakeResp(503)] * 4, clock, lines, max_retries=3, base_delay=100.0, max_delay=100.0,
                        max_total_retry_seconds=None)
    with pytest.raises(HttpError) as ei:
        http.get("other", URL)
    assert "retry time cap" not in ei.value.detail and len(http.session.calls) == 4

import json

import pytest
import requests

from conftest import FakeResp, make_http, ok
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

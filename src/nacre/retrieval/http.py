"""One HTTP session with per-source rate limits, backoff and a raw-response cache."""
import email.utils
import hashlib
import json
import random
import time
from pathlib import Path

import requests

from nacre.retrieval import gaps as _gaps


class HttpError(Exception):
    """A request failed; `kind` is an instrument-gap failure_kind."""

    def __init__(self, kind, detail, status=None):
        super().__init__("%s: %s" % (kind, detail))
        self.kind, self.detail, self.status = kind, detail, status


class Response:
    def __init__(self, status, text, cache_key, from_cache=False):
        self.status, self.text, self.cache_key, self.from_cache = status, text, cache_key, from_cache

    def json(self):
        try:
            return json.loads(self.text)
        except ValueError as exc:
            raise HttpError("parse_error", "invalid JSON: %s" % exc, self.status)


def cache_key(method, url, params=None, body=None):
    blob = json.dumps([method, url, sorted((params or {}).items()), body], sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def parse_retry_after(value, now=None):
    if value is None:
        return None
    value = str(value).strip()
    if value.isdigit():
        return float(value)
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    now = now if now is not None else time.time()
    return max(0.0, when.timestamp() - now)


class Http:
    def __init__(self, config, session=None, sleep=time.sleep, clock=time.monotonic,
                 rng=random.random, max_retries=5, base_delay=1.0, max_delay=60.0):
        self.config = config
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = config.user_agent
        self.sleep, self.clock, self.rng = sleep, clock, rng
        self.max_retries, self.base_delay, self.max_delay = max_retries, base_delay, max_delay
        self._last = {}

    def _throttle(self, source):
        gap = float(self.config.source(source).get("min_interval", 0))
        last = self._last.get(source)
        if last is not None:
            wait = gap - (self.clock() - last)
            if wait > 0:
                self.sleep(wait)
        self._last[source] = self.clock()

    def _cache_path(self, key):
        return Path(self.config.cache_dir) / key[:2] / (key + ".json")

    def _delay(self, attempt, retry_after):
        if retry_after is not None:
            return min(retry_after, self.max_delay * 5)
        return min(self.max_delay, self.base_delay * 2 ** attempt) * (0.5 + self.rng() / 2)

    def request(self, source, method, url, params=None, headers=None, json_body=None, use_cache=True):
        body = json.dumps(json_body, sort_keys=True) if json_body is not None else None
        key = cache_key(method, url, params, body)
        path = self._cache_path(key)
        if use_cache and path.exists():
            try:
                hit = json.loads(path.read_text())
                return Response(hit["status"], hit["text"], key, from_cache=True)
            except (ValueError, KeyError):
                pass
        timeout = float(self.config.source(source).get("timeout", 30))
        last_detail, last_status = "", None
        for attempt in range(self.max_retries + 1):
            self._throttle(source)
            try:
                r = self.session.request(method, url, params=params, headers=headers,
                                         json=json_body, timeout=timeout)
            except requests.exceptions.SSLError as exc:
                raise HttpError("http_error", "TLS failure, not retried: %s" % exc)
            except requests.RequestException as exc:
                last_detail, last_status, retry_after = "%s: %s" % (type(exc).__name__, exc), None, None
            else:
                last_status = r.status_code
                if r.status_code == 429 or r.status_code >= 500:
                    last_detail = "HTTP %d" % r.status_code
                    retry_after = parse_retry_after(r.headers.get("Retry-After"))
                elif r.status_code == 404:
                    raise HttpError("not_indexed", "HTTP 404 %s" % url, 404)
                elif r.status_code >= 400:
                    raise HttpError("http_error", "HTTP %d %s" % (r.status_code, url), r.status_code)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps({"url": url, "status": r.status_code, "text": r.text}))
                    return Response(r.status_code, r.text, key)
            if attempt < self.max_retries:
                self.sleep(self._delay(attempt, retry_after))
        kind = "rate_limited" if last_status == 429 else "http_error"
        raise HttpError(kind, "%s after %d attempts (%s)" % (last_detail, self.max_retries + 1, url), last_status)

    def get(self, source, url, **kw):
        return self.request(source, "GET", url, **kw)

    def post(self, source, url, **kw):
        return self.request(source, "POST", url, **kw)

    def download(self, source, url, dest, headers=None):
        """Stream a binary file to `dest` (never cached as text); returns bytes written."""
        timeout = float(self.config.source(source).get("timeout", 30))
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(self.max_retries + 1):
            self._throttle(source)
            try:
                r = self.session.get(url, headers=headers, timeout=timeout, stream=True)
            except requests.exceptions.SSLError as exc:
                raise HttpError("http_error", "TLS failure, not retried: %s" % exc)
            except requests.RequestException as exc:
                last, retry_after, status = "%s: %s" % (type(exc).__name__, exc), None, None
            else:
                status = r.status_code
                if status == 429 or status >= 500:
                    last, retry_after = "HTTP %d" % status, parse_retry_after(r.headers.get("Retry-After"))
                elif status >= 400:
                    raise HttpError("not_indexed" if status == 404 else "http_error",
                                    "HTTP %d %s" % (status, url), status)
                else:
                    n = 0
                    with dest.open("wb") as fh:
                        for chunk in r.iter_content(65536):
                            fh.write(chunk)
                            n += len(chunk)
                    return n
            if attempt < self.max_retries:
                self.sleep(self._delay(attempt, retry_after))
        raise HttpError("rate_limited" if status == 429 else "http_error", "%s (%s)" % (last, url), status)

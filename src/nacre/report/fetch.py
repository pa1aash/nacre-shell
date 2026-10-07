"""Headless retrieval helper (standard library only).

get(url) fetches a URL with a descriptive User-Agent, retries with backoff on
429 and 5xx, and falls back to the Wayback Machine when the live fetch fails or
looks blocked. Every request is appended to a JSONL log and the raw response is
stored in a content-addressed cache.
"""
import hashlib
import json
import mimetypes
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "nacre-shell-venue-fetch/0.1 (research repository; mailto:palaashgang@gmail.com)"
WAYBACK_PREFIX = "https://web.archive.org/web/2id_/"
RETRY_STATUSES = {429, 500, 502, 503, 504}
BLOCK_MARKERS = (b"cf-chl", b"Attention Required", b"Access Denied", b"Request unsuccessful")

_EXT_OVERRIDES = {"text/html": ".html", "application/zip": ".zip", "application/pdf": ".pdf",
                  "application/x-zip-compressed": ".zip", "application/json": ".json"}


def _utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_venue_dir():
    from nacre import _util
    return _util.repo_root() / "charter" / "venue"


@dataclass
class Result:
    url: str
    final_url: str = ""
    via: str = ""            # live | wayback
    status: int = 0
    content: bytes = b""
    content_type: str = ""
    sha256: str = ""
    path: Path = None
    error: str = ""
    retrieved_utc: str = ""
    attempts: list = field(default_factory=list)

    @property
    def ok(self):
        return 200 <= self.status < 300 and not self.error

    def text(self):
        m = re.search(r"charset=([\w-]+)", self.content_type or "")
        return self.content.decode(m.group(1) if m else "utf-8", errors="replace")


class Fetcher:
    def __init__(self, venue_dir=None, wayback_prefix=WAYBACK_PREFIX, retries=3, backoff=1.5,
                 timeout=30, sleep=time.sleep, user_agent=USER_AGENT):
        self.venue_dir = Path(venue_dir) if venue_dir else default_venue_dir()
        self.cache_dir = self.venue_dir / "_cache"
        self.log_path = self.venue_dir / "fetch_log.jsonl"
        self.wayback_prefix = wayback_prefix
        self.retries = retries
        self.backoff = backoff
        self.timeout = timeout
        self.sleep = sleep
        self.user_agent = user_agent

    # -- single request, no fallback ------------------------------------
    def _request(self, url, accept):
        headers = {"User-Agent": self.user_agent}
        if accept:
            headers["Accept"] = accept
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
                return resp.status, resp.geturl(), resp.headers.get("Content-Type", ""), body, "", None
        except urllib.error.HTTPError as exc:
            body = exc.read() if hasattr(exc, "read") else b""
            return exc.code, exc.geturl() or url, exc.headers.get("Content-Type", "") if exc.headers else "", body, \
                "HTTP %d" % exc.code, exc.headers.get("Retry-After") if exc.headers else None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return 0, url, "", b"", "%s: %s" % (type(exc).__name__, exc), None

    def _with_retries(self, url, accept):
        last = None
        for attempt in range(self.retries + 1):
            last = self._request(url, accept)
            status, _, _, _, err, retry_after = last
            if not err:
                return last
            if status in RETRY_STATUSES or status == 0:
                if attempt < self.retries:
                    delay = self.backoff * (2 ** attempt)
                    if retry_after and retry_after.isdigit():
                        delay = max(delay, min(int(retry_after), 60))
                    self.sleep(delay)
                    continue
            break
        return last

    @staticmethod
    def _blocked(status, body):
        if status in (401, 403, 451):
            return True
        return status == 200 and len(body) < 20000 and any(m in body for m in BLOCK_MARKERS)

    def _ext(self, content_type, url):
        ctype = (content_type or "").split(";")[0].strip().lower()
        if ctype in _EXT_OVERRIDES:
            return _EXT_OVERRIDES[ctype]
        guess = mimetypes.guess_extension(ctype) if ctype else None
        if guess:
            return guess
        suffix = Path(urllib.parse.urlparse(url).path).suffix
        return suffix if re.fullmatch(r"\.[A-Za-z0-9]{1,5}", suffix or "") else ".bin"

    def _record(self, res):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {"utc": res.retrieved_utc, "url": res.url, "final_url": res.final_url, "via": res.via,
               "status": res.status, "bytes": len(res.content), "sha256": res.sha256,
               "content_type": res.content_type, "error": res.error}
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    def _finish(self, url, via, got):
        status, final_url, ctype, body, err, _ = got
        res = Result(url=url, final_url=final_url, via=via, status=status, content=body,
                     content_type=ctype, error=err, retrieved_utc=_utc())
        if body:
            res.sha256 = hashlib.sha256(body).hexdigest()
            if not err:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                res.path = self.cache_dir / (res.sha256 + self._ext(ctype, final_url or url))
                if not res.path.exists():
                    res.path.write_bytes(body)
        self._record(res)
        return res

    # -- public ---------------------------------------------------------
    def get(self, url, accept=None, wayback=True):
        got = self._with_retries(url, accept)
        status, _, _, body, err, _ = got
        if not err and not self._blocked(status, body):
            return self._finish(url, "live", got)
        if not err:
            got = got[:4] + ("blocked",) + got[5:]
        live = self._finish(url, "live", got)
        if not wayback:
            return live
        got2 = self._with_retries(self.wayback_prefix + url, accept)
        status2, _, _, body2, err2, _ = got2
        if not err2 and not self._blocked(status2, body2):
            res = self._finish(url, "wayback", got2)
            res.attempts = ["live: " + live.error]
            return res
        if not err2:
            got2 = got2[:4] + ("blocked",) + got2[5:]
        res = self._finish(url, "wayback", got2)
        res.attempts = ["live: " + live.error]
        res.error = "live: %s; wayback: %s" % (live.error, res.error)
        return res


def get(url, **kwargs):
    fetcher_args = {k: kwargs.pop(k) for k in list(kwargs)
                    if k in ("venue_dir", "wayback_prefix", "retries", "backoff", "timeout", "sleep")}
    return Fetcher(**fetcher_args).get(url, **kwargs)

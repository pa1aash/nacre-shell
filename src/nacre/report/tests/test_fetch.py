import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from nacre.report.fetch import Fetcher, USER_AGENT


class _Handler(BaseHTTPRequestHandler):
    hits = {}
    seen_agents = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        cls = type(self)
        cls.hits[self.path] = cls.hits.get(self.path, 0) + 1
        cls.seen_agents.append(self.headers.get("User-Agent"))
        n = cls.hits[self.path]
        if self.path == "/ok":
            self._send(200, b"<html>ok</html>", "text/html; charset=utf-8")
        elif self.path == "/flaky":
            if n < 3:
                self._send(429 if n == 1 else 503, b"slow down", "text/plain", {"Retry-After": "0"})
            else:
                self._send(200, b"recovered", "text/plain")
        elif self.path == "/forbidden":
            self._send(403, b"no", "text/plain")
        elif self.path == "/challenge":
            self._send(200, b"<html>cf-chl challenge</html>", "text/html")
        elif self.path == "/gone":
            self._send(404, b"gone", "text/plain")
        elif self.path.startswith("/wb/") and self.path.endswith(("/forbidden", "/challenge")):
            self._send(200, b"archived copy", "text/html")
        elif self.path.startswith("/wb/"):
            self._send(404, b"not archived", "text/plain")
        else:
            self._send(404, b"?", "text/plain")

    def _send(self, code, body, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def server():
    _Handler.hits = {}
    _Handler.seen_agents = []
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield "http://127.0.0.1:%d" % srv.server_address[1]
    srv.shutdown()
    srv.server_close()


@pytest.fixture()
def fetcher(tmp_path, server):
    return Fetcher(venue_dir=tmp_path, wayback_prefix=server + "/wb/", retries=3, backoff=0.0,
                   sleep=lambda s: None, timeout=5)


def _log(tmp_path):
    return [json.loads(x) for x in (tmp_path / "fetch_log.jsonl").read_text(encoding="utf-8").splitlines()]


def test_live_fetch_records_and_caches(fetcher, server, tmp_path):
    res = fetcher.get(server + "/ok")
    assert res.ok and res.via == "live" and res.status == 200
    assert res.sha256 == hashlib.sha256(b"<html>ok</html>").hexdigest()
    assert res.path.parent == tmp_path / "_cache" and res.path.name == res.sha256 + ".html"
    assert res.path.read_bytes() == b"<html>ok</html>"
    row = _log(tmp_path)[0]
    assert set(row) == {"utc", "url", "final_url", "via", "status", "bytes", "sha256", "content_type", "error"}
    assert row["via"] == "live" and row["bytes"] == 15 and row["error"] == ""


def test_user_agent_identifies_operator(fetcher, server):
    fetcher.get(server + "/ok")
    assert _Handler.seen_agents[0] == USER_AGENT
    assert "mailto:" in USER_AGENT


def test_retries_on_429_and_5xx(fetcher, server):
    res = fetcher.get(server + "/flaky")
    assert res.ok and res.content == b"recovered" and _Handler.hits["/flaky"] == 3


def test_retry_sleeps_back_off(server, tmp_path):
    delays = []
    f = Fetcher(venue_dir=tmp_path, wayback_prefix=server + "/wb/", retries=3, backoff=2.0,
                sleep=delays.append, timeout=5)
    f.get(server + "/flaky")
    assert delays == [2.0, 4.0]


def test_forbidden_falls_back_to_wayback(fetcher, server, tmp_path):
    res = fetcher.get(server + "/forbidden")
    assert res.ok and res.via == "wayback" and res.content == b"archived copy"
    rows = _log(tmp_path)
    assert [r["via"] for r in rows] == ["live", "wayback"]
    assert rows[0]["error"] == "HTTP 403"


def test_challenge_page_is_treated_as_blocked(fetcher, server):
    res = fetcher.get(server + "/challenge")
    assert res.via == "wayback" and res.ok


def test_both_fail_reports_error_and_logs_both(fetcher, server, tmp_path):
    res = fetcher.get(server + "/gone")
    assert not res.ok and "live: HTTP 404" in res.error and "wayback: HTTP 404" in res.error
    assert res.path is None
    assert len(_log(tmp_path)) == 2


def test_wayback_can_be_disabled(fetcher, server):
    res = fetcher.get(server + "/forbidden", wayback=False)
    assert not res.ok and res.via == "live"


def test_unreachable_host_is_an_error_not_a_crash(tmp_path):
    f = Fetcher(venue_dir=tmp_path, wayback_prefix="http://127.0.0.1:9/wb", retries=0, backoff=0.0,
                sleep=lambda s: None, timeout=2)
    res = f.get("http://127.0.0.1:9/x")
    assert not res.ok and res.error

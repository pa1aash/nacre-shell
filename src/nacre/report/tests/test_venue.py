import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import yaml

from nacre.report import venue
from nacre.report.fetch import Fetcher

PAGE = {"body": b"<html><h1>Limits</h1><p>The limit is 8000 words</p></html>"}


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = PAGE["body"]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def server():
    srv = HTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:%d/page" % srv.server_address[1]
    srv.shutdown()
    srv.server_close()


def _field(url, value="8000 words", **kw):
    f = {"value": value, "source_url": url, "locator": "Limits", "retrieved_utc": "2026-01-01T00:00:00Z", "via": "live"}
    f.update(kw)
    return f


def _write(root, name, fields):
    d = root / "charter" / "venue"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(yaml.safe_dump({"fields": fields}), encoding="utf-8")


def _template(root):
    (root / "charter" / "venue" / "template.yaml").write_text(yaml.safe_dump(
        {"archive_url": "http://x/y.zip", "retrieved_utc": "t", "archive_sha256": "ab", "files": [{"path": "a"}]}),
        encoding="utf-8")


def test_coverage_counts_nulls(tmp_path):
    _write(tmp_path, "manuscript.yaml", {"a": _field("u"), "b": {"value": None}})
    _write(tmp_path, "artwork.yaml", {"c": _field("u")})
    assert venue.coverage(tmp_path) == {"manuscript.yaml": (1, 2), "artwork.yaml": (1, 1)}


def test_consistency_clean(tmp_path):
    _write(tmp_path, "manuscript.yaml", {"a": _field("u"), "b": {"value": None}})
    _write(tmp_path, "artwork.yaml", {})
    _template(tmp_path)
    assert venue.consistency(tmp_path) == []


def test_consistency_flags_missing_source_and_long_passage(tmp_path):
    long = " ".join(["word"] * 40)
    _write(tmp_path, "manuscript.yaml", {"a": _field("u", retrieved_utc=None), "b": _field("u", value=long),
                                          "c": _field("u", via="cache")})
    _write(tmp_path, "artwork.yaml", {})
    _template(tmp_path)
    text = "\n".join(venue.consistency(tmp_path))
    assert "a: value present but retrieved_utc missing" in text
    assert "b: string value over" in text
    assert "c: via must be live or wayback" in text


def test_refresh_unchanged_then_changed_and_stale(tmp_path, server):
    _write(tmp_path, "manuscript.yaml", {"limit": _field(server)})
    _write(tmp_path, "artwork.yaml", {})
    f = Fetcher(venue_dir=tmp_path / "charter" / "venue", retries=0, sleep=lambda s: None, timeout=5)
    lines, changed = venue.refresh(tmp_path, f)
    assert changed == 0 and "new" in lines[0]
    lines, changed = venue.refresh(tmp_path, f)
    assert changed == 0 and lines[0].startswith("unchanged")
    PAGE["body"] = b"<html><p>The limit is now different</p></html>"
    try:
        lines, changed = venue.refresh(tmp_path, f)
    finally:
        PAGE["body"] = b"<html><h1>Limits</h1><p>The limit is 8000 words</p></html>"
    assert changed == 1 and lines[0].startswith("CHANGED")
    assert any("stale?" in ln and "8000 words" in ln for ln in lines)


def test_show_filters(tmp_path):
    _write(tmp_path, "manuscript.yaml", {"abstract.max": _field("u", value=250, unit="words"), "x.y": _field("u")})
    _write(tmp_path, "artwork.yaml", {})
    rows = venue.show(tmp_path, "manuscript", "abstract")
    assert len(rows) == 1 and "250" in rows[0] and "words" in rows[0]

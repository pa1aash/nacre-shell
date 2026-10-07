import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote

import pytest

from nacre.report import bib
from nacre.report.fetch import Fetcher

SYNTH = ("@article{Synthetic_2000,\n  title={A Synthetic Record for Testing},\n  author={Testauthor, Alice and Other, Bob},\n"
         "  year={2000},\n  doi={10.0000/nacre.test},\n  journal={Journal of Synthetic Records}\n}\n")
SYNTH2 = SYNTH.replace("Synthetic_2000", "Synthetic_2000b").replace("nacre.test", "nacre.test2")


class _H(BaseHTTPRequestHandler):
    routes = {}

    def log_message(self, *a):
        pass

    def do_GET(self):
        code, ctype, body = self.routes.get(unquote(self.path), (404, "text/plain", b"none"))
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def env(tmp_path):
    _H.routes = {}
    srv = HTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    (tmp_path / "paper").mkdir()
    fetcher = Fetcher(venue_dir=tmp_path / "f", retries=0, sleep=lambda s: None, timeout=5)
    kw = {"fetcher": fetcher, "doi_base": base + "/doi/", "crossref_base": base + "/works/", "out": lambda *a: None}
    yield tmp_path, kw
    srv.shutdown()
    srv.server_close()


def _serve_doi(doi, body=SYNTH, ctype="application/x-bibtex"):
    _H.routes["/doi/" + doi] = (200, ctype, body.encode())


def test_normalise_doi():
    assert bib.normalise_doi("https://doi.org/10.0000/NACRE.Test") == "10.0000/nacre.test"
    assert bib.normalise_doi("http://dx.doi.org/10.0000/x") == "10.0000/x"
    assert bib.normalise_doi("doi: 10.0000/x") == "10.0000/x"
    with pytest.raises(bib.BibError):
        bib.normalise_doi("not-a-doi")


def test_add_stores_entry_with_deterministic_key_and_provenance(env):
    root, kw = env
    _serve_doi("10.0000/nacre.test")
    assert bib.add(root, "https://doi.org/10.0000/NACRE.test", **kw) == 0
    text = (root / "paper" / "refs.bib").read_text(encoding="utf-8")
    assert text.startswith("@article{testauthor2000synthetic,")
    assert "title={A Synthetic Record for Testing}" in text  # as fetched
    rec = json.loads((root / "paper" / "bib" / "provenance.jsonl").read_text().splitlines()[0])
    assert rec["doi"] == "10.0000/nacre.test" and rec["key"] == "testauthor2000synthetic"
    assert rec["original_key"] == "Synthetic_2000" and len(rec["sha256"]) == 64 and rec["retrieved_utc"]
    assert bib.check(root, out=lambda *a: None) == 0


def test_dedupe_by_doi(env):
    root, kw = env
    _serve_doi("10.0000/nacre.test")
    bib.add(root, "10.0000/nacre.test", **kw)
    bib.add(root, "https://doi.org/10.0000/NACRE.TEST", **kw)
    assert (root / "paper" / "refs.bib").read_text().count("@article") == 1
    assert len((root / "paper" / "bib" / "provenance.jsonl").read_text().splitlines()) == 1


def test_key_collision_gets_suffix(env):
    root, kw = env
    _serve_doi("10.0000/nacre.test")
    _serve_doi("10.0000/nacre.test2", SYNTH2)
    bib.add(root, "10.0000/nacre.test", **kw)
    bib.add(root, "10.0000/nacre.test2", **kw)
    keys = [json.loads(x)["key"] for x in (root / "paper" / "bib" / "provenance.jsonl").read_text().splitlines()]
    assert keys == ["testauthor2000synthetic", "testauthor2000synthetica"]


def test_make_key_skips_stopwords_and_folds_accents():
    entry = "@article{x,\n author={M\\\"uller, Jos\\'e},\n title={The Study of a Catalysis},\n year={1999}\n}"
    assert bib.make_key(entry, set()) == "muller1999study"
    assert bib.make_key(entry, {"muller1999study"}) == "muller1999studya"


def test_one_line_entry_from_server(env):
    root, kw = env
    one = "@article{Key_1, title={Single Line Entry}, author={Zed, Ann}, year={2001}, doi={10.0000/nacre.test}}"
    _serve_doi("10.0000/nacre.test", one)
    bib.add(root, "10.0000/nacre.test", **kw)
    assert (root / "paper" / "refs.bib").read_text().startswith("@article{zed2001single,")


def test_fallback_to_crossref_transform(env):
    root, kw = env
    _H.routes["/doi/10.0000/nacre.test"] = (404, "text/plain", b"nope")
    _H.routes["/works/10.0000/nacre.test/transform/application/x-bibtex"] = (200, "application/x-bibtex", SYNTH.encode())
    assert bib.add(root, "10.0000/nacre.test", **kw) == 0
    rec = json.loads((root / "paper" / "bib" / "provenance.jsonl").read_text().splitlines()[0])
    assert "/works/" in rec["url"]


def test_refuses_non_bibtex_response(env):
    root, kw = env
    _serve_doi("10.0000/nacre.test", "<html>landing page</html>", "text/html")
    with pytest.raises(bib.BibError):
        bib.add(root, "10.0000/nacre.test", **kw)
    assert not (root / "paper" / "refs.bib").exists()
    assert not (root / "paper" / "bib").exists()


def test_dry_run_writes_nothing(env):
    root, kw = env
    _serve_doi("10.0000/nacre.test")
    printed = []
    kw["out"] = printed.append
    assert bib.add(root, "10.0000/nacre.test", dry_run=True, **kw) == 0
    assert any("testauthor2000synthetic" in p for p in printed)
    assert not (root / "paper" / "refs.bib").exists() and not (root / "paper" / "bib").exists()


def test_check_flags_missing_provenance_and_orphans(env):
    root, kw = env
    (root / "paper" / "refs.bib").write_text("@article{orphan2000,\n  title={x},\n  doi={10.0000/o}\n}\n", encoding="utf-8")
    assert bib.check(root, out=lambda *a: None) == 1
    (root / "paper" / "refs.bib").write_text("", encoding="utf-8")
    (root / "paper" / "bib").mkdir()
    (root / "paper" / "bib" / "provenance.jsonl").write_text(
        json.dumps({"doi": "10.0000/o", "key": "gone", "original_key": "g", "url": "u", "retrieved_utc": "t", "sha256": "s"}) + "\n")
    assert bib.check(root, out=lambda *a: None) == 1

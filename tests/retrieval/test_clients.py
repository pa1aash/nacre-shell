import csv
import json

from conftest import FakeResp, make_http, ok
from nacre.retrieval import gaps
from nacre.retrieval.crossref import Crossref
from nacre.retrieval.http import HttpError
from nacre.retrieval.lens import Lens
from nacre.retrieval.semanticscholar import SemanticScholar
from nacre.retrieval.wayback import Wayback


def rows(ledger):
    with ledger.path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def test_lens_without_token_writes_gap_and_makes_no_request(cfg, ledger):
    http, _ = make_http(cfg, [])
    assert Lens(http, cfg, ledger).search("calcium carbonate coating") == []
    assert http.session.calls == []
    (row,) = rows(ledger)
    assert (row["source"], row["failure_kind"], row["query_or_id"]) == ("lens", "no_token", "calcium carbonate coating")
    assert list(row) == gaps.COLUMNS


def test_lens_with_token_posts_bearer_and_normalises(cfg, ledger):
    cfg.env["LENS_TOKEN"] = "tok"
    payload = {"data": [{"lens_id": "L1", "jurisdiction": "EP", "doc_number": "9", "kind": "A1",
                         "date_published": "2010-01-01", "biblio": {"invention_title": [{"lang": "en", "text": "T"}]}}]}
    http, _ = make_http(cfg, [ok(payload)])
    recs = Lens(http, cfg, ledger).search("q")
    assert [r["source_id"] for r in recs] == ["L1"]
    method, url, _, headers, body = http.session.calls[0]
    assert method == "POST" and headers["Authorization"] == "Bearer tok" and body["query"]
    assert not ledger.path.exists()


def test_http_failure_becomes_gap_not_exception(cfg, ledger):
    http, _ = make_http(cfg, [FakeResp(403)])
    assert Crossref(http, cfg, ledger).search("x") == []
    (row,) = rows(ledger)
    assert (row["source"], row["failure_kind"]) == ("crossref", "http_error")


def test_rate_limit_exhaustion_is_logged(cfg, ledger):
    http, _ = make_http(cfg, [FakeResp(429)] * 2)
    http.max_retries = 1
    assert SemanticScholar(http, cfg, ledger).lookup("10.1001/a") is None
    assert rows(ledger)[0]["failure_kind"] == "rate_limited"


def test_empty_result_and_404_are_not_indexed(cfg, ledger):
    http, _ = make_http(cfg, [ok({"message": {"items": []}}), FakeResp(404)])
    c = Crossref(http, cfg, ledger)
    assert c.search("nothing") == []
    assert c.lookup("10.1001/missing") is None
    assert [r["failure_kind"] for r in rows(ledger)] == ["not_indexed", "not_indexed"]


def test_garbage_json_is_parse_error(cfg, ledger):
    http, _ = make_http(cfg, [FakeResp(200, "<html>")])
    assert Crossref(http, cfg, ledger).search("x") == []
    assert rows(ledger)[0]["failure_kind"] == "parse_error"


def test_crossref_sends_mailto_and_s2_key_header(cfg, ledger):
    cfg.env["S2_API_KEY"] = "k"
    http, _ = make_http(cfg, [ok({"message": {"items": []}}), ok({"data": []})])
    Crossref(http, cfg, ledger).search("x")
    SemanticScholar(http, cfg, ledger).search("x")
    assert http.session.calls[0][2]["mailto"] == "tester@example.org"
    assert http.session.calls[1][3] == {"x-api-key": "k"}


def test_semanticscholar_references_unwrap_and_paper_ref(cfg, ledger):
    payload = {"data": [{"citedPaper": {"paperId": "p9", "title": "Ref", "year": 2001, "externalIds": {"DOI": "10.1002/R"}}},
                        {"citedPaper": {"paperId": None, "title": "unresolved"}}]}
    http, _ = make_http(cfg, [ok(payload)])
    recs = SemanticScholar(http, cfg, ledger).references("https://doi.org/10.1001/A")
    assert [r["doi"] for r in recs] == ["10.1002/r"]
    assert "DOI:10.1001/a/references" in http.session.calls[0][1]


def test_wayback_missing_snapshot_is_gap(cfg, ledger):
    http, _ = make_http(cfg, [ok({"archived_snapshots": {}})])
    assert Wayback(http, cfg, ledger).snapshot("http://gone.example") is None
    assert rows(ledger)[0]["failure_kind"] == "not_indexed"


def test_gap_ledger_validates_kind_and_filters_since(ledger):
    import pytest
    with pytest.raises(ValueError):
        ledger.log("x", "q", "bogus")
    ledger.log("x", "q", "no_token", "multi\nline detail")
    assert ledger.read("2999-01-01T00:00:00Z") == [] and len(ledger.read("2000-01-01T00:00:00Z")) == 1
    assert "\n" not in rows(ledger)[0]["detail"]

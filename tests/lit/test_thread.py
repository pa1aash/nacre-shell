import json

import pytest

from lit_helpers import FakeHttp, good_row, tiny_pdf
from nacre.lit import evidence as E
from nacre.lit import merge as M
from nacre.lit import routes
from nacre.lit.thread import ThreadSession, jats_to_text, pdf_to_text
from nacre.retrieval.config import Config

DOI = "10.1000/test.1"


def session(tmp_path, http):
    cfg = Config(root=tmp_path, env={})
    cfg.contact = {"mailto": "tester@example.org", "user_agent": "test-agent"}
    return ThreadSession("T-C", root=tmp_path, http=http, config=cfg)


def test_unknown_thread(tmp_path):
    with pytest.raises(ValueError):
        ThreadSession("T-Z", root=tmp_path, http=FakeHttp())


def test_paths_are_thread_scoped(tmp_path):
    ts = session(tmp_path, FakeHttp())
    assert ts.config.gaps_path == tmp_path / "lit" / "corpus" / "T-C" / "instrument_gaps.csv"
    assert ts.config.records_path.is_relative_to(tmp_path / ".local")
    assert ts.config.cache_dir.is_relative_to(tmp_path / ".local")
    assert ts.config.source("openalex")["min_interval"] > 0


def test_search_logs_query(tmp_path):
    payload = {"results": [{"id": "https://openalex.org/W1", "doi": "https://doi.org/" + DOI, "title": "T",
                            "publication_year": 2020, "authorships": []}]}
    ts = session(tmp_path, FakeHttp({"api.openalex.org/works": payload}))
    recs = ts.search("openalex", "calcite", 5)
    assert recs[0]["doi"] == DOI
    line = json.loads((ts.dir / "queries.jsonl").read_text())
    assert line["route"] == "openalex" and line["query"] == "calcite" and line["hits"] == 1
    assert line["dois"] == [DOI] and line["date"].endswith("Z")
    assert ts.config.records_path.exists()


def test_search_unknown_route(tmp_path):
    with pytest.raises(ValueError):
        session(tmp_path, FakeHttp()).search("google", "x")


def test_fulltext_paywalled_is_logged(tmp_path):
    http = FakeHttp({"api.unpaywall.org": {"doi": DOI, "is_oa": False, "oa_locations": []},
                     "api.openalex.org": {"id": "W1"}, "europepmc/webservices/rest/search": {"resultList": {"result": []}}})
    ts = session(tmp_path, http)
    txt, why = ts.fulltext(DOI)
    assert txt is None and why.startswith("paywalled")
    gaps = ts.config.gaps_path.read_text()
    assert "paywalled" in gaps and DOI in gaps
    assert not (ts.dir / "sources.jsonl").exists()


def test_fulltext_falls_back_to_archived_copy(tmp_path):
    pdf_url = "https://publisher.example/x.pdf"
    http = FakeHttp({"api.unpaywall.org": {"doi": DOI, "is_oa": True, "best_oa_location": {"url_for_pdf": pdf_url,
                                                                                          "license": "cc-by"}},
                     "api.openalex.org": {"id": "W1"}, "europepmc/webservices/rest/search": {"resultList": {"result": []}}},
                    downloads={"web.archive.org": tiny_pdf(["page one", "Table 2 log Ksp = -8.48"])})
    ts = session(tmp_path, http)
    txt, route = ts.fulltext(DOI)
    assert route == "unpaywall+wayback"
    assert txt.is_relative_to(tmp_path / ".local" / "lit" / "T-C")
    src = json.loads((ts.dir / "sources.jsonl").read_text())
    assert src["doi"] == DOI and src["access_route"] == "fulltext:unpaywall+wayback"
    assert len(src["sha256"]) == 64 and src["pages"] == 2 and src["licence"] == "cc-by"
    assert src["local_path"].startswith(".local/")
    hits = list(ts.grep(r"Ksp"))
    assert hits and hits[0][1] == "2/-"
    assert "http_error" in ts.config.gaps_path.read_text()


def test_fulltext_europepmc_xml(tmp_path):
    xml = "<article><sec><title>Results</title><p>gamma = 0.1 J m<sup>-2</sup></p></sec></article>"
    http = FakeHttp({"api.unpaywall.org": {"doi": DOI, "is_oa": True, "oa_locations": []},
                     "api.openalex.org": {"id": "W1"},
                     "europepmc/webservices/rest/search": {"resultList": {"result": [{"pmcid": "PMC1"}]}},
                     "PMC1/fullTextXML": xml})
    ts = session(tmp_path, http)
    txt, route = ts.fulltext(DOI)
    assert route == "europepmc-xml"
    assert "Results" in txt.read_text() and "gamma = 0.1 J m -2" in txt.read_text()


def test_abstract_cached_locally_and_logged(tmp_path):
    http = FakeHttp({"api.crossref.org/works/": {"message": {"abstract": "<jats:p>" + "word " * 20 + "</jats:p>"}}})
    ts = session(tmp_path, http)
    path, text = ts.abstract(DOI)
    assert path.is_relative_to(tmp_path / ".local") and text.startswith("word")
    src = json.loads((ts.dir / "sources.jsonl").read_text())
    assert src["access_route"] == "abstract:crossref"
    assert "word" not in (ts.dir / "sources.jsonl").read_text()


def test_abstract_missing_logged(tmp_path):
    ts = session(tmp_path, FakeHttp())
    assert ts.abstract(DOI) == (None, "")
    assert "no abstract" in ts.config.gaps_path.read_text()


def test_pdf_page_markers(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(tiny_pdf(["alpha", "beta"]))
    n = pdf_to_text(pdf, tmp_path / "a.txt")
    text = (tmp_path / "a.txt").read_text()
    assert n == 2 and "=== pdf page 2 (label -) ===" in text


def test_jats_table_cells(tmp_path):
    jats_to_text("<table><tr><td>a</td><td>b</td></tr></table>", tmp_path / "t.txt")
    assert "a | | b" in (tmp_path / "t.txt").read_text().replace("  ", " ")


def test_inverted_index():
    assert routes.inverted_to_text({"b": [1], "a": [0], "c": [2]}) == "a b c"
    assert routes.inverted_to_text(None) == ""


def test_merge_run_writes_outputs(tmp_path):
    for t in E.THREADS:
        d = tmp_path / "lit" / "corpus" / t
        d.mkdir(parents=True)
        rows = []
        if t == "T-C":
            rows = [good_row()]
        E.write_csv(d / "rows.csv", rows)
        (d / "gaps.md").write_text("# %s gaps\n\n- nothing on X found by search\n" % t)
    assert M.run(tmp_path) == 0
    _, rows = E.read_csv(tmp_path / "lit" / "evidence_table.csv")
    assert [r["row_id"] for r in rows] == ["TC-001"]
    import yaml

    cov = yaml.safe_load((tmp_path / "lit" / "corpus" / "coverage.yaml").read_text())
    assert len(cov["targets"]) == len(E.TARGETS)
    gaps = (tmp_path / "lit" / "corpus" / "gaps.md").read_text()
    assert "nothing on X" in gaps and gaps.index("ACC-water") < gaps.index("in-cell potential")


def test_merge_refuses_invalid_rows(tmp_path):
    for t in E.THREADS:
        d = tmp_path / "lit" / "corpus" / t
        d.mkdir(parents=True)
        E.write_csv(d / "rows.csv", [good_row(locator="")] if t == "T-C" else [])
    assert M.run(tmp_path) == 1
    assert not (tmp_path / "lit" / "evidence_table.csv").exists()

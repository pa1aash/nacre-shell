import json

from nacre.retrieval import record as R
from nacre.retrieval.store import Store
from conftest import SECRET


def rec(source="crossref", sid="1", **kw):
    return R.make_record(source, sid, "2026-01-01T00:00:00Z", "k-" + source, **kw)


def test_dedupe_exact_doi_first(tmp_path):
    s = Store(tmp_path / "r.jsonl")
    a, how = s.upsert(rec(doi="10.1001/a", title="Alpha", year=2020, arxiv_id="2101.00001"))
    assert how == "new"
    # same DOI, different title/arXiv: DOI wins and merges
    b, how = s.upsert(rec("unpaywall", "2", doi="https://doi.org/10.1001/A", title="Other title", year=2001))
    assert how == "doi" and b is a and len(s.records) == 1


def test_dedupe_arxiv_before_title(tmp_path):
    s = Store(tmp_path / "r.jsonl")
    s.upsert(rec("arxiv", "2101.00001", arxiv_id="2101.00001", title="Same", year=2021))
    s.upsert(rec("arxiv", "2101.00009", arxiv_id="2101.00009", title="Same", year=2021))
    assert len(s.records) == 2
    _, how = s.upsert(rec("semanticscholar", "p", arxiv_id="arXiv:2101.00009v2", title="Different", year=1999))
    assert how == "arxiv_id" and len(s.records) == 2


def test_dedupe_title_year_fallback_and_guards(tmp_path):
    s = Store(tmp_path / "r.jsonl")
    s.upsert(rec(title="Mussel-inspired Adhesion", year=2020))
    _, how = s.upsert(rec("openaire", "9", title="mussel inspired  adhesion!", year=2020))
    assert how == "title_year" and len(s.records) == 1
    s.upsert(rec("openaire", "10", title="Mussel inspired adhesion", year=2021))   # other year
    assert len(s.records) == 2
    s.upsert(rec("zenodo", "11", doi="10.1001/x", title="Distinct", year=2018))
    s.upsert(rec("zenodo", "12", doi="10.1001/y", title="Distinct", year=2018))      # conflicting DOIs
    assert len(s.records) == 4


def test_seen_in_merges_provenance_from_all_sources(tmp_path):
    s = Store(tmp_path / "r.jsonl")
    s.upsert(rec("semanticscholar", "p1", doi="10.1001/a", title="T", year=2020, oa_status="open"))
    s.upsert(rec("crossref", "10.1001/a", doi="10.1001/a", title="T (Crossref)", year=2020,
                 authors=[R.author("Doe", "J", "0000-1")]))
    e, _ = s.upsert(rec("unpaywall", "10.1001/a", doi="10.1001/a", oa_status="gold", licence="cc-by"))
    assert [x["source"] for x in e["seen_in"]] == ["semanticscholar", "crossref", "unpaywall"]
    assert e["title"] == "T (Crossref)" and e["source"] == "crossref"      # higher-ranked source wins
    assert (e["oa_status"], e["licence"]) == ("gold", "cc-by")              # Unpaywall owns OA fields
    assert e["authors"][0]["orcid"] == "0000-1"
    s.upsert(rec("crossref", "10.1001/a", doi="10.1001/a", title="T"))            # re-seen: no duplicate entry
    assert len(e["seen_in"]) == 3


def test_records_jsonl_never_holds_abstract_or_fulltext(tmp_path):
    path = tmp_path / "r.jsonl"
    s = Store(path)
    dirty = rec(doi="10.1001/a", title="T", year=2020)
    dirty.update(abstract=SECRET, full_text=SECRET, summary=SECRET, fulltext=SECRET)
    s.upsert(dirty)
    s.save()
    text = path.read_text()
    assert SECRET not in text
    stored = json.loads(text.splitlines()[0])
    assert not {"abstract", "full_text", "fulltext", "summary", "text"} & set(stored)
    assert set(stored) == set(R.FIELDS) | {"seen_in", "fulltext_sha256"}
    Store(path).save()                       # round trip keeps it clean
    assert SECRET not in path.read_text()


def test_attach_fulltext_records_sha256(tmp_path):
    import hashlib
    pdf = tmp_path / "f.pdf"
    pdf.write_bytes(b"%PDF-1.4 synthetic")
    s = Store(tmp_path / "r.jsonl")
    s.upsert(rec(doi="10.1001/a", title="T", year=2020))
    digest = s.attach_fulltext("https://doi.org/10.1001/A", pdf, "cc-by")
    assert digest == hashlib.sha256(b"%PDF-1.4 synthetic").hexdigest()
    assert s.lookup("10.1001/a")["fulltext_sha256"] == digest and s.lookup("10.1001/a")["licence"] == "cc-by"
    s.save()
    assert Store(tmp_path / "r.jsonl").stats()["with_fulltext_sha256"] == 1


def test_stats(tmp_path):
    s = Store(tmp_path / "r.jsonl")
    s.upsert(rec(doi="10.1001/a", title="T", year=2020))
    s.upsert(rec("unpaywall", "x", doi="10.1001/a"))
    st = s.stats()
    assert st["records"] == 1 and st["multi_source"] == 1 and st["seen_in_by_source"] == {"crossref": 1, "unpaywall": 1}

import json

from nacre.retrieval import arxiv, chemrxiv, crossref, lens, openaire, record, semanticscholar, unpaywall, wayback, zenodo
from retrieval_helpers import SECRET

T, K = "2026-01-01T00:00:00Z", "key"


def no_leak(rec):
    assert SECRET not in json.dumps(rec)
    assert set(rec) == set(record.FIELDS)


def test_crossref():
    item = {"DOI": "10.1000/ABC", "title": ["A Title"], "abstract": SECRET, "type": "journal-article",
            "author": [{"family": "Doe", "given": "Jane", "ORCID": "http://orcid.org/0000-0000-0000-0001"}],
            "issued": {"date-parts": [[2021, 3]]}, "container-title": ["J. Test"],
            "license": [{"URL": "https://example.org/lic"}], "URL": "https://doi.org/10.1000/abc"}
    r = crossref.parse_item(item, T, K)
    no_leak(r)
    assert (r["doi"], r["year"], r["venue"], r["licence"]) == ("10.1000/abc", 2021, "J. Test", "https://example.org/lic")
    assert r["authors"][0] == {"family": "Doe", "given": "Jane", "orcid": "0000-0000-0000-0001"}


def test_unpaywall():
    item = {"doi": "10.1000/ABC", "title": "T", "is_oa": True, "oa_status": "green", "year": 2020,
            "journal_name": "J", "genre": "journal-article", "abstract": SECRET,
            "best_oa_location": {"url": "https://x/landing", "url_for_pdf": "https://x/f.pdf", "license": "cc-by"}}
    r = unpaywall.parse_item(item, T, K)
    no_leak(r)
    assert (r["oa_status"], r["licence"]) == ("green", "cc-by")
    assert unpaywall.best_pdf_url(item) == "https://x/f.pdf"
    closed = unpaywall.parse_item({"doi": "10.1001/x", "is_oa": False, "oa_status": "closed"}, T, K)
    assert closed["oa_status"] == "closed" and closed["licence"] is None


def test_semanticscholar():
    item = {"paperId": "p1", "title": "T", "year": 2019, "venue": "V", "abstract": SECRET,
            "externalIds": {"DOI": "10.1005/XY", "ArXiv": "2101.00002"}, "isOpenAccess": True,
            "authors": [{"authorId": "1", "name": "Ada Lovelace"}],
            "openAccessPdf": {"url": "https://x/p.pdf", "license": "CCBY"}, "publicationTypes": ["JournalArticle"]}
    r = semanticscholar.parse_item(item, T, K)
    no_leak(r)
    assert (r["doi"], r["arxiv_id"], r["oa_status"], r["licence"]) == ("10.1005/xy", "2101.00002", "open", "CCBY")
    assert r["authors"][0]["family"] == "Lovelace"


def test_arxiv_feed():
    xml = """<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry><id>http://arxiv.org/abs/2101.00003v2</id><title>A  Spaced
      Title</title><summary>%s</summary><published>2021-01-02T00:00:00Z</published>
      <author><name>Grace Hopper</name></author><arxiv:doi>10.1009/ZZ</arxiv:doi>
      <arxiv:primary_category term="cond-mat.mtrl-sci"/>
      <link href="http://arxiv.org/pdf/2101.00003v2" rel="related" title="pdf"/></entry>
      <entry><id>http://arxiv.org/api/errors#bad</id><title>Error</title></entry></feed>""" % SECRET
    recs = arxiv.parse_feed(xml, T, K)
    assert len(recs) == 1
    r = recs[0]
    no_leak(r)
    assert (r["arxiv_id"], r["doi"], r["title"], r["year"]) == ("2101.00003", "10.1009/zz", "A Spaced Title", 2021)
    assert r["venue"] == "arXiv:cond-mat.mtrl-sci"


def test_chemrxiv():
    item = {"id": "abc123", "title": "T", "doi": "10.26434/chemrxiv-1", "abstract": SECRET,
            "authors": [{"firstName": "A", "lastName": "B", "orcid": "0000-0001"}],
            "publishedDate": "2022-05-01T00:00:00Z", "license": {"name": "CC BY 4.0"},
            "asset": {"original": {"url": "https://x/a.pdf"}}}
    r = chemrxiv.parse_item(item, T, K)
    no_leak(r)
    assert (r["year"], r["licence"], r["type"]) == (2022, "CC BY 4.0", "preprint")


def test_openaire():
    item = {"id": "oa1", "type": "dataset", "mainTitle": "T", "descriptions": [SECRET],
            "authors": [{"fullName": "SMITH JOHN", "name": None, "surname": None, "rank": 1, "pid": None}],
            "publicationDate": "2018-04-05", "pids": [{"scheme": "doi", "value": "10.1007/DS"}],
            "bestAccessRight": {"label": "OPEN"}, "instances": [{"license": "CC0", "urls": ["https://x/d"]}]}
    r = openaire.parse_item(item, T, K)
    no_leak(r)
    assert (r["doi"], r["year"], r["licence"], r["type"]) == ("10.1007/ds", 2018, "CC0", "dataset")
    assert r["authors"][0] == {"family": "Smith", "given": "John", "orcid": None}


def test_zenodo():
    item = {"id": 77, "doi": "10.5281/zenodo.77", "links": {"self_html": "https://zenodo.org/records/77"},
            "metadata": {"title": "T", "description": SECRET, "publication_date": "2020-02-02",
                         "creators": [{"name": "Doe, Jane", "orcid": "0000-0002"}], "license": {"id": "cc-by-4.0"},
                         "access_right": "open", "resource_type": {"type": "dataset"}}}
    r = zenodo.parse_item(item, T, K)
    no_leak(r)
    assert (r["source_id"], r["licence"], r["type"], r["authors"][0]["family"]) == ("77", "cc-by-4.0", "dataset", "Doe")


def test_wayback():
    data = {"archived_snapshots": {"closest": {"available": True, "url": "http://web.archive.org/web/1/x",
                                               "timestamp": "20200101000000", "status": "200"}}}
    snap = wayback.parse_snapshot(data, "http://x", T, K)
    assert snap["snapshot_url"].startswith("http://web.archive.org") and snap["timestamp"] == "20200101000000"
    assert wayback.parse_snapshot({"archived_snapshots": {}}, "http://x", T, K) is None


def test_lens():
    item = {"lens_id": "000-111", "jurisdiction": "US", "doc_number": "123", "kind": "B2",
            "date_published": "2015-06-01", "abstract": SECRET,
            "biblio": {"invention_title": [{"lang": "de", "text": "Titel"}, {"lang": "en", "text": "Title"}],
                       "parties": {"inventors": [{"extracted_name": {"value": "Doe, Jane"}}]}}}
    r = lens.parse_item(item, T, K)
    no_leak(r)
    assert (r["title"], r["venue"], r["type"], r["year"]) == ("Title", "US-123-B2", "patent", 2015)

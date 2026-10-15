"""Live smoke: one call per source. Run with `uv run pytest -m network`.

A failing source becomes a gap row and a line in lit/corpus/cache/smoke_results.json;
it never fails the run. The reference DOI is looked up through Crossref at run time.
"""
import json
import re

import pytest

from nacre.retrieval.cli import SEARCHABLE, build

pytestmark = pytest.mark.network
QUERY = "calcium carbonate polydopamine"
RESULTS = {}


@pytest.fixture(scope="module")
def env():
    config, ledger, clients = build()
    yield config, ledger, clients
    path = config.cache_dir / "smoke_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(RESULTS, indent=2, sort_keys=True))


def record(name, ok, detail=""):
    RESULTS[name] = {"status": "ok" if ok else "gap", "detail": detail}


def attempt(name, ledger, fn):
    try:
        out = fn()
    except Exception as exc:  # a smoke failure is data, not a test failure
        ledger.log(name, "smoke", "http_error", "%s: %s" % (type(exc).__name__, exc))
        record(name, False, "%s: %s" % (type(exc).__name__, exc))
        return None
    return out


@pytest.mark.parametrize("name", [n for n in SEARCHABLE if n != "lens"])
def test_search(name, env):
    _, ledger, clients = env
    recs = attempt(name, ledger, lambda: clients[name].search(QUERY, 3))
    if recs is None:
        return
    record(name, bool(recs), "%d record(s)" % len(recs) if recs else "no records (gap row written)")


def test_lens(env):
    config, ledger, clients = env
    recs = attempt("lens", ledger, lambda: clients["lens"].search(QUERY, 3))
    if recs is None:
        return
    if config.key("LENS_TOKEN"):
        record("lens", bool(recs), "%d record(s)" % len(recs))
    else:
        record("lens", False, "no LENS_TOKEN: instrument gap recorded")


def test_unpaywall_and_s2_by_doi(env):
    _, ledger, clients = env
    hits = attempt("crossref-doi-pick", ledger, lambda: clients["crossref"].search("mussel-inspired polydopamine adhesion", 5))
    # a main journal article, not supplementary material (DOIs ending .s001, .s002, ...)
    doi = next((h["doi"] for h in hits or [] if h.get("doi") and h.get("type") == "journal-article"
                and not re.search(r"\.s\d+$", h["doi"])), None)
    if not doi:
        record("unpaywall", False, "no reference DOI from Crossref")
        record("semanticscholar-doi", False, "no reference DOI from Crossref")
        return
    unp = attempt("unpaywall", ledger, lambda: clients["unpaywall"].lookup(doi))
    record("unpaywall", bool(unp), "DOI %s" % doi if unp else "DOI %s not returned (gap row written)" % doi)
    s2 = attempt("semanticscholar", ledger, lambda: clients["semanticscholar"].lookup(doi))
    record("semanticscholar-doi", bool(s2), "DOI %s" % doi if s2 else "DOI %s not returned (gap row written)" % doi)
    refs = attempt("semanticscholar", ledger, lambda: clients["semanticscholar"].references(doi, 3))
    record("semanticscholar-references", bool(refs), "%d reference(s)" % len(refs or []))


def test_wayback(env):
    _, ledger, clients = env
    snap = attempt("wayback", ledger, lambda: clients["wayback"].snapshot("https://example.com"))
    record("wayback", bool(snap), snap["snapshot_url"] if snap else "no snapshot (gap row written)")

"""Routes not covered by nacre.retrieval: OpenAlex, Europe PMC and PubMed search, and abstracts.

Every client reuses nacre.retrieval.http.Http (rate limits, backoff, raw cache) and logs failures to
the ledger it is given. Abstract text is returned to the caller and never reaches a committed file.
"""
import html
import re
import urllib.parse

from nacre.retrieval import record as R
from nacre.retrieval.base import Client

OPENALEX = "https://api.openalex.org/works"
EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CROSSREF = "https://api.crossref.org/works/"
S2 = "https://api.semanticscholar.org/graph/v1/paper/"

# Extra per-source settings; configs/retrieval/sources.yaml is not this lane's to edit.
SOURCE_DEFAULTS = {
    "openalex": {"min_interval": 0.2, "timeout": 45},
    "europepmc": {"min_interval": 0.3, "timeout": 45},
    "pubmed": {"min_interval": 0.4, "timeout": 30},
    "publisher": {"min_interval": 1.0, "timeout": 60},
}


def strip_markup(text):
    """JATS/HTML fragment to plain text."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    return " ".join(html.unescape(text).split())


def inverted_to_text(inv):
    """OpenAlex abstract_inverted_index to running text."""
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def openalex_record(item, retrieved_utc, cache_key):
    authors = []
    for a in item.get("authorships") or []:
        fam, giv = R.split_name((a.get("author") or {}).get("display_name"))
        authors.append(R.author(fam, giv, (a.get("author") or {}).get("orcid")))
    best = item.get("best_oa_location") or {}
    oa = item.get("open_access") or {}
    venue = ((item.get("primary_location") or {}).get("source") or {}).get("display_name")
    return R.make_record(
        "openalex", item.get("id"), retrieved_utc, cache_key,
        doi=item.get("doi"), title=item.get("title"), authors=authors,
        year=item.get("publication_year"), venue=venue, type=item.get("type"),
        oa_status=oa.get("oa_status"), licence=best.get("license"),
        urls=[best.get("pdf_url"), best.get("landing_page_url"), oa.get("oa_url")])


def openalex_pdf_urls(item):
    urls = []
    for loc in [item.get("best_oa_location") or {}] + list(item.get("locations") or []):
        u = (loc or {}).get("pdf_url")
        if u and u not in urls:
            urls.append(u)
    return urls


class OpenAlex(Client):
    name = "openalex"

    def _params(self, extra):
        p = {"mailto": self.config.mailto}
        p.update(extra)
        return p

    def search(self, query, limit=10):
        resp = self.fetch(query, OPENALEX, params=self._params({"search": query, "per-page": limit}))
        data = self.json_or_gap(query, resp)
        if data is None:
            return []
        items = data.get("results") or []
        if not items:
            self.empty_gap(query)
        return [openalex_record(i, self.now(), resp.cache_key) for i in items]

    def work(self, doi):
        doi = R.normalize_doi(doi)
        if not doi:
            return None
        resp = self.fetch(doi, OPENALEX + "/doi:" + urllib.parse.quote(doi, safe="/"), params=self._params({}))
        return self.json_or_gap(doi, resp)

    def abstract(self, doi):
        item = self.work(doi)
        return inverted_to_text((item or {}).get("abstract_inverted_index"))


def europepmc_record(item, retrieved_utc, cache_key):
    authors = []
    for a in ((item.get("authorList") or {}).get("author") or []):
        authors.append(R.author(a.get("lastName") or a.get("fullName", ""), a.get("firstName", "")))
    return R.make_record(
        "europepmc", item.get("id"), retrieved_utc, cache_key,
        doi=item.get("doi"), title=item.get("title"), authors=authors, year=item.get("pubYear"),
        venue=item.get("journalTitle"), type=item.get("pubType"),
        oa_status="open" if item.get("isOpenAccess") == "Y" else None,
        urls=["https://europepmc.org/article/%s/%s" % (item.get("source"), item.get("id"))])


class EuropePMC(Client):
    name = "europepmc"

    def _search_raw(self, query, limit, result_type="lite"):
        resp = self.fetch(query, EUROPEPMC + "/search",
                          params={"query": query, "format": "json", "pageSize": limit, "resultType": result_type})
        return self.json_or_gap(query, resp), resp

    def search(self, query, limit=10):
        data, resp = self._search_raw(query, limit)
        items = ((data or {}).get("resultList") or {}).get("result") or []
        if data is not None and not items:
            self.empty_gap(query)
        return [europepmc_record(i, self.now(), resp.cache_key) for i in items]

    def by_doi(self, doi):
        data, _ = self._search_raw('DOI:"%s"' % doi, 1, "core")
        items = ((data or {}).get("resultList") or {}).get("result") or []
        return items[0] if items else None

    def abstract(self, doi):
        return strip_markup((self.by_doi(doi) or {}).get("abstractText"))

    def fulltext_xml(self, pmcid):
        resp = self.fetch(pmcid, EUROPEPMC + "/%s/fullTextXML" % pmcid)
        return resp.text if resp is not None else None


class PubMed(Client):
    name = "pubmed"

    def search(self, query, limit=10):
        resp = self.fetch(query, EUTILS + "/esearch.fcgi",
                          params={"db": "pubmed", "term": query, "retmode": "json", "retmax": limit})
        data = self.json_or_gap(query, resp)
        ids = ((data or {}).get("esearchresult") or {}).get("idlist") or []
        if data is not None and not ids:
            self.empty_gap(query)
            return []
        if not ids:
            return []
        resp = self.fetch(query, EUTILS + "/esummary.fcgi",
                          params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"})
        summ = (self.json_or_gap(query, resp) or {}).get("result") or {}
        out = []
        for pmid in ids:
            s = summ.get(pmid) or {}
            doi = next((a.get("value") for a in s.get("articleids") or [] if a.get("idtype") == "doi"), None)
            # PubMed display names are "Family Initials".
            authors = [R.author(*((a.get("name") or "").split(" ", 1) + [""])[:2]) for a in s.get("authors") or []]
            out.append(R.make_record("pubmed", pmid, self.now(), resp.cache_key if resp else None,
                                     doi=doi, title=s.get("title"), authors=authors,
                                     year=(s.get("pubdate") or "")[:4] or None, venue=s.get("fulljournalname"),
                                     urls=["https://pubmed.ncbi.nlm.nih.gov/%s/" % pmid]))
        return out


class Abstracts(Client):
    """Abstract text by DOI from Crossref, then OpenAlex, Europe PMC and Semantic Scholar."""
    name = "abstracts"

    def __init__(self, http, config, ledger, openalex, europepmc):
        super().__init__(http, config, ledger)
        self.openalex, self.europepmc = openalex, europepmc

    def crossref(self, doi):
        resp = self.fetch(doi, CROSSREF + urllib.parse.quote(doi, safe="/"), params={"mailto": self.config.mailto})
        data = self.json_or_gap(doi, resp) or {}
        return strip_markup((data.get("message") or {}).get("abstract"))

    def semanticscholar(self, doi):
        key = self.config.key("S2_API_KEY")
        resp = self.fetch(doi, S2 + "DOI:" + urllib.parse.quote(doi, safe="/"), params={"fields": "abstract"},
                          headers={"x-api-key": key} if key else {})
        return ((self.json_or_gap(doi, resp) or {}).get("abstract") or "").strip()

    def get(self, doi):
        """Returns (route, text); route is None when no route has an abstract."""
        for route, fn in (("crossref", self.crossref), ("openalex", self.openalex.abstract),
                          ("europepmc", self.europepmc.abstract), ("semanticscholar", self.semanticscholar)):
            text = fn(doi)
            if text and len(text) > 40:
                return route, text
        self.gap(doi, "not_indexed", "no abstract on crossref, openalex, europepmc or semanticscholar")
        return None, ""

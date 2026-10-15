"""Semantic Scholar Graph API: search, paper lookup, references and citations."""
import urllib.parse

from nacre.retrieval import record as R
from nacre.retrieval.base import Client

API = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,year,venue,externalIds,authors,openAccessPdf,publicationTypes,isOpenAccess,url"


def parse_item(item, retrieved_utc, cache_key):
    """Normalise one paper. S2 gives author display names only, so names are split heuristically."""
    ext = item.get("externalIds") or {}
    authors = []
    for a in item.get("authors") or []:
        fam, giv = R.split_name(a.get("name"))
        authors.append(R.author(fam, giv))
    pdf = item.get("openAccessPdf") or {}
    types = item.get("publicationTypes") or []
    return R.make_record(
        "semanticscholar", item.get("paperId"), retrieved_utc, cache_key,
        doi=ext.get("DOI"), arxiv_id=ext.get("ArXiv"), title=item.get("title"), authors=authors,
        year=item.get("year"), venue=item.get("venue") or None, type=types[0] if types else None,
        oa_status=("open" if item.get("isOpenAccess") else "closed") if "isOpenAccess" in item else None,
        licence=pdf.get("license") or None, urls=[item.get("url"), pdf.get("url")])


class SemanticScholar(Client):
    name = "semanticscholar"

    def _headers(self):
        key = self.config.key("S2_API_KEY")
        return {"x-api-key": key} if key else {}

    def _items(self, query_or_id, url, params, unwrap=None):
        resp = self.fetch(query_or_id, url, params=params, headers=self._headers())
        data = self.json_or_gap(query_or_id, resp)
        if data is None:
            return []
        rows = data.get("data") or []
        if unwrap:
            rows = [r.get(unwrap) for r in rows]
        rows = [r for r in rows if r and r.get("paperId")]
        if not rows:
            self.empty_gap(query_or_id)
        return [parse_item(r, self.now(), resp.cache_key) for r in rows]

    def search(self, query, limit=10):
        return self._items(query, API + "/paper/search", {"query": query, "limit": limit, "fields": FIELDS})

    @staticmethod
    def paper_ref(ident):
        doi = R.normalize_doi(ident)
        if doi:
            return "DOI:" + doi
        arx = R.normalize_arxiv(ident)
        return "ARXIV:" + arx if arx else str(ident)

    def lookup(self, ident):
        ref = self.paper_ref(ident)
        resp = self.fetch(ref, API + "/paper/" + urllib.parse.quote(ref, safe=":/"),
                          params={"fields": FIELDS}, headers=self._headers())
        data = self.json_or_gap(ref, resp)
        if not data or not data.get("paperId"):
            return None
        return parse_item(data, self.now(), resp.cache_key)

    def references(self, ident, limit=100):
        ref = self.paper_ref(ident)
        return self._items(ref, API + "/paper/%s/references" % urllib.parse.quote(ref, safe=":/"),
                           {"limit": limit, "fields": FIELDS}, unwrap="citedPaper")

    def citations(self, ident, limit=100):
        ref = self.paper_ref(ident)
        return self._items(ref, API + "/paper/%s/citations" % urllib.parse.quote(ref, safe=":/"),
                           {"limit": limit, "fields": FIELDS}, unwrap="citingPaper")

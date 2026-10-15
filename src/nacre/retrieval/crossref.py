"""Crossref works search and DOI lookup (polite pool via mailto)."""
import urllib.parse

from nacre.retrieval import record as R
from nacre.retrieval.base import Client

API = "https://api.crossref.org/works"


def parse_item(item, retrieved_utc, cache_key):
    """Normalise one Crossref work. The abstract field, if any, is dropped."""
    parts = ((item.get("issued") or {}).get("date-parts") or [[None]])[0]
    authors = [R.author(a.get("family") or a.get("name", ""), a.get("given", ""), a.get("ORCID"))
               for a in item.get("author") or []]
    licences = [l.get("URL") for l in item.get("license") or [] if l.get("URL")]
    return R.make_record(
        "crossref", item.get("DOI"), retrieved_utc, cache_key,
        doi=item.get("DOI"), title=((item.get("title") or [""])[0] or None), authors=authors,
        year=parts[0] if parts else None, venue=(item.get("container-title") or [None])[0],
        type=item.get("type"), licence=licences[0] if licences else None,
        urls=[item.get("URL")])


class Crossref(Client):
    name = "crossref"

    def _params(self, extra):
        p = {"mailto": self.config.mailto}
        p.update(extra)
        return p

    def search(self, query, limit=10):
        resp = self.fetch(query, API, params=self._params({"query": query, "rows": limit}))
        data = self.json_or_gap(query, resp)
        if data is None:
            return []
        items = (data.get("message") or {}).get("items") or []
        if not items:
            self.empty_gap(query)
        return [parse_item(i, self.now(), resp.cache_key) for i in items]

    def lookup(self, doi):
        doi = R.normalize_doi(doi)
        if not doi:
            return None
        resp = self.fetch(doi, API + "/" + urllib.parse.quote(doi, safe="/"), params=self._params({}))
        data = self.json_or_gap(doi, resp)
        if data is None or not data.get("message"):
            return None
        return parse_item(data["message"], self.now(), resp.cache_key)
